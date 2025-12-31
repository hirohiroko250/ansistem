"""
Billing Creation Mixin - 請求確定データ生成
"""
from datetime import date
from decimal import Decimal
from collections import defaultdict

from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models, transaction
from drf_spectacular.utils import extend_schema

from apps.billing.models import ConfirmedBilling, MonthlyBillingDeadline, GuardianBalance
from apps.billing.serializers import ConfirmedBillingCreateSerializer, BillingConfirmBatchSerializer


def _get_tenant_id(request):
    """リクエストからテナントIDを取得"""
    tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)
    if not tenant_id:
        from apps.tenants.models import Tenant
        default_tenant = Tenant.objects.first()
        if default_tenant:
            tenant_id = default_tenant.id
    return tenant_id


class BillingCreationMixin:
    """請求確定データ生成関連アクション"""

    @extend_schema(summary='請求確定データを生成')
    @action(detail=False, methods=['post'])
    def create_confirmed_billing(self, request):
        """指定月の請求確定データを生成"""
        serializer = ConfirmedBillingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data['year']
        month = data['month']
        student_ids = data.get('student_ids')

        tenant_id = _get_tenant_id(request)

        from apps.students.models import Student
        from apps.contracts.models import StudentItem, Contract

        # billing_month形式
        billing_month_hyphen = f"{year}-{str(month).zfill(2)}"
        billing_month_compact = f"{year}{str(month).zfill(2)}"

        # 対象月の開始日・終了日
        billing_start = date(year, month, 1)
        if month == 12:
            billing_end = date(year + 1, 1, 1)
        else:
            billing_end = date(year, month + 1, 1)

        # 対象生徒を取得
        students = self._get_target_students(
            tenant_id, student_ids, billing_month_hyphen, billing_month_compact,
            billing_start, billing_end, Student, StudentItem, Contract
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        with transaction.atomic():
            for student in students:
                result = self._process_student_billing(
                    student, tenant_id, year, month, request.user
                )
                if result['error']:
                    errors.append(result['error'])
                    skipped_count += 1
                elif result['created']:
                    created_count += 1
                elif result['updated']:
                    updated_count += 1
                else:
                    skipped_count += 1

            # マイル割引を適用
            self._apply_mile_discounts(tenant_id, year, month)

        return Response({
            'success': True,
            'year': year,
            'month': month,
            'created_count': created_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'error_count': len(errors),
            'errors': errors[:10],
        })

    def _get_target_students(self, tenant_id, student_ids, billing_month_hyphen,
                              billing_month_compact, billing_start, billing_end,
                              Student, StudentItem, Contract):
        """対象生徒を取得"""
        # 滞納がある退会者のIDを取得
        students_with_unpaid = ConfirmedBilling.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True,
            balance__gt=0
        ).values_list('student_id', flat=True).distinct()

        guardians_with_balance = GuardianBalance.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True,
            balance__lt=0
        ).values_list('guardian_id', flat=True)

        withdrawn_with_debt_ids = set(
            Student.objects.filter(
                tenant_id=tenant_id,
                status=Student.Status.WITHDRAWN,
                deleted_at__isnull=True
            ).filter(
                models.Q(id__in=students_with_unpaid) |
                models.Q(guardian_id__in=guardians_with_balance)
            ).values_list('id', flat=True)
        )

        if student_ids:
            return Student.objects.filter(
                tenant_id=tenant_id,
                id__in=student_ids,
                deleted_at__isnull=True
            ).exclude(
                status=Student.Status.SUSPENDED
            ).exclude(
                models.Q(status=Student.Status.WITHDRAWN) & ~models.Q(id__in=withdrawn_with_debt_ids)
            )

        # 対象月にStudentItemまたはContractがある生徒
        student_ids_with_items = StudentItem.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).filter(
            models.Q(billing_month=billing_month_hyphen) | models.Q(billing_month=billing_month_compact)
        ).values_list('student_id', flat=True).distinct()

        student_ids_with_contracts = Contract.objects.filter(
            tenant_id=tenant_id,
            status=Contract.Status.ACTIVE,
            start_date__lt=billing_end,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=billing_start)
        ).values_list('student_id', flat=True).distinct()

        all_student_ids = set(student_ids_with_items) | set(student_ids_with_contracts) | withdrawn_with_debt_ids

        return Student.objects.filter(
            tenant_id=tenant_id,
            id__in=all_student_ids,
            deleted_at__isnull=True
        ).exclude(
            status=Student.Status.SUSPENDED
        ).exclude(
            models.Q(status=Student.Status.WITHDRAWN) & ~models.Q(id__in=withdrawn_with_debt_ids)
        )

    def _process_student_billing(self, student, tenant_id, year, month, user):
        """生徒の請求確定データを処理"""
        result = {'error': None, 'created': False, 'updated': False}

        try:
            guardian = student.guardian
            if not guardian:
                result['error'] = {
                    'student_id': str(student.id),
                    'student_name': student.full_name,
                    'error': '保護者が設定されていません'
                }
                return result

            confirmed, was_created = ConfirmedBilling.create_from_student_items(
                tenant_id=tenant_id,
                student=student,
                guardian=guardian,
                year=year,
                month=month,
                user=user
            )

            if confirmed.subtotal == 0:
                confirmed, was_created = ConfirmedBilling.create_from_contracts(
                    tenant_id=tenant_id,
                    student=student,
                    guardian=guardian,
                    year=year,
                    month=month,
                    user=user
                )

            if confirmed.subtotal == 0 and not confirmed.items_snapshot and not confirmed.discounts_snapshot:
                confirmed.delete()
                return result

            if was_created:
                result['created'] = True
            else:
                if confirmed.status == ConfirmedBilling.Status.PAID:
                    pass  # skipped
                else:
                    result['updated'] = True

        except Exception as e:
            result['error'] = {
                'student_id': str(student.id),
                'student_name': student.full_name,
                'error': str(e)
            }

        return result

    def _apply_mile_discounts(self, tenant_id, year, month):
        """マイル割引を適用（保護者単位で1回のみ）"""
        from apps.pricing.calculations import calculate_mile_discount

        billings = ConfirmedBilling.objects.filter(
            tenant_id=tenant_id,
            year=year,
            month=month,
            deleted_at__isnull=True
        ).select_related('student', 'guardian')

        guardian_billings = defaultdict(list)
        for b in billings:
            if b.guardian_id:
                guardian_billings[b.guardian_id].append(b)

        for guardian_id, family_billings in guardian_billings.items():
            if not family_billings:
                continue

            guardian = family_billings[0].guardian
            if not guardian:
                continue

            # 既存のマイル割引を削除
            for b in family_billings:
                discounts = b.discounts_snapshot or []
                new_discounts = [d for d in discounts if 'マイル' not in (d.get('discount_name', '') or '')]
                if len(new_discounts) != len(discounts):
                    b.discounts_snapshot = new_discounts

            mile_discount_amount, total_miles, mile_discount_name = calculate_mile_discount(guardian)

            if mile_discount_amount > 0:
                first_billing = family_billings[0]
                discounts = first_billing.discounts_snapshot or []
                discounts.append({
                    'discount_name': mile_discount_name,
                    'amount': str(mile_discount_amount),
                    'discount_unit': 'yen',
                    'source': 'mile_discount',
                    'total_miles': total_miles,
                    'is_family_discount': True,
                })
                first_billing.discounts_snapshot = discounts

            for b in family_billings:
                discounts = b.discounts_snapshot or []
                discount_total = sum(Decimal(str(d.get('amount', 0))) for d in discounts)
                total_amount = Decimal(str(b.subtotal)) - discount_total
                if total_amount < 0:
                    total_amount = Decimal('0')

                b.discount_total = discount_total
                b.total_amount = total_amount
                b.balance = total_amount - Decimal(str(b.paid_amount or 0))
                b.save(update_fields=['discounts_snapshot', 'discount_total', 'total_amount', 'balance'])

    @extend_schema(summary='締日確定一括処理')
    @action(detail=False, methods=['post'])
    def confirm_batch(self, request):
        """締日確定一括処理"""
        serializer = BillingConfirmBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data['year']
        month = data['month']
        close_deadline = data.get('close_deadline', True)

        tenant_id = _get_tenant_id(request)

        deadline, _ = MonthlyBillingDeadline.get_or_create_for_month(
            tenant_id=tenant_id,
            year=year,
            month=month
        )

        if deadline.is_closed:
            return Response({
                'error': f'{year}年{month}月分は既に締め済みです'
            }, status=400)

        create_result = self.create_confirmed_billing(request)

        if close_deadline:
            deadline.close_manually(request.user, f'一括確定処理により締め')

        return Response({
            'success': True,
            'year': year,
            'month': month,
            'billing_result': create_result.data,
            'deadline_closed': close_deadline,
            'is_closed': deadline.is_closed,
        })

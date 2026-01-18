"""
Billing Celery Tasks - 請求確定バックグラウンドタスク
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from decimal import Decimal
from collections import defaultdict
from django.db import models, transaction
from datetime import date

logger = get_task_logger(__name__)


@shared_task(bind=True, soft_time_limit=1800, time_limit=2400)
def generate_confirmed_billing_task(self, tenant_id, year, month, user_id=None):
    """請求確定データを生成するCeleryタスク

    Args:
        tenant_id: テナントID
        year: 請求年
        month: 請求月
        user_id: 実行ユーザーID（オプション）

    Returns:
        dict: 処理結果
    """
    from apps.billing.models import ConfirmedBilling
    from apps.students.models import Student
    from apps.contracts.models import Contract
    from apps.users.models import User
    from apps.pricing.calculations import calculate_mile_discount

    logger.info(f"Starting billing generation for {year}/{month}")

    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass

    # 対象月の開始日・終了日
    billing_start = date(year, month, 1)
    if month == 12:
        billing_end = date(year + 1, 1, 1)
    else:
        billing_end = date(year, month + 1, 1)

    # 対象生徒を取得
    student_ids_with_contracts = Contract.objects.filter(
        tenant_id=tenant_id,
        status=Contract.Status.ACTIVE,
        start_date__lt=billing_end,
    ).filter(
        models.Q(end_date__isnull=True) | models.Q(end_date__gte=billing_start)
    ).values_list('student_id', flat=True).distinct()

    students = Student.objects.filter(
        tenant_id=tenant_id,
        id__in=student_ids_with_contracts,
        deleted_at__isnull=True
    ).exclude(
        status__in=[Student.Status.SUSPENDED, Student.Status.WITHDRAWN]
    )

    total = students.count()
    logger.info(f"Target students: {total}")

    created_count = 0
    updated_count = 0
    error_count = 0
    errors = []

    # 生徒ごとに処理
    for i, student in enumerate(students):
        try:
            guardian = student.guardian
            if not guardian:
                error_count += 1
                errors.append(f"{student.full_name}: 保護者なし")
                continue

            # まずStudentItemから生成を試みる
            confirmed, was_created = ConfirmedBilling.create_from_student_items(
                tenant_id=tenant_id,
                student=student,
                guardian=guardian,
                year=year,
                month=month,
                user=user
            )

            # subtotalが0ならContractから生成
            if confirmed.subtotal == 0:
                confirmed, was_created = ConfirmedBilling.create_from_contracts(
                    tenant_id=tenant_id,
                    student=student,
                    guardian=guardian,
                    year=year,
                    month=month,
                    user=user
                )

            # 空の請求データは削除
            if confirmed.subtotal == 0 and not confirmed.items_snapshot and not confirmed.discounts_snapshot:
                confirmed.delete()
                continue

            if was_created:
                created_count += 1
            else:
                updated_count += 1

            # 進捗更新
            if (i + 1) % 500 == 0:
                self.update_state(
                    state='PROGRESS',
                    meta={'current': i + 1, 'total': total}
                )
                logger.info(f"Progress: {i + 1}/{total}")

        except Exception as e:
            error_count += 1
            errors.append(f"{student.full_name}: {str(e)[:100]}")
            logger.error(f"Error processing {student.full_name}: {e}")

    # マイル割引を適用
    logger.info("Applying mile discounts...")
    _apply_mile_discounts(tenant_id, year, month)

    # 最終集計
    final_billings = ConfirmedBilling.objects.filter(
        tenant_id=tenant_id,
        year=year,
        month=month
    )
    total_amount = sum(b.total_amount for b in final_billings)

    result = {
        'success': True,
        'year': year,
        'month': month,
        'created_count': created_count,
        'updated_count': updated_count,
        'error_count': error_count,
        'errors': errors[:10],
        'total_billings': final_billings.count(),
        'total_amount': float(total_amount),
    }

    logger.info(f"Billing generation completed: {result}")
    return result


def _apply_mile_discounts(tenant_id, year, month):
    """マイル割引を適用（保護者単位で1回のみ）"""
    from apps.billing.models import ConfirmedBilling
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

    with transaction.atomic():
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

            # マイル割引を計算
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

            # total_amountを再計算
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

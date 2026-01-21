"""
ConfirmedBillingService - 確定請求サービス

確定請求の生成、締め処理のビジネスロジック
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, List, Any, Tuple

from django.db import models, transaction
from django.utils import timezone

from apps.billing.models import (
    Invoice, GuardianBalance, PaymentProvider, MonthlyBillingDeadline,
    ConfirmedBilling
)
from apps.contracts.models import Contract
from apps.students.models import Student, Guardian

logger = logging.getLogger(__name__)


class ConfirmedBillingService:
    """確定請求サービス"""

    @classmethod
    def close_month(
        cls,
        tenant_id: str,
        year: int,
        month: int,
        notes: str = '',
        user=None
    ) -> Dict[str, Any]:
        """月次締め処理を実行

        Args:
            tenant_id: テナントID
            year: 年
            month: 月
            notes: 備考
            user: 操作ユーザー

        Returns:
            処理結果
        """
        # 締日取得
        default_closing_day = 25
        provider = PaymentProvider.objects.filter(
            tenant_id=tenant_id,
            is_active=True
        ).first()
        if provider:
            default_closing_day = provider.closing_day or 25

        deadline, _ = MonthlyBillingDeadline.get_or_create_for_month(
            tenant_id=tenant_id,
            year=year,
            month=month,
            closing_day=default_closing_day
        )

        if deadline.is_closed:
            raise ValueError('この月は既に締め済みです')

        # 対象月の開始日・終了日
        billing_start = date(year, month, 1)
        if month == 12:
            billing_end = date(year + 1, 1, 1)
        else:
            billing_end = date(year, month + 1, 1)

        # 該当月に有効な契約がある生徒を取得
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
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        guardian_billing_totals = {}

        with transaction.atomic():
            for student in students:
                try:
                    guardian = student.guardian
                    if not guardian:
                        skipped_count += 1
                        continue

                    # まずStudentItemから生成を試みる（入会時費用等）
                    confirmed, was_created = ConfirmedBilling.create_from_student_items(
                        tenant_id=tenant_id,
                        student=student,
                        guardian=guardian,
                        year=year,
                        month=month,
                        user=user
                    )

                    # subtotalが0ならContractから生成（月額費用）
                    if confirmed.subtotal == 0:
                        confirmed, was_created = ConfirmedBilling.create_from_contracts(
                            tenant_id=tenant_id,
                            student=student,
                            guardian=guardian,
                            year=year,
                            month=month,
                            user=user
                        )

                    # 空の請求確定データは削除
                    if confirmed.subtotal == 0 and not confirmed.items_snapshot and not confirmed.discounts_snapshot:
                        confirmed.delete()
                        skipped_count += 1
                        continue

                    if was_created:
                        created_count += 1
                        if guardian.id not in guardian_billing_totals:
                            guardian_billing_totals[guardian.id] = {
                                'guardian': guardian,
                                'total': Decimal('0'),
                            }
                        guardian_billing_totals[guardian.id]['total'] += confirmed.total_amount or Decimal('0')
                    else:
                        if confirmed.status == ConfirmedBilling.Status.PAID:
                            skipped_count += 1
                        else:
                            updated_count += 1

                except Exception as e:
                    errors.append(str(e))

            # 保護者ごとにGuardianBalanceを更新
            for guardian_id, data in guardian_billing_totals.items():
                if data['total'] > 0:
                    balance_obj, _ = GuardianBalance.objects.get_or_create(
                        tenant_id=tenant_id,
                        guardian=data['guardian'],
                        defaults={'balance': 0}
                    )
                    balance_obj.add_billing(
                        amount=data['total'],
                        reason=f'{year}年{month}月分請求確定',
                    )

            # 締める
            deadline.close_manually(user, notes)

            # 次月の請求データを自動生成
            next_month_result = cls._create_next_month_billings(
                tenant_id=tenant_id,
                year=year,
                month=month,
                closing_day=deadline.closing_day,
                user=user
            )

        return {
            'success': True,
            'message': f'{year}年{month}月分を締めました',
            'is_closed': deadline.is_closed,
            'created_count': created_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'error_count': len(errors),
            'next_month': next_month_result,
        }

    @classmethod
    def _create_next_month_billings(
        cls,
        tenant_id: str,
        year: int,
        month: int,
        closing_day: int,
        user=None
    ) -> Dict[str, Any]:
        """次月の請求データを自動生成"""
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1

        # 次月の締日を作成
        next_deadline, _ = MonthlyBillingDeadline.get_or_create_for_month(
            tenant_id=tenant_id,
            year=next_year,
            month=next_month,
            closing_day=closing_day
        )

        # 次月の請求対象期間
        next_billing_start = date(next_year, next_month, 1)
        if next_month == 12:
            next_billing_end = date(next_year + 1, 1, 1)
        else:
            next_billing_end = date(next_year, next_month + 1, 1)

        # 次月に有効な契約がある生徒を取得
        next_student_ids = Contract.objects.filter(
            tenant_id=tenant_id,
            status=Contract.Status.ACTIVE,
            start_date__lt=next_billing_end,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=next_billing_start)
        ).values_list('student_id', flat=True).distinct()

        next_students = Student.objects.filter(
            tenant_id=tenant_id,
            id__in=next_student_ids,
            deleted_at__isnull=True
        )

        next_created_count = 0
        next_skipped_count = 0

        for student in next_students:
            try:
                guardian = student.guardian
                if not guardian:
                    next_skipped_count += 1
                    continue

                confirmed, was_created = ConfirmedBilling.create_from_contracts(
                    tenant_id=tenant_id,
                    student=student,
                    guardian=guardian,
                    year=next_year,
                    month=next_month,
                    user=user
                )

                # 空の請求は削除
                if confirmed.subtotal == 0 and not confirmed.items_snapshot and not confirmed.discounts_snapshot:
                    confirmed.delete()
                    next_skipped_count += 1
                    continue

                if was_created:
                    next_created_count += 1
                else:
                    next_skipped_count += 1

            except Exception as e:
                logger.error(f'Error creating next month billing for student {student.id}: {e}')
                next_skipped_count += 1

        return {
            'year': next_year,
            'month': next_month,
            'created_count': next_created_count,
            'skipped_count': next_skipped_count,
        }

    @classmethod
    def create_for_student(
        cls,
        tenant_id: str,
        student: Student,
        guardian: Guardian,
        year: int,
        month: int,
        user=None
    ) -> Tuple[ConfirmedBilling, bool]:
        """生徒の確定請求を作成

        Args:
            tenant_id: テナントID
            student: 生徒
            guardian: 保護者
            year: 年
            month: 月
            user: 操作ユーザー

        Returns:
            (ConfirmedBilling, was_created)
        """
        return ConfirmedBilling.create_from_contracts(
            tenant_id=tenant_id,
            student=student,
            guardian=guardian,
            year=year,
            month=month,
            user=user
        )

    @classmethod
    def start_review(
        cls,
        deadline: MonthlyBillingDeadline,
        user=None
    ) -> MonthlyBillingDeadline:
        """月を確認中にする"""
        if deadline.is_closed:
            raise ValueError('この月は既に確定済みです')

        if deadline.is_under_review:
            raise ValueError('この月は既に確認中です')

        deadline.start_review(user)
        return deadline

    @classmethod
    def cancel_review(
        cls,
        deadline: MonthlyBillingDeadline,
        user=None
    ) -> MonthlyBillingDeadline:
        """確認中を解除"""
        if not deadline.is_under_review:
            raise ValueError('この月は確認中ではありません')

        deadline.cancel_review(user)
        return deadline

    @classmethod
    def reopen_month(
        cls,
        deadline: MonthlyBillingDeadline,
        reason: str,
        user=None
    ) -> MonthlyBillingDeadline:
        """締めを解除する"""
        if not deadline.is_closed:
            raise ValueError('この月は締め済みではありません')

        if not reason:
            raise ValueError('締め解除には理由が必要です')

        deadline.reopen(user, reason)
        return deadline

    @classmethod
    def get_status_list(
        cls,
        tenant_id: str,
        range_months: int = 10
    ) -> Dict[str, Any]:
        """締切状態一覧を取得

        Args:
            tenant_id: テナントID
            range_months: 取得範囲（前後の月数）

        Returns:
            {'currentYear': int, 'currentMonth': int, 'billingYear': int, 'billingMonth': int, 'months': list}
        """
        today = date.today()

        # デフォルト締日を取得
        default_closing_day = 25
        provider = PaymentProvider.objects.filter(
            tenant_id=tenant_id,
            is_active=True
        ).first()
        if provider:
            default_closing_day = provider.closing_day or 25

        # 請求対象月の最小値を計算
        if today.day < default_closing_day:
            min_billing_month = today.month + 1
        else:
            min_billing_month = today.month + 2
        min_billing_year = today.year
        if min_billing_month > 12:
            min_billing_month -= 12
            min_billing_year += 1

        months = []
        first_open_found = False
        current_billing_year = None
        current_billing_month = None

        for offset in range(-3, 7):
            year = today.year
            month = today.month + offset
            while month <= 0:
                month += 12
                year -= 1
            while month > 12:
                month -= 12
                year += 1

            deadline, created = MonthlyBillingDeadline.get_or_create_for_month(
                tenant_id=tenant_id,
                year=year,
                month=month,
                closing_day=default_closing_day
            )

            is_current = False
            if not first_open_found and not deadline.is_closed:
                if (year > min_billing_year) or (year == min_billing_year and month >= min_billing_month):
                    is_current = True
                    first_open_found = True
                    current_billing_year = year
                    current_billing_month = month

            months.append({
                'id': str(deadline.id),
                'year': deadline.year,
                'month': deadline.month,
                'label': f'{deadline.year}年{deadline.month}月分',
                'closingDay': deadline.closing_day,
                'closingDate': deadline.closing_date.strftime('%Y-%m-%d'),
                'status': deadline.status,
                'statusDisplay': deadline.status_display,
                'isClosed': deadline.is_closed,
                'isUnderReview': deadline.is_under_review,
                'canEdit': deadline.can_edit,
                'isManuallyClosed': deadline.is_manually_closed,
                'isReopened': deadline.is_reopened,
                'isCurrent': is_current,
            })

        return {
            'currentYear': today.year,
            'currentMonth': today.month,
            'billingYear': current_billing_year,
            'billingMonth': current_billing_month,
            'defaultClosingDay': default_closing_day,
            'months': months,
        }

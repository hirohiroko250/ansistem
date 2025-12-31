"""
Invoice Billing Mixin - 締日期間確定機能
"""
import logging
from datetime import date

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.billing.models import Invoice, ConfirmedBilling

logger = logging.getLogger(__name__)


class InvoiceBillingMixin:
    """請求書締日期間確定機能"""

    @extend_schema(summary='締日期間確定')
    @action(detail=False, methods=['post'], url_path='close_period')
    def close_period(self, request):
        """締日期間を確定（請求データをロック）

        確定ボタンを押したタイミングで、前回確定から現在までのデータを確定する。
        締め日は10日固定。
        """
        from dateutil.relativedelta import relativedelta
        from apps.students.models import Student
        from apps.contracts.models import StudentItem

        tenant_id = request.user.tenant_id
        today = date.today()
        closing_day = 10  # 締め日は10日固定

        try:
            # 前回の確定日を取得（ConfirmedBillingの最新confirmed_at）
            last_confirmed = ConfirmedBilling.objects.filter(
                tenant_id=tenant_id
            ).order_by('-confirmed_at').first()

            if last_confirmed:
                # 前回確定日の翌日から
                start_date = last_confirmed.confirmed_at.date() + relativedelta(days=1)
            else:
                # 初回の場合は最初の請求データから
                first_invoice = Invoice.objects.filter(
                    tenant_id=tenant_id
                ).order_by('created_at').first()
                if first_invoice:
                    start_date = first_invoice.created_at.date()
                else:
                    start_date = today - relativedelta(months=1)

            end_date = today

            # 締め日（10日）を基準に請求月を計算
            # 例: 11/11〜12/10 は12月請求分、12/11〜1/10 は1月請求分
            if today.day <= closing_day:
                # 今月分
                billing_year = today.year
                billing_month = today.month
            else:
                # 翌月分
                next_month = today + relativedelta(months=1)
                billing_year = next_month.year
                billing_month = next_month.month

            # 未確定の請求書からConfirmedBillingを作成
            confirmed_count = self._create_confirmed_billings(
                tenant_id, billing_year, billing_month, request.user
            )

            # 対象請求書をロック
            locked_count = Invoice.objects.filter(
                tenant_id=tenant_id,
                billing_year=billing_year,
                billing_month=billing_month,
                is_locked=False,
            ).update(
                is_locked=True,
                locked_at=timezone.now(),
                locked_by=request.user,
            )

            return Response({
                'success': True,
                'message': f'{billing_year}年{billing_month}月分の締め確定が完了しました',
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                },
                'billing_year': billing_year,
                'billing_month': billing_month,
                'confirmed_billings': confirmed_count,
                'locked_invoices': locked_count,
            })

        except Exception as e:
            logger.error(f'Failed to close period: {e}')
            return Response(
                {'error': f'締め確定に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _create_confirmed_billings(self, tenant_id, billing_year, billing_month, user):
        """未確定の請求書からConfirmedBillingを作成"""
        from apps.students.models import Student
        from apps.contracts.models import StudentItem

        students = Student.objects.filter(
            tenant_id=tenant_id,
            status='active'
        ).select_related('guardian')

        confirmed_count = 0
        for student in students:
            # 既にこの月の確定データがあればスキップ
            existing = ConfirmedBilling.objects.filter(
                tenant_id=tenant_id,
                student=student,
                year=billing_year,
                month=billing_month
            ).first()
            if existing:
                continue

            # 生徒の請求項目を取得
            student_items = StudentItem.objects.filter(
                student=student,
                is_active=True
            ).select_related('product')

            if not student_items.exists():
                continue

            # 請求金額を計算
            subtotal = sum(item.unit_price * item.quantity for item in student_items)
            discount_total = 0  # 割引計算は必要に応じて追加
            tax_amount = 0  # 税額計算は必要に応じて追加
            total_amount = subtotal - discount_total + tax_amount

            # スナップショット作成
            items_snapshot = [
                {
                    'product_id': str(item.product.id),
                    'product_name': item.product.name,
                    'category': item.product.get_item_type_display(),
                    'unit_price': int(item.unit_price),
                    'quantity': item.quantity,
                    'amount': int(item.unit_price * item.quantity),
                }
                for item in student_items
            ]

            # ConfirmedBilling作成
            ConfirmedBilling.objects.create(
                tenant_id=tenant_id,
                student=student,
                guardian=student.guardian,
                year=billing_year,
                month=billing_month,
                subtotal=subtotal,
                discount_total=discount_total,
                tax_amount=tax_amount,
                total_amount=total_amount,
                items_snapshot=items_snapshot,
                discounts_snapshot=[],
                status=ConfirmedBilling.Status.CONFIRMED,
                payment_method=ConfirmedBilling.PaymentMethod.DIRECT_DEBIT,
                confirmed_at=timezone.now(),
                confirmed_by=user,
            )
            confirmed_count += 1

        return confirmed_count

"""
Invoice Import Mixin - CSVインポート機能
"""
import csv
import io
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.billing.models import (
    Invoice, Payment, GuardianBalance, ConfirmedBilling, DirectDebitResult,
)


class InvoiceImportMixin:
    """請求書CSVインポート機能"""

    @extend_schema(summary='引落結果CSVインポート')
    @action(detail=False, methods=['post'], url_path='import-debit-result')
    def import_debit_result(self, request):
        """引落結果CSVを取り込み、請求書と入金を更新"""
        from apps.students.models import Guardian

        file = request.FILES.get('file')
        if not file:
            return Response(
                {'success': False, 'imported': 0, 'errors': ['ファイルが指定されていません']},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # CSVを読み込み（Shift-JIS想定）
            content = file.read().decode('shift_jis')
            reader = csv.DictReader(io.StringIO(content))

            imported = 0
            errors = []

            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        result = self._process_debit_result_row(request, row, row_num)
                        if result['success']:
                            imported += 1
                        else:
                            errors.append(result['error'])
                    except Exception as e:
                        errors.append(f"行{row_num}: {str(e)}")

            return Response({
                'success': len(errors) == 0,
                'imported': imported,
                'errors': errors
            })

        except Exception as e:
            return Response(
                {'success': False, 'imported': 0, 'errors': [str(e)]},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _process_debit_result_row(self, request, row, row_num):
        """引落結果の1行を処理"""
        from apps.students.models import Guardian

        customer_code = row.get('顧客番号', '').strip()
        result_code = row.get('結果コード', '').strip()
        amount = row.get('引落金額', '0').strip()
        invoice_no = row.get('備考', '').strip()

        # 保護者を検索
        guardian = Guardian.objects.filter(
            tenant_id=request.user.tenant_id,
            guardian_no=customer_code
        ).first()

        if not guardian:
            return {'success': False, 'error': f"行{row_num}: 顧客番号 {customer_code} が見つかりません"}

        # 請求書を検索
        invoice = Invoice.objects.filter(
            tenant_id=request.user.tenant_id,
            invoice_no=invoice_no,
            guardian=guardian
        ).first()

        # 結果ステータスを判定
        if result_code == '0':
            result_status = DirectDebitResult.ResultStatus.SUCCESS
            failure_reason = ''
        elif result_code == '1':
            result_status = DirectDebitResult.ResultStatus.FAILED
            failure_reason = DirectDebitResult.FailureReason.INSUFFICIENT_FUNDS
        else:
            result_status = DirectDebitResult.ResultStatus.FAILED
            failure_reason = DirectDebitResult.FailureReason.OTHER

        # 引落結果を記録
        debit_result = DirectDebitResult.objects.create(
            tenant_id=request.user.tenant_id,
            guardian=guardian,
            invoice=invoice,
            debit_date=timezone.now().date(),
            amount=Decimal(amount) if amount else 0,
            result_status=result_status,
            failure_reason=failure_reason,
        )

        # 成功時は入金処理
        if result_status == DirectDebitResult.ResultStatus.SUCCESS:
            self._process_successful_debit(request, guardian, invoice, amount, debit_result)

        return {'success': True}

    def _process_successful_debit(self, request, guardian, invoice, amount, debit_result):
        """成功した引落の入金処理"""
        payment_amount = Decimal(amount) if amount else Decimal('0')

        payment = Payment.objects.create(
            tenant_id=request.user.tenant_id,
            payment_no=Payment.generate_payment_no(request.user.tenant_id),
            guardian=guardian,
            invoice=invoice,
            payment_date=timezone.now().date(),
            amount=payment_amount,
            method=Payment.Method.DIRECT_DEBIT,
            status=Payment.Status.SUCCESS,
            notes=f"引落結果取込: {debit_result.id}",
            registered_by=request.user,
        )
        if invoice:
            payment.apply_to_invoice()

        # ConfirmedBillingも更新
        self._update_confirmed_billings(guardian, payment_amount)

        # GuardianBalanceに入金を記録
        balance_obj, _ = GuardianBalance.objects.get_or_create(
            tenant_id=request.user.tenant_id,
            guardian=guardian,
            defaults={'balance': 0}
        )
        balance_obj.add_payment(
            amount=payment_amount,
            reason=f'口座振替による入金',
            payment=payment,
        )

    def _update_confirmed_billings(self, guardian, payment_amount):
        """ConfirmedBillingの入金処理"""
        confirmed_billings = ConfirmedBilling.objects.filter(
            guardian=guardian,
            status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL],
        ).order_by(
            models.Case(
                models.When(balance=payment_amount, then=0),
                default=1,
            ),
            'year',
            'month',
        )

        remaining_amount = payment_amount
        for cb in confirmed_billings:
            if remaining_amount <= 0:
                break
            apply_amount = min(remaining_amount, cb.balance)
            if apply_amount > 0:
                cb.paid_amount += apply_amount
                cb.balance = cb.total_amount - cb.paid_amount
                if cb.balance <= 0:
                    cb.status = ConfirmedBilling.Status.PAID
                    cb.paid_at = timezone.now()
                elif cb.paid_amount > 0:
                    cb.status = ConfirmedBilling.Status.PARTIAL
                cb.save()
                remaining_amount -= apply_amount

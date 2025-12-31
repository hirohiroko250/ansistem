"""
BankTransferImport Confirm Mixin - 確定機能
"""
from django.db import models, transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.billing.models import (
    Invoice, Payment, GuardianBalance, ConfirmedBilling, BankTransfer,
)


class BankTransferImportConfirmMixin:
    """振込インポート確定機能"""

    @extend_schema(summary='インポートバッチを確定')
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """インポートバッチを確定し、照合済みの振込を入金処理する"""
        import_batch = self.get_object()

        if import_batch.confirmed_at:
            return Response({'error': 'このバッチは既に確定済みです'}, status=400)

        matched_transfers = BankTransfer.objects.filter(
            import_batch_id=str(import_batch.id),
            status=BankTransfer.Status.MATCHED,
            guardian__isnull=False,
        )

        applied_count = 0
        errors = []

        with transaction.atomic():
            for transfer in matched_transfers:
                try:
                    self._apply_transfer_payment(transfer, import_batch, request.user)
                    applied_count += 1
                except Exception as e:
                    errors.append({
                        'transfer_id': str(transfer.id),
                        'payer_name': transfer.payer_name,
                        'error': str(e),
                    })

            import_batch.confirm(request.user)
            import_batch.update_counts()

        return Response({
            'success': True,
            'applied_count': applied_count,
            'error_count': len(errors),
            'errors': errors[:10],
        })

    def _apply_transfer_payment(self, transfer, import_batch, user):
        """振込を入金処理する"""
        # 請求書を検索
        invoice = Invoice.objects.filter(
            guardian=transfer.guardian,
            status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE],
        ).order_by(
            models.Case(
                models.When(balance_due=transfer.amount, then=0),
                default=1,
            ),
            'billing_year',
            'billing_month',
        ).first()

        # 入金を作成
        payment_no = Payment.generate_payment_no(transfer.tenant_id)
        payment = Payment.objects.create(
            tenant_id=transfer.tenant_id,
            payment_no=payment_no,
            guardian=transfer.guardian,
            invoice=invoice,
            payment_date=transfer.transfer_date,
            amount=transfer.amount,
            method=Payment.Method.BANK_TRANSFER,
            status=Payment.Status.SUCCESS,
            payer_name=transfer.payer_name,
            bank_name=transfer.source_bank_name,
            notes=f'振込インポート確定: {import_batch.batch_no}',
            registered_by=user,
        )

        # 請求書を更新
        if invoice:
            invoice.paid_amount += transfer.amount
            invoice.balance_due = invoice.total_amount - invoice.paid_amount
            if invoice.balance_due <= 0:
                invoice.status = Invoice.Status.PAID
            elif invoice.paid_amount > 0:
                invoice.status = Invoice.Status.PARTIAL
            invoice.save()
            transfer.invoice = invoice

        # ConfirmedBillingを更新
        self._update_confirmed_billings(transfer)

        # 預り金残高を更新
        balance_obj, _ = GuardianBalance.objects.get_or_create(
            tenant_id=transfer.tenant_id,
            guardian=transfer.guardian,
            defaults={'balance': 0}
        )
        balance_obj.add_payment(
            amount=transfer.amount,
            reason=f'銀行振込による入金（{transfer.payer_name}）',
            payment=payment,
        )

        # 振込ステータスを更新
        transfer.status = BankTransfer.Status.APPLIED
        transfer.save()

    def _update_confirmed_billings(self, transfer):
        """ConfirmedBillingの入金処理"""
        confirmed_billings = ConfirmedBilling.objects.filter(
            guardian=transfer.guardian,
            status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL],
        ).order_by(
            models.Case(
                models.When(balance=transfer.amount, then=0),
                default=1,
            ),
            'year',
            'month',
        )

        remaining_amount = transfer.amount
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

"""
PaymentService - 入金サービス

入金処理、消込、口座振替結果処理のビジネスロジック
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, List, Any

from django.db import models, transaction
from django.utils import timezone

from apps.billing.models import (
    Invoice, Payment, GuardianBalance, ConfirmedBilling, DirectDebitResult
)
from apps.students.models import Guardian

logger = logging.getLogger(__name__)


class PaymentService:
    """入金サービス"""

    @staticmethod
    def generate_payment_no(tenant_id: str) -> str:
        """入金番号を生成"""
        return Payment.generate_payment_no(tenant_id)

    @classmethod
    def register_payment(
        cls,
        tenant_id: str,
        guardian_id: str,
        payment_date: date,
        amount: Decimal,
        method: str,
        invoice_id: Optional[str] = None,
        payer_name: str = '',
        bank_name: str = '',
        notes: str = '',
        user=None
    ) -> Payment:
        """入金を登録

        Args:
            tenant_id: テナントID
            guardian_id: 保護者ID
            payment_date: 入金日
            amount: 金額
            method: 入金方法
            invoice_id: 請求書ID（オプション）
            payer_name: 振込人名
            bank_name: 銀行名
            notes: 備考
            user: 操作ユーザー

        Returns:
            Payment
        """
        with transaction.atomic():
            payment = Payment.objects.create(
                tenant_id=tenant_id,
                payment_no=cls.generate_payment_no(tenant_id),
                guardian_id=guardian_id,
                invoice_id=invoice_id,
                payment_date=payment_date,
                amount=amount,
                method=method,
                status=Payment.Status.SUCCESS,
                payer_name=payer_name,
                bank_name=bank_name,
                notes=notes,
                registered_by=user,
            )

            # 請求書に入金を適用
            payment.apply_to_invoice()

            # ConfirmedBillingも更新
            guardian = Guardian.objects.get(id=guardian_id)
            cls._apply_to_confirmed_billings(guardian, amount)

            # GuardianBalanceに入金を記録
            balance_obj, _ = GuardianBalance.objects.get_or_create(
                tenant_id=tenant_id,
                guardian=guardian,
                defaults={'balance': 0}
            )
            balance_obj.add_payment(
                amount=amount,
                reason='手動入金登録',
                payment=payment,
            )

        return payment

    @classmethod
    def create_payment_from_debit_result(
        cls,
        tenant_id: str,
        guardian: Guardian,
        invoice: Optional[Invoice],
        amount: Decimal,
        debit_result: DirectDebitResult,
        user=None
    ) -> Payment:
        """口座振替結果から入金を作成

        Args:
            tenant_id: テナントID
            guardian: 保護者
            invoice: 請求書（オプション）
            amount: 金額
            debit_result: 引落結果
            user: 操作ユーザー

        Returns:
            Payment
        """
        with transaction.atomic():
            payment = Payment.objects.create(
                tenant_id=tenant_id,
                payment_no=cls.generate_payment_no(tenant_id),
                guardian=guardian,
                invoice=invoice,
                payment_date=timezone.now().date(),
                amount=amount,
                method=Payment.Method.DIRECT_DEBIT,
                status=Payment.Status.SUCCESS,
                notes=f"引落結果取込: {debit_result.id}",
                registered_by=user,
            )

            if invoice:
                payment.apply_to_invoice()

            cls._apply_to_confirmed_billings(guardian, amount)

            balance_obj, _ = GuardianBalance.objects.get_or_create(
                tenant_id=tenant_id,
                guardian=guardian,
                defaults={'balance': 0}
            )
            balance_obj.add_payment(
                amount=amount,
                reason='口座振替による入金',
                payment=payment,
            )

        return payment

    @classmethod
    def apply_debit_result(
        cls,
        tenant_id: str,
        payment: Payment,
        result_code: str,
        result_message: str = '',
        user=None
    ) -> Payment:
        """口座振替結果を適用

        Args:
            tenant_id: テナントID
            payment: 入金
            result_code: 結果コード
            result_message: 結果メッセージ
            user: 操作ユーザー

        Returns:
            Payment
        """
        payment.debit_result_code = result_code
        payment.debit_result_message = result_message

        with transaction.atomic():
            if result_code == '0':  # 成功
                payment.status = Payment.Status.SUCCESS
                payment.apply_to_invoice()

                if payment.guardian:
                    cls._apply_to_confirmed_billings(payment.guardian, payment.amount)

                    balance_obj, _ = GuardianBalance.objects.get_or_create(
                        tenant_id=tenant_id,
                        guardian=payment.guardian,
                        defaults={'balance': 0}
                    )
                    balance_obj.add_payment(
                        amount=payment.amount,
                        reason='口座振替による入金',
                        payment=payment,
                    )
            else:
                payment.status = Payment.Status.FAILED

            payment.save()

        return payment

    @classmethod
    def match_payment_to_invoice(
        cls,
        payment: Payment,
        invoice: Invoice,
        user=None
    ) -> Dict[str, Any]:
        """入金を請求書に消込

        Args:
            payment: 入金
            invoice: 請求書
            user: 操作ユーザー

        Returns:
            {'success': bool, 'payment': Payment, 'invoice': Invoice}
        """
        if payment.invoice:
            raise ValueError('この入金は既に消込済みです')

        with transaction.atomic():
            payment.invoice = invoice
            payment.guardian = invoice.guardian
            payment.save()

            payment.apply_to_invoice()

            if invoice.guardian:
                cls._apply_to_confirmed_billings(invoice.guardian, payment.amount)

        return {
            'success': True,
            'payment': payment,
            'invoice': invoice
        }

    @classmethod
    def get_match_candidates(
        cls,
        tenant_id: str,
        payment: Payment
    ) -> List[Dict[str, Any]]:
        """入金に対する消込候補を取得

        Args:
            tenant_id: テナントID
            payment: 入金

        Returns:
            消込候補リスト
        """
        from apps.billing.serializers import InvoiceSerializer

        candidates = []

        # 金額で一致する請求書を探す
        amount_matches = Invoice.objects.filter(
            tenant_id=tenant_id,
            status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL],
            balance_due=payment.amount
        ).select_related('guardian')

        for invoice in amount_matches:
            candidates.append({
                'invoice': InvoiceSerializer(invoice).data,
                'match_type': 'amount',
                'match_score': 100,
                'match_reason': f'金額完全一致（¥{payment.amount:,.0f}）'
            })

        # 振込名義からカナ検索
        if payment.payer_name:
            payer_kana = payment.payer_name.strip()
            name_matches = Guardian.objects.filter(
                tenant_id=tenant_id,
                full_name_kana__icontains=payer_kana
            )

            for guardian in name_matches:
                guardian_invoices = Invoice.objects.filter(
                    guardian=guardian,
                    status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL]
                )
                for invoice in guardian_invoices:
                    existing_ids = [c['invoice']['id'] for c in candidates]
                    if str(invoice.id) not in existing_ids:
                        score = 80
                        if invoice.balance_due == payment.amount:
                            score = 100
                        candidates.append({
                            'invoice': InvoiceSerializer(invoice).data,
                            'match_type': 'name',
                            'match_score': score,
                            'match_reason': f'振込名義一致（{payer_kana}）'
                        })

        candidates.sort(key=lambda x: x['match_score'], reverse=True)
        return candidates[:20]

    @classmethod
    def get_unmatched_payments(cls, tenant_id: str) -> List[Payment]:
        """未消込入金一覧を取得"""
        return Payment.objects.filter(
            tenant_id=tenant_id,
            invoice__isnull=True,
            status__in=[Payment.Status.SUCCESS, Payment.Status.PENDING]
        ).select_related('guardian').order_by('-payment_date')

    @classmethod
    def _apply_to_confirmed_billings(cls, guardian: Guardian, amount: Decimal) -> None:
        """確定請求に入金を適用"""
        confirmed_billings = ConfirmedBilling.objects.filter(
            guardian=guardian,
            status__in=[
                ConfirmedBilling.Status.CONFIRMED,
                ConfirmedBilling.Status.UNPAID,
                ConfirmedBilling.Status.PARTIAL
            ],
        ).order_by(
            models.Case(
                models.When(balance=amount, then=0),
                default=1,
            ),
            'year',
            'month',
        )

        remaining_amount = amount
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

"""
BalanceService - 預り金サービス

預り金の入金、相殺、残高管理のビジネスロジック
"""
import logging
from decimal import Decimal
from typing import Optional, Dict, Any

from django.db import transaction
from django.utils import timezone

from apps.billing.models import (
    Invoice, Payment, GuardianBalance, OffsetLog
)
from apps.students.models import Guardian

logger = logging.getLogger(__name__)


class BalanceService:
    """預り金サービス"""

    @classmethod
    def get_balance(cls, tenant_id: str, guardian_id: str) -> Dict[str, Any]:
        """保護者の預り金残高を取得

        Args:
            tenant_id: テナントID
            guardian_id: 保護者ID

        Returns:
            {'guardian_id': str, 'balance': int, 'last_updated': str or None}
        """
        balance = GuardianBalance.objects.filter(
            tenant_id=tenant_id,
            guardian_id=guardian_id
        ).first()

        if balance:
            return {
                'guardian_id': str(guardian_id),
                'balance': int(balance.balance),
                'last_updated': balance.last_updated.isoformat() if balance.last_updated else None,
            }
        else:
            return {
                'guardian_id': str(guardian_id),
                'balance': 0,
                'last_updated': None,
            }

    @classmethod
    def deposit(
        cls,
        tenant_id: str,
        guardian_id: str,
        amount: Decimal,
        reason: str = '',
        user=None
    ) -> GuardianBalance:
        """預り金に入金

        Args:
            tenant_id: テナントID
            guardian_id: 保護者ID
            amount: 金額
            reason: 理由
            user: 操作ユーザー

        Returns:
            GuardianBalance
        """
        with transaction.atomic():
            balance, created = GuardianBalance.objects.get_or_create(
                tenant_id=tenant_id,
                guardian_id=guardian_id,
                defaults={'balance': Decimal('0')}
            )
            balance.add_balance(amount, reason)

        return balance

    @classmethod
    def offset(
        cls,
        tenant_id: str,
        guardian_id: str,
        invoice_id: str,
        amount: Decimal,
        user=None
    ) -> Dict[str, Any]:
        """預り金を請求書に相殺

        Args:
            tenant_id: テナントID
            guardian_id: 保護者ID
            invoice_id: 請求書ID
            amount: 金額
            user: 操作ユーザー

        Returns:
            {'success': bool, 'balance': GuardianBalance, 'invoice': Invoice}

        Raises:
            ValueError: 残高不足など
        """
        balance = GuardianBalance.objects.filter(
            guardian_id=guardian_id,
            tenant_id=tenant_id
        ).first()

        if not balance:
            raise ValueError('預り金残高が見つかりません')

        invoice = Invoice.objects.filter(
            id=invoice_id,
            tenant_id=tenant_id
        ).first()

        if not invoice:
            raise ValueError('請求書が見つかりません')

        with transaction.atomic():
            balance.use_balance(
                amount,
                invoice=invoice,
                reason=f'請求書 {invoice.invoice_no} への相殺'
            )

            # 相殺入金を作成
            Payment.objects.create(
                tenant_id=tenant_id,
                payment_no=Payment.generate_payment_no(tenant_id),
                guardian=invoice.guardian,
                invoice=invoice,
                payment_date=timezone.now().date(),
                amount=amount,
                method=Payment.Method.OFFSET,
                status=Payment.Status.SUCCESS,
                notes='預り金からの相殺',
                registered_by=user,
            )

            # 請求書の入金額を更新
            invoice.paid_amount += amount
            invoice.balance_due = invoice.total_amount - invoice.paid_amount
            if invoice.balance_due <= 0:
                invoice.status = Invoice.Status.PAID
            elif invoice.paid_amount > 0:
                invoice.status = Invoice.Status.PARTIAL
            invoice.save()

        return {
            'success': True,
            'balance': balance,
            'invoice': invoice
        }

    @classmethod
    def get_passbook(
        cls,
        tenant_id: str,
        guardian: Guardian,
        limit: int = 50
    ) -> Dict[str, Any]:
        """保護者の通帳（入出金履歴）を取得

        Args:
            tenant_id: テナントID
            guardian: 保護者
            limit: 取得件数上限

        Returns:
            {'guardian_id': str, 'guardian_name': str, 'current_balance': int, 'transactions': list}
        """
        logs = OffsetLog.objects.filter(
            tenant_id=tenant_id,
            guardian=guardian
        ).select_related('invoice', 'payment').order_by('-created_at')[:limit]

        balance_obj = GuardianBalance.objects.filter(guardian=guardian).first()
        current_balance = int(balance_obj.balance) if balance_obj else 0

        transactions = []
        for log in logs:
            transactions.append({
                'id': str(log.id),
                'date': log.created_at.isoformat(),
                'type': log.log_type,
                'amount': int(log.amount),
                'balance_after': int(log.balance_after) if log.balance_after else None,
                'reason': log.reason,
                'invoice_no': log.invoice.invoice_no if log.invoice else None,
            })

        return {
            'guardian_id': str(guardian.id),
            'guardian_name': guardian.full_name,
            'current_balance': current_balance,
            'transactions': transactions
        }

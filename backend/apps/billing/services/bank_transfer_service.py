"""
BankTransferService - 振込入金サービス

振込照合、入金処理、CSVインポートのビジネスロジック
"""
import csv
import io
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any

from django.db import models, transaction
from django.utils import timezone

from apps.billing.models import (
    Invoice, Payment, GuardianBalance, ConfirmedBilling,
    BankTransfer, BankTransferImport
)
from apps.students.models import Guardian

logger = logging.getLogger(__name__)


class BankTransferService:
    """振込入金サービス"""

    @classmethod
    def match_to_guardian(
        cls,
        transfer: BankTransfer,
        guardian: Guardian,
        user=None
    ) -> BankTransfer:
        """振込を保護者に照合

        Args:
            transfer: 振込
            guardian: 保護者
            user: 操作ユーザー

        Returns:
            BankTransfer
        """
        if transfer.status not in [BankTransfer.Status.PENDING, BankTransfer.Status.UNMATCHED]:
            raise ValueError('この振込は既に照合済みです')

        transfer.match_to_guardian(guardian, user)
        return transfer

    @classmethod
    def apply_transfer(
        cls,
        transfer: BankTransfer,
        invoice: Optional[Invoice] = None,
        user=None
    ) -> Dict[str, Any]:
        """振込を請求書に適用し入金処理

        Args:
            transfer: 振込
            invoice: 請求書（オプション）
            user: 操作ユーザー

        Returns:
            {'success': bool, 'transfer': BankTransfer, 'payment_id': str, 'matched_to_invoice': bool}
        """
        if transfer.status == BankTransfer.Status.APPLIED:
            raise ValueError('この振込は既に入金処理済みです')

        guardian = invoice.guardian if invoice else transfer.guardian
        if not guardian:
            raise ValueError('保護者が照合されていません。先に照合してください。')

        with transaction.atomic():
            payment_no = Payment.generate_payment_no(transfer.tenant_id)
            payment = Payment.objects.create(
                tenant_id=transfer.tenant_id,
                payment_no=payment_no,
                guardian=guardian,
                invoice=invoice,
                payment_date=transfer.transfer_date,
                amount=transfer.amount,
                method=Payment.Method.BANK_TRANSFER,
                status=Payment.Status.SUCCESS if invoice else Payment.Status.PENDING,
                payer_name=transfer.payer_name,
                bank_name=transfer.source_bank_name,
                notes=f'振込インポート: {transfer.import_batch_id}',
                registered_by=user,
            )

            if invoice:
                invoice.paid_amount += transfer.amount
                invoice.balance_due = invoice.total_amount - invoice.paid_amount
                if invoice.balance_due <= 0:
                    invoice.status = Invoice.Status.PAID
                elif invoice.paid_amount > 0:
                    invoice.status = Invoice.Status.PARTIAL
                invoice.save()

                transfer.apply_to_invoice(invoice, user)
                message = '入金処理を完了しました（消込済み）'
            else:
                transfer.status = BankTransfer.Status.APPLIED
                if not transfer.matched_at:
                    transfer.matched_by = user
                    transfer.matched_at = timezone.now()
                transfer.save()
                message = '入金確認を完了しました（未消込）'

            # ConfirmedBillingも更新
            cls._apply_to_confirmed_billings(guardian, transfer.amount)

            # GuardianBalanceに入金を記録
            balance_obj, _ = GuardianBalance.objects.get_or_create(
                tenant_id=transfer.tenant_id,
                guardian=guardian,
                defaults={'balance': 0}
            )
            balance_obj.add_payment(
                amount=transfer.amount,
                reason=f'銀行振込による入金（{transfer.payer_name}）',
                payment=payment,
            )

            # バッチのカウント更新
            if transfer.import_batch_id:
                try:
                    import_batch = BankTransferImport.objects.get(id=transfer.import_batch_id)
                    import_batch.update_counts()
                except BankTransferImport.DoesNotExist:
                    pass

        return {
            'success': True,
            'message': message,
            'transfer': transfer,
            'payment_id': str(payment.id),
            'matched_to_invoice': invoice is not None,
        }

    @classmethod
    def bulk_match(
        cls,
        matches: List[Dict[str, Any]],
        user=None
    ) -> List[Dict[str, Any]]:
        """複数の振込を一括で照合

        Args:
            matches: [{'transfer_id': str, 'guardian_id': str, 'invoice_id': str?, 'apply_payment': bool?}]
            user: 操作ユーザー

        Returns:
            [{'transfer_id': str, 'success': bool, 'error': str?}]
        """
        results = []

        with transaction.atomic():
            for match_data in matches:
                try:
                    transfer = BankTransfer.objects.get(id=match_data['transfer_id'])
                    guardian = Guardian.objects.get(id=match_data['guardian_id'])

                    if match_data.get('apply_payment') and match_data.get('invoice_id'):
                        invoice = Invoice.objects.get(id=match_data['invoice_id'])
                        payment = Payment.objects.create(
                            tenant_id=transfer.tenant_id,
                            payment_no=Payment.generate_payment_no(transfer.tenant_id),
                            guardian=guardian,
                            invoice=invoice,
                            payment_date=transfer.transfer_date,
                            amount=transfer.amount,
                            method=Payment.Method.BANK_TRANSFER,
                            status=Payment.Status.SUCCESS,
                            payer_name=transfer.payer_name,
                            bank_name=transfer.source_bank_name,
                            notes=f'振込インポート: {transfer.import_batch_id}',
                            registered_by=user,
                        )
                        invoice.paid_amount += transfer.amount
                        invoice.balance_due = invoice.total_amount - invoice.paid_amount
                        if invoice.balance_due <= 0:
                            invoice.status = Invoice.Status.PAID
                        elif invoice.paid_amount > 0:
                            invoice.status = Invoice.Status.PARTIAL
                        invoice.save()
                        transfer.apply_to_invoice(invoice, user)
                    else:
                        transfer.match_to_guardian(guardian, user)

                    results.append({
                        'transfer_id': str(transfer.id),
                        'success': True,
                    })

                except Exception as e:
                    results.append({
                        'transfer_id': match_data.get('transfer_id', ''),
                        'success': False,
                        'error': str(e),
                    })

        return results

    @classmethod
    def import_csv(
        cls,
        tenant_id: str,
        file_content: bytes,
        filename: str,
        file_format: str = 'zengin',
        encoding: str = 'shift_jis',
        user=None
    ) -> Dict[str, Any]:
        """振込CSVをインポート

        Args:
            tenant_id: テナントID
            file_content: ファイル内容
            filename: ファイル名
            file_format: ファイル形式
            encoding: エンコーディング
            user: 操作ユーザー

        Returns:
            {'success': bool, 'import_id': str, 'total': int, 'errors': list}
        """
        try:
            content = file_content.decode(encoding)
            reader = csv.DictReader(io.StringIO(content))

            import_batch = BankTransferImport.objects.create(
                tenant_id=tenant_id,
                filename=filename,
                file_format=file_format,
                encoding=encoding,
                uploaded_by=user,
            )

            total = 0
            errors = []

            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        transfer_date_str = row.get('振込日', row.get('取引日', ''))
                        if transfer_date_str:
                            for fmt in ['%Y/%m/%d', '%Y-%m-%d', '%Y%m%d']:
                                try:
                                    transfer_date = datetime.strptime(transfer_date_str, fmt).date()
                                    break
                                except ValueError:
                                    continue
                            else:
                                transfer_date = timezone.now().date()
                        else:
                            transfer_date = timezone.now().date()

                        amount_str = row.get('金額', row.get('入金額', '0'))
                        amount = Decimal(amount_str.replace(',', '').replace('円', '').strip())

                        payer_name = row.get('振込人名', row.get('依頼人名', '')).strip()
                        source_bank = row.get('銀行名', row.get('振込銀行', '')).strip()
                        source_branch = row.get('支店名', row.get('振込支店', '')).strip()

                        BankTransfer.objects.create(
                            tenant_id=tenant_id,
                            import_batch=import_batch,
                            transfer_date=transfer_date,
                            amount=amount,
                            payer_name=payer_name,
                            source_bank_name=source_bank,
                            source_branch_name=source_branch,
                            status=BankTransfer.Status.PENDING,
                        )
                        total += 1

                    except Exception as e:
                        errors.append(f"行{row_num}: {str(e)}")

            import_batch.total_count = total
            import_batch.pending_count = total
            import_batch.save()

            return {
                'success': len(errors) == 0,
                'import_id': str(import_batch.id),
                'total': total,
                'errors': errors
            }

        except Exception as e:
            return {
                'success': False,
                'import_id': None,
                'total': 0,
                'errors': [str(e)]
            }

    @classmethod
    def auto_match(
        cls,
        tenant_id: str,
        import_batch_id: str
    ) -> Dict[str, Any]:
        """振込を自動照合

        Args:
            tenant_id: テナントID
            import_batch_id: インポートバッチID

        Returns:
            {'matched': int, 'unmatched': int}
        """
        transfers = BankTransfer.objects.filter(
            tenant_id=tenant_id,
            import_batch_id=import_batch_id,
            status=BankTransfer.Status.PENDING
        )

        matched = 0
        unmatched = 0

        for transfer in transfers:
            # 保護者番号のヒントから照合
            if transfer.guardian_no_hint:
                guardian = Guardian.objects.filter(
                    tenant_id=tenant_id,
                    guardian_no=transfer.guardian_no_hint
                ).first()
                if guardian:
                    transfer.guardian = guardian
                    transfer.status = BankTransfer.Status.MATCHED
                    transfer.save()
                    matched += 1
                    continue

            # 振込人名からカナ照合
            if transfer.payer_name:
                payer_kana = transfer.payer_name.strip()
                guardian = Guardian.objects.filter(
                    tenant_id=tenant_id,
                    full_name_kana__icontains=payer_kana
                ).first()
                if guardian:
                    transfer.guardian = guardian
                    transfer.status = BankTransfer.Status.MATCHED
                    transfer.save()
                    matched += 1
                    continue

            transfer.status = BankTransfer.Status.UNMATCHED
            transfer.save()
            unmatched += 1

        # バッチのカウント更新
        try:
            import_batch = BankTransferImport.objects.get(id=import_batch_id)
            import_batch.update_counts()
        except BankTransferImport.DoesNotExist:
            pass

        return {
            'matched': matched,
            'unmatched': unmatched
        }

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

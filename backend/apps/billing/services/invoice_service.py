"""
InvoiceService - 請求書サービス

請求書の生成、確定、エクスポート関連のビジネスロジック
"""
import csv
import io
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any, Tuple

from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse

from apps.billing.models import (
    Invoice, InvoiceLine, Payment, GuardianBalance,
    BillingPeriod, PaymentProvider, MonthlyBillingDeadline,
    ConfirmedBilling, DirectDebitResult
)
from apps.students.models import Guardian

logger = logging.getLogger(__name__)


class InvoiceService:
    """請求書サービス"""

    @staticmethod
    def check_deadline_editable(tenant_id: str, billing_year: int, billing_month: int) -> bool:
        """請求月が編集可能かチェック"""
        return MonthlyBillingDeadline.is_month_editable(tenant_id, billing_year, billing_month)

    @staticmethod
    def generate_invoice_no(tenant_id: str) -> str:
        """請求書番号を生成"""
        today = timezone.now()
        prefix = f"INV-{today.strftime('%Y%m%d')}-"
        last = Invoice.objects.filter(
            tenant_id=tenant_id,
            invoice_no__startswith=prefix
        ).order_by('-invoice_no').first()

        if last:
            try:
                new_num = int(last.invoice_no.split('-')[-1]) + 1
            except ValueError:
                new_num = 1
        else:
            new_num = 1

        return f"{prefix}{new_num:04d}"

    @staticmethod
    def confirm_invoice(invoice: Invoice, user) -> Invoice:
        """請求書を確定"""
        if invoice.status != Invoice.Status.DRAFT:
            raise ValueError('この請求書は既に確定されています')

        invoice.confirm(user)
        return invoice

    @classmethod
    def export_debit_csv(
        cls,
        tenant_id: str,
        start_date: date,
        end_date: date,
        provider: str = 'jaccs',
        user=None
    ) -> Tuple[HttpResponse, List[str]]:
        """引落データをCSV形式でエクスポート

        Args:
            tenant_id: テナントID
            start_date: 開始日
            end_date: 終了日
            provider: 決済代行会社コード
            user: 操作ユーザー

        Returns:
            (HttpResponse, exported_invoice_ids)
        """
        batch_no = f"EXP-{timezone.now().strftime('%Y%m%d%H%M%S')}-{provider.upper()}"

        invoices = Invoice.objects.filter(
            tenant_id=tenant_id,
            issue_date__gte=start_date,
            issue_date__lte=end_date,
            payment_method=Invoice.PaymentMethod.DIRECT_DEBIT,
            status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL],
        ).select_related('guardian')

        response = HttpResponse(content_type='text/csv; charset=shift_jis')
        filename = f"debit_export_{start_date}_{end_date}_{provider}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow([
            '顧客番号', '氏名カナ', '銀行コード', '支店コード',
            '口座種別', '口座番号', '引落金額', '備考'
        ])

        exported_invoice_ids = []

        for inv in invoices:
            guardian = inv.guardian
            if not guardian:
                continue

            amount = int(inv.balance_due)
            if amount <= 0:
                continue

            writer.writerow([
                guardian.guardian_no or '',
                guardian.full_name_kana or f"{guardian.last_name_kana or ''}{guardian.first_name_kana or ''}",
                guardian.bank_code or '',
                guardian.branch_code or '',
                '1' if guardian.account_type == 'ordinary' else '2',
                guardian.account_number or '',
                amount,
                inv.invoice_no,
            ])
            exported_invoice_ids.append(str(inv.id))

        # エクスポートした請求書をロック
        now = timezone.now()
        Invoice.objects.filter(
            tenant_id=tenant_id,
            issue_date__lte=end_date,
            is_locked=False,
        ).update(
            is_locked=True,
            locked_at=now,
            locked_by=user,
            export_batch_no=batch_no,
        )

        return response, exported_invoice_ids

    @classmethod
    def import_debit_result(
        cls,
        tenant_id: str,
        file_content: bytes,
        user=None
    ) -> Dict[str, Any]:
        """引落結果CSVを取り込み

        Args:
            tenant_id: テナントID
            file_content: CSVファイル内容
            user: 操作ユーザー

        Returns:
            {'success': bool, 'imported': int, 'errors': list}
        """
        try:
            content = file_content.decode('shift_jis')
            reader = csv.DictReader(io.StringIO(content))

            imported = 0
            errors = []

            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        customer_code = row.get('顧客番号', '').strip()
                        result_code = row.get('結果コード', '').strip()
                        amount = row.get('引落金額', '0').strip()
                        invoice_no = row.get('備考', '').strip()

                        guardian = Guardian.objects.filter(
                            tenant_id=tenant_id,
                            guardian_no=customer_code
                        ).first()

                        if not guardian:
                            errors.append(f"行{row_num}: 顧客番号 {customer_code} が見つかりません")
                            continue

                        invoice = Invoice.objects.filter(
                            tenant_id=tenant_id,
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

                        debit_result = DirectDebitResult.objects.create(
                            tenant_id=tenant_id,
                            guardian=guardian,
                            invoice=invoice,
                            debit_date=timezone.now().date(),
                            amount=Decimal(amount) if amount else 0,
                            result_status=result_status,
                            failure_reason=failure_reason,
                        )

                        # 成功時は入金処理
                        if result_status == DirectDebitResult.ResultStatus.SUCCESS:
                            from apps.billing.services.payment_service import PaymentService
                            PaymentService.create_payment_from_debit_result(
                                tenant_id=tenant_id,
                                guardian=guardian,
                                invoice=invoice,
                                amount=Decimal(amount) if amount else Decimal('0'),
                                debit_result=debit_result,
                                user=user
                            )

                        imported += 1

                    except Exception as e:
                        errors.append(f"行{row_num}: {str(e)}")

            return {
                'success': len(errors) == 0,
                'imported': imported,
                'errors': errors
            }

        except Exception as e:
            return {
                'success': False,
                'imported': 0,
                'errors': [str(e)]
            }

    @classmethod
    def export_billing_csv(
        cls,
        tenant_id: str,
        start_date: date,
        end_date: date,
        billing_year: Optional[int] = None,
        billing_month: Optional[int] = None,
        close_period: bool = False,
        user=None
    ) -> HttpResponse:
        """請求データをCSV形式でエクスポート

        Args:
            tenant_id: テナントID
            start_date: 開始日
            end_date: 終了日
            billing_year: 請求年（オプション）
            billing_month: 請求月（オプション）
            close_period: 締め確定も同時に実行するか
            user: 操作ユーザー

        Returns:
            HttpResponse (CSV)
        """
        from django.db.models import Q

        invoices = Invoice.objects.filter(
            tenant_id=tenant_id,
        ).select_related('guardian').prefetch_related('lines', 'lines__student')

        if billing_year and billing_month:
            invoices = invoices.filter(
                billing_year=int(billing_year),
                billing_month=int(billing_month)
            )
        else:
            start_year, start_month = start_date.year, start_date.month
            end_year, end_month = end_date.year, end_date.month

            year_month_conditions = Q()
            current_year, current_month = start_year, start_month
            while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
                year_month_conditions |= Q(billing_year=current_year, billing_month=current_month)
                if current_month == 12:
                    current_year += 1
                    current_month = 1
                else:
                    current_month += 1

            invoices = invoices.filter(year_month_conditions)

        invoices = invoices.order_by('billing_year', 'billing_month', 'invoice_no')

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        filename = f"請求データ_{start_date}_{end_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow([
            '請求番号', '請求年', '請求月', '保護者番号', '保護者名', '保護者名カナ',
            'ステータス', '支払方法', '発行日', '請求額', '入金額', '未払額',
            '生徒名', '商品名', '商品タイプ', '数量', '単価', '税込金額', '税率'
        ])

        for inv in invoices:
            guardian = inv.guardian
            guardian_no = guardian.guardian_no if guardian else ''
            guardian_name = guardian.full_name if guardian else ''
            guardian_name_kana = guardian.full_name_kana if guardian else ''

            status_display = dict(Invoice.Status.choices).get(inv.status, inv.status)
            method_display = dict(Invoice.PaymentMethod.choices).get(inv.payment_method, inv.payment_method)

            lines = inv.lines.all()
            if lines:
                for line in lines:
                    writer.writerow([
                        inv.invoice_no or '',
                        inv.billing_year,
                        inv.billing_month,
                        guardian_no,
                        guardian_name,
                        guardian_name_kana,
                        status_display,
                        method_display,
                        inv.issue_date.strftime('%Y-%m-%d') if inv.issue_date else '',
                        int(inv.total_amount or 0),
                        int(inv.paid_amount or 0),
                        int(inv.balance_due or 0),
                        line.student.full_name if line.student else '',
                        line.product_name or '',
                        line.product_type or '',
                        line.quantity or 1,
                        int(line.unit_price or 0),
                        int(line.price_with_tax or 0),
                        f"{int((line.tax_rate or 0) * 100)}%",
                    ])
            else:
                writer.writerow([
                    inv.invoice_no or '',
                    inv.billing_year,
                    inv.billing_month,
                    guardian_no,
                    guardian_name,
                    guardian_name_kana,
                    status_display,
                    method_display,
                    inv.issue_date.strftime('%Y-%m-%d') if inv.issue_date else '',
                    int(inv.total_amount or 0),
                    int(inv.paid_amount or 0),
                    int(inv.balance_due or 0),
                    '', '', '', '', '', '', ''
                ])

        # 締め確定処理
        if close_period and billing_year and billing_month:
            cls._close_billing_period(
                tenant_id=tenant_id,
                billing_year=int(billing_year),
                billing_month=int(billing_month),
                start_date=start_date,
                end_date=end_date,
                user=user
            )

        return response

    @classmethod
    def _close_billing_period(
        cls,
        tenant_id: str,
        billing_year: int,
        billing_month: int,
        start_date: date,
        end_date: date,
        user=None
    ) -> None:
        """請求期間を締める"""
        try:
            deadline, created = MonthlyBillingDeadline.objects.get_or_create(
                tenant_id=tenant_id,
                year=billing_year,
                month=billing_month,
                defaults={
                    'closing_day': PaymentProvider.objects.filter(
                        tenant_id=tenant_id, is_active=True
                    ).first().closing_day if PaymentProvider.objects.filter(
                        tenant_id=tenant_id, is_active=True
                    ).exists() else 25
                }
            )
            if not deadline.is_closed:
                deadline.is_closed = True
                deadline.is_manually_closed = True
                deadline.closed_at = timezone.now()
                deadline.closed_by = user
                deadline.notes = f'CSVエクスポート時に自動締め（{start_date}〜{end_date}）'
                deadline.save()

            Invoice.objects.filter(
                tenant_id=tenant_id,
                billing_year=billing_year,
                billing_month=billing_month,
                is_locked=False,
            ).update(
                is_locked=True,
                locked_at=timezone.now(),
                locked_by=user,
            )
        except Exception as e:
            logger.error(f'Failed to close period: {e}')

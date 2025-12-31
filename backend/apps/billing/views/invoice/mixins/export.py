"""
Invoice Export Mixin - CSVエクスポート機能
"""
import csv
import logging
from datetime import datetime

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.billing.models import Invoice, MonthlyBillingDeadline, PaymentProvider

logger = logging.getLogger(__name__)


class InvoiceExportMixin:
    """請求書CSVエクスポート機能"""

    @extend_schema(summary='引落データCSVエクスポート')
    @action(detail=False, methods=['get'], url_path='export-debit')
    def export_debit(self, request):
        """引落データをCSV形式でエクスポート（JACCS/UFJファクター/中京ファイナンス向け）

        日付範囲で指定可能。エクスポート後、該当請求書と以前の請求書は編集ロックされる。
        """
        from calendar import monthrange

        # 日付範囲パラメータ（新形式）
        start_date = request.query_params.get('start_date')  # YYYY-MM-DD
        end_date = request.query_params.get('end_date')      # YYYY-MM-DD
        provider = request.query_params.get('provider', 'jaccs')

        # 旧形式（year/month）との互換性
        billing_year = request.query_params.get('billing_year')
        billing_month = request.query_params.get('billing_month')

        if not start_date or not end_date:
            if billing_year and billing_month:
                # 旧形式の場合は月初〜月末に変換
                year = int(billing_year)
                month = int(billing_month)
                last_day = monthrange(year, month)[1]
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year}-{month:02d}-{last_day:02d}"
            else:
                return Response(
                    {'error': '期間を指定してください（start_date, end_date または billing_year, billing_month）'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': '日付形式が不正です（YYYY-MM-DD）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # バッチ番号を生成
        batch_no = f"EXP-{timezone.now().strftime('%Y%m%d%H%M%S')}-{provider.upper()}"

        # 対象請求書を取得（口座引落、発行済または一部入金、期間内）
        invoices = Invoice.objects.filter(
            tenant_id=request.user.tenant_id,
            issue_date__gte=start_dt,
            issue_date__lte=end_dt,
            payment_method=Invoice.PaymentMethod.DIRECT_DEBIT,
            status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL],
        ).select_related('guardian')

        # CSVレスポンス作成
        response = HttpResponse(content_type='text/csv; charset=shift_jis')
        filename = f"debit_export_{start_date}_{end_date}_{provider}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # ヘッダー行（全銀形式ベース）
        writer.writerow([
            '顧客番号', '氏名カナ', '銀行コード', '支店コード',
            '口座種別', '口座番号', '引落金額', '備考'
        ])

        exported_invoice_ids = []

        # データ行
        for inv in invoices:
            guardian = inv.guardian
            if not guardian:
                continue

            # 引落金額（未払額）
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
            exported_invoice_ids.append(inv.id)

        # エクスポートした請求書と、それ以前の請求書をロック
        now = timezone.now()
        Invoice.objects.filter(
            tenant_id=request.user.tenant_id,
            issue_date__lte=end_dt,
            is_locked=False,
        ).update(
            is_locked=True,
            locked_at=now,
            locked_by=request.user,
            export_batch_no=batch_no,
        )

        return response

    @extend_schema(summary='請求データCSVエクスポート（締日期間）')
    @action(detail=False, methods=['get'], url_path='export_csv')
    def export_csv(self, request):
        """請求データをCSV形式でエクスポート（締日期間指定）

        start_date, end_date で期間を指定
        billing_year, billing_month で請求月を指定
        close_period=true で締め確定も同時に実行
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        billing_year = request.query_params.get('billing_year')
        billing_month = request.query_params.get('billing_month')
        close_period = request.query_params.get('close_period', 'false').lower() == 'true'

        if not start_date or not end_date:
            return Response(
                {'error': '期間を指定してください（start_date, end_date）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': '日付形式が不正です（YYYY-MM-DD）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tenant_id = request.user.tenant_id

        # 対象請求書を取得
        invoices = Invoice.objects.filter(
            tenant_id=tenant_id,
        ).select_related('guardian').prefetch_related('lines')

        # billing_year, billing_month が指定されている場合はそれでフィルタ
        if billing_year and billing_month:
            invoices = invoices.filter(
                billing_year=int(billing_year),
                billing_month=int(billing_month)
            )
        else:
            # 期間ベースでフィルタ
            start_year, start_month = start_dt.year, start_dt.month
            end_year, end_month = end_dt.year, end_dt.month

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

        # CSVレスポンス作成
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        filename = f"請求データ_{start_date}_{end_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # ヘッダー行
        writer.writerow([
            '請求番号', '請求年', '請求月', '保護者番号', '保護者名', '保護者名カナ',
            'ステータス', '支払方法', '発行日', '請求額', '入金額', '未払額',
            '生徒名', '商品名', '商品タイプ', '数量', '単価', '税込金額', '税率'
        ])

        # データ行（請求明細ごとに1行）
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
                # 明細がない場合は請求書のみ出力
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
            self._close_period_on_export(
                tenant_id, billing_year, billing_month, start_date, end_date, request.user
            )

        return response

    def _close_period_on_export(self, tenant_id, billing_year, billing_month, start_date, end_date, user):
        """エクスポート時の締め確定処理"""
        try:
            # MonthlyBillingDeadlineを締め状態に更新
            deadline, created = MonthlyBillingDeadline.objects.get_or_create(
                tenant_id=tenant_id,
                year=int(billing_year),
                month=int(billing_month),
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

            # 対象請求書をロック
            Invoice.objects.filter(
                tenant_id=tenant_id,
                billing_year=int(billing_year),
                billing_month=int(billing_month),
                is_locked=False,
            ).update(
                is_locked=True,
                locked_at=timezone.now(),
                locked_by=user,
            )
        except Exception as e:
            # 締め処理に失敗してもCSVは返す（ログのみ）
            logger.error(f'Failed to close period: {e}')

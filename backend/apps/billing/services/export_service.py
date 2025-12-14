"""
Direct Debit Export Service
引落データエクスポートサービス

UFJファクター、JACCS、中京ファイナンスなど各決済代行会社向けの
引落データをCSV形式でエクスポートする。
"""
import csv
import io
from datetime import date
from decimal import Decimal
from typing import List, Tuple, Optional

from django.db import transaction
from django.utils import timezone

from apps.billing.models import (
    Invoice, Payment, PaymentProvider, BillingPeriod,
    DebitExportBatch, DebitExportLine
)
from apps.students.models import Guardian


class DirectDebitExportService:
    """引落データエクスポートサービス"""

    # 口座種別マッピング (Guardianモデル -> 全銀フォーマット)
    ACCOUNT_TYPE_MAP = {
        'ordinary': '1',    # 普通預金
        'current': '2',     # 当座預金
        'savings': '1',     # 貯蓄預金 (普通として扱う)
    }

    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id

    def generate_batch(
        self,
        provider: PaymentProvider,
        year: int,
        month: int,
        user=None
    ) -> DebitExportBatch:
        """エクスポートバッチを生成

        Args:
            provider: 決済代行会社
            year: 対象年
            month: 対象月
            user: 実行ユーザー

        Returns:
            生成されたDebitExportBatch
        """
        # 請求期間を取得または作成
        billing_period, created = BillingPeriod.objects.get_or_create(
            tenant_id=self.tenant_id,
            provider=provider,
            year=year,
            month=month,
            defaults={
                'closing_date': date(year, month, provider.closing_day),
            }
        )

        # バッチを作成
        batch_no = DebitExportBatch.generate_batch_no(self.tenant_id, provider.code)
        batch = DebitExportBatch.objects.create(
            tenant_id=self.tenant_id,
            batch_no=batch_no,
            provider=provider,
            billing_period=billing_period,
            status=DebitExportBatch.Status.DRAFT,
        )

        # 明細を生成
        self._generate_lines(batch, year, month)

        return batch

    def _generate_lines(self, batch: DebitExportBatch, year: int, month: int):
        """バッチに紐づく明細を生成

        該当月の請求書と保護者の口座情報を取得し、DebitExportLineを作成する。
        """
        # 該当月の請求書を取得
        invoices = Invoice.objects.filter(
            tenant_id=self.tenant_id,
            billing_year=year,
            billing_month=month,
            status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL],
            balance_due__gt=0,  # 未払い額がある請求書のみ
        ).select_related('guardian')

        line_no = 1
        total_count = 0
        total_amount = Decimal('0')

        for invoice in invoices:
            guardian = invoice.guardian

            # 口座情報のバリデーション
            errors = self.validate_bank_info(guardian)
            if errors:
                # 口座情報が不完全な場合はスキップ（ログに記録することも可能）
                continue

            # 口座種別を変換
            account_type = self.ACCOUNT_TYPE_MAP.get(guardian.account_type, '1')

            # 明細を作成
            DebitExportLine.objects.create(
                tenant_id=self.tenant_id,
                batch=batch,
                line_no=line_no,
                guardian=guardian,
                invoice=invoice,
                bank_code=guardian.bank_code.zfill(4),
                branch_code=guardian.branch_code.zfill(3),
                account_type=account_type,
                account_number=guardian.account_number.zfill(7),
                account_holder_kana=guardian.account_holder_kana or '',
                amount=invoice.balance_due,
                customer_code=str(guardian.guardian_no or guardian.id)[:20],
                result_status=DebitExportLine.ResultStatus.PENDING,
            )

            total_count += 1
            total_amount += invoice.balance_due
            line_no += 1

        # バッチの集計情報を更新
        batch.total_count = total_count
        batch.total_amount = total_amount
        batch.save()

    def validate_bank_info(self, guardian: Guardian) -> List[str]:
        """口座情報のバリデーション

        Args:
            guardian: 保護者

        Returns:
            エラーメッセージのリスト（空リストなら有効）
        """
        errors = []

        if not guardian.bank_code:
            errors.append('銀行コードが未設定です')
        elif len(guardian.bank_code) > 4:
            errors.append('銀行コードが4桁を超えています')

        if not guardian.branch_code:
            errors.append('支店コードが未設定です')
        elif len(guardian.branch_code) > 3:
            errors.append('支店コードが3桁を超えています')

        if not guardian.account_number:
            errors.append('口座番号が未設定です')
        elif len(guardian.account_number) > 8:
            errors.append('口座番号が8桁を超えています')

        if not guardian.account_holder_kana:
            errors.append('口座名義（カナ）が未設定です')

        return errors

    def export_to_csv(self, batch: DebitExportBatch, user=None) -> str:
        """CSV形式でエクスポート

        Args:
            batch: エクスポートバッチ
            user: 実行ユーザー

        Returns:
            CSV文字列（Shift-JIS エンコード）
        """
        provider = batch.provider
        lines = batch.lines.all().order_by('line_no')

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # 対象年月（YYYYMM形式）
        period = batch.billing_period
        target_period = f"{period.year}{period.month:02d}"

        for line in lines:
            row = [
                provider.consignor_code,          # 委託者コード
                target_period,                    # 対象年月
                line.bank_code,                   # 銀行コード
                line.branch_code,                 # 支店コード
                line.account_type,                # 預金種目
                line.account_number,              # 口座番号
                line.account_holder_kana,         # 名義カナ
                int(line.amount),                 # 金額
                '1',                              # 区分（通常は1）
                line.customer_code,               # 顧客番号
            ]
            writer.writerow(row)

        # バッチのステータスを更新
        batch.status = DebitExportBatch.Status.EXPORTED
        batch.export_date = timezone.now()
        batch.exported_by = user
        batch.save()

        return output.getvalue()

    def export_to_csv_bytes(self, batch: DebitExportBatch, user=None) -> bytes:
        """CSV形式でエクスポート（バイト列）

        Args:
            batch: エクスポートバッチ
            user: 実行ユーザー

        Returns:
            CSV バイト列（指定されたエンコーディング）
        """
        csv_str = self.export_to_csv(batch, user)
        encoding = batch.provider.file_encoding or 'shift_jis'
        return csv_str.encode(encoding, errors='replace')

    def get_export_filename(self, batch: DebitExportBatch) -> str:
        """エクスポートファイル名を生成

        Args:
            batch: エクスポートバッチ

        Returns:
            ファイル名
        """
        provider = batch.provider
        period = batch.billing_period
        timestamp = timezone.now().strftime('%Y%m%d%H%M')

        return f"{provider.code}_output_{period.year}{period.month:02d}_{timestamp}.csv"

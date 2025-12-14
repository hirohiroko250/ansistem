"""
Direct Debit Import Service
引落結果インポートサービス

決済代行会社からの引落結果CSVをインポートし、
DebitExportLine, DirectDebitResult, Payment などを更新する。
"""
import csv
import io
from datetime import date
from decimal import Decimal
from typing import Dict, List, Tuple, Optional, BinaryIO

from django.db import transaction
from django.utils import timezone

from apps.billing.models import (
    Invoice, Payment, PaymentProvider, BillingPeriod,
    DebitExportBatch, DebitExportLine, DirectDebitResult
)


class DirectDebitImportService:
    """引落結果インポートサービス"""

    # 結果コードマッピング
    # 0: 成功, 1: 残高不足, 4: その他エラー（各社で異なる場合あり）
    RESULT_CODE_MAP = {
        '0': ('success', '引落成功', None),
        '1': ('failed', '残高不足', DirectDebitResult.FailureReason.INSUFFICIENT_FUNDS),
        '2': ('failed', '口座解約', DirectDebitResult.FailureReason.ACCOUNT_CLOSED),
        '3': ('failed', '口座相違', DirectDebitResult.FailureReason.INVALID_ACCOUNT),
        '4': ('failed', 'その他エラー', DirectDebitResult.FailureReason.OTHER),
        '9': ('failed', '振替拒否', DirectDebitResult.FailureReason.REJECTED),
    }

    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id

    def import_result_csv(
        self,
        batch: DebitExportBatch,
        file_content: bytes,
        user=None
    ) -> Dict:
        """結果CSVをインポート

        Args:
            batch: エクスポートバッチ
            file_content: CSVファイルの内容（バイト列）
            user: 実行ユーザー

        Returns:
            インポート結果の辞書
        """
        encoding = batch.provider.file_encoding or 'shift_jis'

        try:
            content = file_content.decode(encoding)
        except UnicodeDecodeError:
            content = file_content.decode('utf-8', errors='replace')

        reader = csv.reader(io.StringIO(content))

        results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'not_found': 0,
            'errors': [],
        }

        with transaction.atomic():
            for row_no, row in enumerate(reader, 1):
                if len(row) < 11:
                    results['errors'].append(f'行{row_no}: 列数不足')
                    continue

                try:
                    result = self._process_result_row(batch, row, row_no)
                    results['total'] += 1

                    if result == 'success':
                        results['success'] += 1
                    elif result == 'failed':
                        results['failed'] += 1
                    elif result == 'not_found':
                        results['not_found'] += 1
                except Exception as e:
                    results['errors'].append(f'行{row_no}: {str(e)}')

            # バッチのステータス更新
            self._update_batch_status(batch, results, user)

        return results

    def _process_result_row(
        self,
        batch: DebitExportBatch,
        row: List[str],
        row_no: int
    ) -> str:
        """結果行を処理

        Args:
            batch: エクスポートバッチ
            row: CSV行データ
            row_no: 行番号

        Returns:
            処理結果（'success', 'failed', 'not_found'）
        """
        # CSV列の解析
        # [委託者コード, 対象年月, 銀行コード, 支店コード, 預金種目, 口座番号, 名義カナ, 金額, 区分, 顧客番号, 結果コード]
        consignor_code = row[0].strip().strip('"')
        target_period = row[1].strip().strip('"')
        bank_code = row[2].strip().strip('"')
        branch_code = row[3].strip().strip('"')
        account_type = row[4].strip().strip('"')
        account_number = row[5].strip().strip('"')
        account_holder_kana = row[6].strip().strip('"')
        amount = Decimal(row[7].strip().strip('"'))
        category = row[8].strip().strip('"')
        customer_code = row[9].strip().strip('"')
        result_code = row[10].strip().strip('"') if len(row) > 10 else '0'

        # 対応する明細を検索
        line = batch.lines.filter(
            customer_code=customer_code,
            amount=amount,
        ).first()

        if not line:
            # 顧客番号と金額で見つからない場合、口座情報でも検索
            line = batch.lines.filter(
                bank_code=bank_code.zfill(4),
                branch_code=branch_code.zfill(3),
                account_number=account_number.zfill(7),
                amount=amount,
            ).first()

        if not line:
            return 'not_found'

        # 結果コードの解析
        status, message, failure_reason = self.parse_result_code(result_code)

        # 明細の更新
        line.result_code = result_code
        line.result_status = (
            DebitExportLine.ResultStatus.SUCCESS if status == 'success'
            else DebitExportLine.ResultStatus.FAILED
        )
        line.result_message = message

        if status == 'success':
            # 成功の場合、Paymentを作成
            self._create_payment(line, batch)
        else:
            # 失敗の場合、DirectDebitResultを作成
            self._create_direct_debit_result(line, batch, failure_reason, message)

        line.save()

        return status

    def parse_result_code(self, code: str) -> Tuple[str, str, Optional[str]]:
        """結果コードを解析

        Args:
            code: 結果コード

        Returns:
            (status, message, failure_reason) のタプル
        """
        return self.RESULT_CODE_MAP.get(
            code,
            ('failed', f'不明なエラーコード: {code}', DirectDebitResult.FailureReason.OTHER)
        )

    def _create_payment(self, line: DebitExportLine, batch: DebitExportBatch):
        """成功した引落のPaymentレコードを作成"""
        period = batch.billing_period

        payment = Payment.objects.create(
            tenant_id=self.tenant_id,
            payment_no=Payment.generate_payment_no(self.tenant_id),
            guardian=line.guardian,
            invoice=line.invoice,
            payment_date=date(period.year, period.month, batch.provider.debit_day),
            amount=line.amount,
            method=Payment.Method.DIRECT_DEBIT,
            status=Payment.Status.SUCCESS,
            debit_result_code=line.result_code,
            debit_result_message=line.result_message,
        )

        # 請求書に入金を適用
        payment.apply_to_invoice()

        # 明細にPaymentを紐付け
        line.payment = payment

    def _create_direct_debit_result(
        self,
        line: DebitExportLine,
        batch: DebitExportBatch,
        failure_reason: Optional[str],
        message: str
    ):
        """失敗した引落のDirectDebitResultレコードを作成"""
        period = batch.billing_period

        result = DirectDebitResult.objects.create(
            tenant_id=self.tenant_id,
            guardian=line.guardian,
            invoice=line.invoice,
            debit_date=date(period.year, period.month, batch.provider.debit_day),
            amount=line.amount,
            result_status=DirectDebitResult.ResultStatus.FAILED,
            failure_reason=failure_reason or DirectDebitResult.FailureReason.OTHER,
            failure_detail=message,
        )

        # 明細にDirectDebitResultを紐付け
        line.direct_debit_result = result

    def _update_batch_status(self, batch: DebitExportBatch, results: Dict, user):
        """バッチのステータスを更新"""
        # 成功・失敗の集計
        success_lines = batch.lines.filter(
            result_status=DebitExportLine.ResultStatus.SUCCESS
        )
        failed_lines = batch.lines.filter(
            result_status=DebitExportLine.ResultStatus.FAILED
        )

        batch.success_count = success_lines.count()
        batch.success_amount = sum(line.amount for line in success_lines)
        batch.failed_count = failed_lines.count()
        batch.failed_amount = sum(line.amount for line in failed_lines)

        batch.status = DebitExportBatch.Status.RESULT_IMPORTED
        batch.result_imported_at = timezone.now()
        batch.result_imported_by = user
        batch.save()

    def import_from_file(
        self,
        batch: DebitExportBatch,
        file: BinaryIO,
        user=None
    ) -> Dict:
        """ファイルオブジェクトから結果をインポート

        Args:
            batch: エクスポートバッチ
            file: ファイルオブジェクト
            user: 実行ユーザー

        Returns:
            インポート結果の辞書
        """
        file_content = file.read()
        return self.import_result_csv(batch, file_content, user)

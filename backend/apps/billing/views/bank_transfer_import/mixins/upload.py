"""
BankTransferImport Upload Mixin - アップロード機能
"""
import csv
import io
import re
import logging
from datetime import datetime
from decimal import Decimal

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from drf_spectacular.utils import extend_schema

from apps.billing.models import Invoice, BankTransfer, BankTransferImport
from apps.core.exceptions import ValidationException

logger = logging.getLogger(__name__)


class BankTransferImportUploadMixin:
    """振込インポートアップロード機能"""

    def _detect_and_parse_bank_raw_csv(self, file_content):
        """銀行の生CSVフォーマットを検出してパース

        銀行の生データ形式:
        - 行タイプ1: ヘッダー情報
        - 行タイプ2: 振込データ (日付, 空, 振込種別, 振込人名義, 金額, ...)
        """
        try:
            content = file_content.decode('shift_jis')
        except (UnicodeDecodeError, LookupError):
            try:
                content = file_content.decode('utf-8-sig')
            except (UnicodeDecodeError, LookupError):
                content = file_content.decode('utf-8')

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        if not rows:
            return None, "ファイルにデータがありません"

        is_bank_raw = any(row and row[0] == '2' for row in rows)

        if not is_bank_raw:
            return None, None

        first_data_row = None
        for row in rows:
            if row and row[0] == '2':
                first_data_row = row
                break

        if not first_data_row:
            return [], None

        is_pattern1 = len(first_data_row) > 2 and first_data_row[2] == ''

        transfers = []
        for row in rows:
            if not row or row[0] != '2':
                continue

            date_str = row[1] if len(row) > 1 else ""
            if date_str:
                date_str = date_str.replace(".", "-")

            if is_pattern1:
                payer_raw = row[4] if len(row) > 4 else ""
                amount_str = row[5] if len(row) > 5 else "0"
            else:
                payer_raw = row[3] if len(row) > 3 else ""
                amount_str = row[5] if len(row) > 5 else "0"

            guardian_id, payer_name = self._parse_payer_name(payer_raw)

            try:
                amount = int(amount_str.replace(',', ''))
            except (ValueError, AttributeError):
                amount = 0

            if date_str and amount > 0:
                transfers.append({
                    'transfer_date': date_str,
                    'amount': amount,
                    'payer_name': payer_name,
                    'payer_name_kana': payer_name,
                    'guardian_id_hint': guardian_id,
                    'source_bank_name': '',
                    'source_branch_name': '',
                })

        return transfers, None

    def _parse_payer_name(self, name_str):
        """振込人名義を解析（ID部分を分離）

        例: ８２１８８５９コジマ → ID: 8218859, 名義: コジマ
        例: カワカミ　ユミコ → ID: なし, 名義: カワカミ ユミコ
        """
        if not name_str:
            return "", ""

        name_str = name_str.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

        match = re.match(r'^(\d+)\s*(.*)$', name_str)
        if match:
            guardian_id = match.group(1)
            name = match.group(2).strip()
            name = name.replace('　', ' ')
            return guardian_id, name
        else:
            name = name_str.replace('　', ' ')
            return "", name

    def _auto_match_transfers(self, transfers, user):
        """振込データを自動照合"""
        from apps.students.models import Guardian
        matched_count = 0

        for transfer in transfers:
            payer_name = transfer.payer_name.replace('　', ' ').strip()
            name_parts = payer_name.split()

            if len(name_parts) >= 2:
                last_name = name_parts[0]
                first_name = name_parts[-1]

                guardian = Guardian.objects.filter(
                    tenant_id=transfer.tenant_id,
                    deleted_at__isnull=True,
                    last_name=last_name,
                    first_name=first_name,
                ).first()

                if not guardian and transfer.payer_name_kana:
                    kana_parts = transfer.payer_name_kana.replace('　', ' ').split()
                    if len(kana_parts) >= 2:
                        guardian = Guardian.objects.filter(
                            tenant_id=transfer.tenant_id,
                            deleted_at__isnull=True,
                            last_name_kana=kana_parts[0],
                            first_name_kana=kana_parts[-1],
                        ).first()

                if guardian:
                    Invoice.objects.filter(
                        guardian=guardian,
                        status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE],
                        balance_due=transfer.amount,
                    ).order_by('billing_year', 'billing_month').first()

                    transfer.guardian = guardian
                    transfer.status = BankTransfer.Status.MATCHED
                    transfer.matched_by = user
                    transfer.matched_at = timezone.now()
                    transfer.save()
                    matched_count += 1

        return matched_count

    def _import_bank_raw_data(self, request, transfers_data, file_name):
        """銀行生データをインポート"""
        from apps.students.models import Guardian
        from apps.tenants.models import Tenant

        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        if not tenant_id:
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        import_batch = BankTransferImport.objects.create(
            tenant_id=tenant_id,
            file_name=file_name,
            file_type='csv',
            imported_by=request.user,
        )

        transfers_created = []
        errors = []
        auto_matched_count = 0

        for idx, data in enumerate(transfers_data):
            try:
                transfer_date = datetime.strptime(data['transfer_date'], '%Y-%m-%d').date()
                guardian_id_hint = data.get('guardian_id_hint', '')

                transfer = BankTransfer.objects.create(
                    tenant_id=tenant_id,
                    transfer_date=transfer_date,
                    amount=Decimal(str(data['amount'])),
                    payer_name=data['payer_name'],
                    payer_name_kana=data['payer_name_kana'],
                    guardian_no_hint=guardian_id_hint,
                    source_bank_name=data['source_bank_name'],
                    source_branch_name=data['source_branch_name'],
                    status=BankTransfer.Status.PENDING,
                    import_batch_id=str(import_batch.id),
                    import_row_no=idx + 1,
                )

                if guardian_id_hint:
                    guardian = Guardian.objects.filter(
                        tenant_id=tenant_id,
                        guardian_no=guardian_id_hint,
                        deleted_at__isnull=True,
                    ).first()

                    if guardian:
                        transfer.guardian = guardian
                        transfer.status = BankTransfer.Status.MATCHED
                        transfer.matched_by = request.user
                        transfer.matched_at = timezone.now()
                        transfer.save()
                        auto_matched_count += 1

                transfers_created.append(transfer)

            except Exception as e:
                errors.append({'row': idx + 1, 'error': str(e)})

        unmatched_transfers = [t for t in transfers_created if t.status == BankTransfer.Status.PENDING]
        if unmatched_transfers:
            auto_matched_count += self._auto_match_transfers(unmatched_transfers, request.user)

        import_batch.update_counts()

        return Response({
            'success': True,
            'batch_id': str(import_batch.id),
            'batch_no': import_batch.batch_no,
            'total_count': len(transfers_created),
            'error_count': len(errors),
            'auto_matched_count': auto_matched_count,
            'format_detected': 'bank_raw',
            'errors': errors[:10],
        })

    @extend_schema(summary='振込データをインポート')
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def upload(self, request):
        """CSVまたはExcelファイルから振込データをインポート

        銀行の生CSVデータ（Shift-JIS、行タイプ形式）にも対応。
        """
        import pandas as pd
        import traceback

        if 'file' not in request.FILES:
            raise ValidationException('ファイルを指定してください')

        file = request.FILES['file']
        logger.warning(f"[BankTransferImport] File size: {file.size}")
        file_name = file.name.lower()

        date_col = request.data.get('date_column', '振込日')
        amount_col = request.data.get('amount_column', '金額')
        payer_name_col = request.data.get('payer_name_column', '振込人名義')
        payer_kana_col = request.data.get('payer_name_kana_column', '振込人名義カナ')
        bank_col = request.data.get('bank_name_column', '銀行名')
        branch_col = request.data.get('branch_name_column', '支店名')

        try:
            logger.warning(f"[BankTransferImport] Processing file: {file_name}")
            if file_name.endswith('.csv'):
                file_content = file.read()
                logger.warning(f"[BankTransferImport] File content length: {len(file_content)} bytes")

                try:
                    bank_transfers, error = self._detect_and_parse_bank_raw_csv(file_content)
                    logger.warning(f"[BankTransferImport] Parse result: transfers={len(bank_transfers) if bank_transfers else None}, error={error}")
                except Exception as parse_e:
                    logger.error(f"[BankTransferImport] Parse exception: {parse_e}")
                    raise

                if error:
                    logger.warning(f"[BankTransferImport] Parse error: {error}")
                    raise ValidationException(error)

                if bank_transfers is not None:
                    logger.warning(f"[BankTransferImport] Detected bank raw format, {len(bank_transfers)} transfers")
                    original_file_name = file.name
                    return self._import_bank_raw_data(request, bank_transfers, original_file_name)

                file.seek(0)
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8-sig')
                except (UnicodeDecodeError, pd.errors.ParserError):
                    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
                file_type = 'csv'
            elif file_name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
                file_type = 'excel'
            else:
                raise ValidationException('CSVまたはExcelファイルのみ対応しています')

            if len(df) == 0:
                raise ValidationException('ファイルにデータがありません')

            tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

            import_batch = BankTransferImport.objects.create(
                tenant_id=tenant_id,
                file_name=file.name,
                file_type=file_type,
                imported_by=request.user,
            )

            transfers_created = []
            errors = []

            for idx, row in df.iterrows():
                try:
                    transfer_date = row.get(date_col)
                    if pd.isna(transfer_date):
                        errors.append({'row': idx + 2, 'error': '振込日が空です'})
                        continue

                    if isinstance(transfer_date, str):
                        transfer_date = datetime.strptime(transfer_date, '%Y-%m-%d').date()
                    elif hasattr(transfer_date, 'date'):
                        transfer_date = transfer_date.date()

                    amount = row.get(amount_col)
                    if pd.isna(amount):
                        errors.append({'row': idx + 2, 'error': '金額が空です'})
                        continue
                    amount = Decimal(str(amount).replace(',', ''))

                    payer_name = row.get(payer_name_col, '')
                    if pd.isna(payer_name) or not payer_name:
                        errors.append({'row': idx + 2, 'error': '振込人名義が空です'})
                        continue

                    transfer = BankTransfer.objects.create(
                        tenant_id=tenant_id,
                        transfer_date=transfer_date,
                        amount=amount,
                        payer_name=str(payer_name),
                        payer_name_kana=str(row.get(payer_kana_col, '')) if not pd.isna(row.get(payer_kana_col)) else '',
                        source_bank_name=str(row.get(bank_col, '')) if not pd.isna(row.get(bank_col)) else '',
                        source_branch_name=str(row.get(branch_col, '')) if not pd.isna(row.get(branch_col)) else '',
                        status=BankTransfer.Status.PENDING,
                        import_batch_id=str(import_batch.id),
                        import_row_no=idx + 1,
                    )
                    transfers_created.append(transfer)

                except Exception as e:
                    errors.append({'row': idx + 2, 'error': str(e)})

            import_batch.update_counts()
            auto_matched = self._auto_match_transfers(transfers_created, request.user)
            import_batch.update_counts()

            return Response({
                'success': True,
                'batch_id': str(import_batch.id),
                'batch_no': import_batch.batch_no,
                'total_count': len(transfers_created),
                'error_count': len(errors),
                'auto_matched_count': auto_matched,
                'errors': errors[:10],
            })

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[BankTransferImport] Error: {e}\n{tb}")
            raise ValidationException(f'ファイルの処理中にエラーが発生しました: {str(e)}')

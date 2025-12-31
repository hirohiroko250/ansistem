"""
返金一覧インポートコマンド
CSVファイルから返金データをインポートする
"""
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.utils import timezone
from apps.billing.models import RefundRequest
from apps.students.models import Guardian, Student
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = '返金一覧CSVをインポート'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='CSVファイルのパス')
        parser.add_argument('--tenant', type=str, default=None, help='テナントID')
        parser.add_argument('--dry-run', action='store_true', help='実際には保存しない')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        tenant_id = options.get('tenant')

        # テナント取得
        if tenant_id:
            tenant = Tenant.objects.get(id=tenant_id)
        else:
            tenant = Tenant.objects.first()

        if not tenant:
            self.stderr.write(self.style.ERROR('テナントが見つかりません'))
            return

        self.stdout.write(f'テナント: {tenant.tenant_name} ({tenant.id})')
        self.stdout.write(f'CSVファイル: {csv_file}')
        self.stdout.write(f'Dry run: {dry_run}')

        new_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        # キャッシュ
        self.guardian_cache = {}

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'総行数: {len(rows)}')

        for row in rows:
            try:
                with transaction.atomic():
                    result = self._import_refund(row, tenant, dry_run)
                    if result == 'new':
                        new_count += 1
                    elif result == 'updated':
                        updated_count += 1
                    elif result == 'skipped':
                        skipped_count += 1
            except Exception as e:
                errors.append(f"請求ID {row.get('請求ID', 'unknown')}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f'''
インポート完了:
- 新規: {new_count}件
- 更新: {updated_count}件
- スキップ: {skipped_count}件
- エラー: {len(errors)}件
'''))

        if errors[:10]:
            self.stderr.write('エラー詳細（最初の10件）:')
            for err in errors[:10]:
                self.stderr.write(f'  {err}')

    def _parse_date(self, date_str):
        """日付文字列をパース"""
        if not date_str or date_str.strip() == '':
            return None
        try:
            return datetime.strptime(date_str, '%Y/%m/%d').date()
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return None

    def _parse_datetime(self, dt_str):
        """日時文字列をパース"""
        if not dt_str or dt_str.strip() == '':
            return None
        try:
            return timezone.make_aware(datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S.%f'))
        except ValueError:
            try:
                return timezone.make_aware(datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S'))
            except ValueError:
                try:
                    return timezone.make_aware(datetime.strptime(dt_str, '%Y/%m/%d'))
                except ValueError:
                    return None

    def _get_guardian(self, guardian_id, tenant):
        """保護者を取得（キャッシュ使用）"""
        if not guardian_id:
            return None
        if guardian_id not in self.guardian_cache:
            guardian = Guardian.objects.filter(
                models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
            ).filter(
                models.Q(old_id=guardian_id) | models.Q(guardian_no=guardian_id)
            ).first()
            self.guardian_cache[guardian_id] = guardian
        return self.guardian_cache.get(guardian_id)

    def _import_refund(self, row, tenant, dry_run):
        """返金をインポート"""
        request_no = row.get('請求ID', '')

        if not request_no:
            return 'skipped'

        # 保護者を取得
        guardian_id = row.get('家族ID', '')
        guardian = self._get_guardian(guardian_id, tenant)

        if not guardian:
            return 'skipped'

        # 返金額
        amount_str = row.get('返金金額', '0') or '0'
        try:
            refund_amount = Decimal(amount_str.replace(',', ''))
        except (InvalidOperation, ValueError, AttributeError):
            refund_amount = Decimal('0')

        if refund_amount <= 0:
            return 'skipped'

        # ステータス
        approval_status = row.get('承認', '0')
        response_status = row.get('対応ステータス', '0')

        if approval_status == '1' and response_status == '1':
            status = RefundRequest.Status.COMPLETED
        elif approval_status == '1':
            status = RefundRequest.Status.APPROVED
        else:
            status = RefundRequest.Status.PENDING

        # 返金理由
        reason = row.get('請求書用理由', '') or row.get('本当の理由　他', '') or ''

        # 日付
        refund_date = self._parse_date(row.get('返金日付', ''))
        scheduled_date = self._parse_date(row.get('返金予定日', ''))
        created_at = self._parse_datetime(row.get('登録日時', ''))

        # 備考
        notes_parts = []
        if row.get('本当の理由　他', ''):
            notes_parts.append(f"実際の理由: {row.get('本当の理由　他', '')}")
        if row.get('名義', ''):
            notes_parts.append(f"名義: {row.get('名義', '')}")
        if row.get('銀行名', ''):
            notes_parts.append(f"銀行: {row.get('銀行名', '')} {row.get('支店名', '')}")
        if row.get('口座番号', ''):
            notes_parts.append(f"口座: {row.get('預金種別', '')} {row.get('口座番号', '')}")
        process_notes = '\n'.join(notes_parts)

        # 既存の返金を検索
        refund = RefundRequest.objects.filter(
            models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
        ).filter(request_no=request_no).first()

        created = refund is None
        if created:
            refund = RefundRequest(tenant_ref=tenant)

        # フィールド設定
        refund.request_no = request_no
        refund.guardian = guardian
        refund.refund_amount = refund_amount
        refund.refund_method = RefundRequest.RefundMethod.BANK_TRANSFER
        refund.reason = reason[:1000] if reason else '返金'
        refund.status = status
        refund.process_notes = process_notes

        if status == RefundRequest.Status.COMPLETED and refund_date:
            refund.processed_at = timezone.make_aware(datetime.combine(refund_date, datetime.min.time()))

        if status in [RefundRequest.Status.APPROVED, RefundRequest.Status.COMPLETED]:
            if not refund.approved_at:
                refund.approved_at = created_at or timezone.now()

        if not dry_run:
            refund.save()

        return 'new' if created else 'updated'

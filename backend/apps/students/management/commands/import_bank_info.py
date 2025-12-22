"""
T1 保護者銀行情報インポートコマンド
CSVファイルから保護者の銀行口座情報をインポートする
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction, models
from apps.students.models import Guardian
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'T1 保護者銀行情報CSVをインポート'

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

        updated_count = 0
        skipped_count = 0
        not_found_count = 0
        errors = []

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'総行数: {len(rows)}')

        for row in rows:
            try:
                with transaction.atomic():
                    result = self._import_bank_info(row, tenant, dry_run)
                    if result == 'updated':
                        updated_count += 1
                    elif result == 'skipped':
                        skipped_count += 1
                    elif result == 'not_found':
                        not_found_count += 1
            except Exception as e:
                errors.append(f"保護者 {row.get('保護者ID', 'unknown')}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f'''
インポート完了:
- 更新: {updated_count}件
- スキップ（銀行情報なし）: {skipped_count}件
- 保護者未登録: {not_found_count}件
- エラー: {len(errors)}件
'''))

        if errors[:10]:
            self.stderr.write('エラー詳細（最初の10件）:')
            for err in errors[:10]:
                self.stderr.write(f'  {err}')

    def _parse_account_type(self, account_type_str):
        """口座種別をパース"""
        if not account_type_str:
            return 'ordinary'
        if account_type_str in ['1', '普通', '普通預金']:
            return 'ordinary'
        elif account_type_str in ['2', '当座', '当座預金']:
            return 'checking'
        elif account_type_str in ['4', '貯蓄', '貯蓄預金']:
            return 'savings'
        return 'ordinary'

    def _import_bank_info(self, row, tenant, dry_run):
        """銀行情報をインポート"""
        guardian_id = row.get('保護者ID', '')

        if not guardian_id:
            return 'skipped'

        # 銀行情報があるかチェック
        bank_name = row.get('銀行名', '') or ''
        bank_code = row.get('銀行番号', '') or ''
        account_number = row.get('口座番号', '') or ''
        account_holder_kana = row.get('口座名義（ｶﾅ）', '') or ''

        # 銀行情報がすべて空の場合はスキップ
        if not bank_name and not bank_code and not account_number and not account_holder_kana:
            return 'skipped'

        # 保護者を検索
        guardian = Guardian.objects.filter(
            models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
        ).filter(
            models.Q(old_id=guardian_id) | models.Q(guardian_no=guardian_id)
        ).first()

        if not guardian:
            return 'not_found'

        # 銀行情報を更新
        guardian.bank_name = bank_name
        guardian.bank_code = bank_code
        guardian.branch_name = row.get('支店名', '') or ''
        guardian.branch_code = row.get('支店番号', '') or ''
        guardian.account_type = self._parse_account_type(row.get('口座種別', ''))
        guardian.account_number = account_number
        guardian.account_holder_kana = account_holder_kana
        # 口座名義はカナから推測（カナがあれば設定）
        if account_holder_kana and not guardian.account_holder:
            guardian.account_holder = account_holder_kana

        if not dry_run:
            guardian.save()

        return 'updated'

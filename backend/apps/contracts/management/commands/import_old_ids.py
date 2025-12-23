"""
旧IDインポートコマンド
ユーザー契約情報とT5追加請求からold_idをインポート
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import Contract, StudentItem
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = '旧IDをCSVからインポート'

    def add_arguments(self, parser):
        parser.add_argument('--contract-csv', type=str, help='ユーザー契約情報CSVのパス')
        parser.add_argument('--item-csv', type=str, help='T5追加請求CSVのパス')
        parser.add_argument('--tenant', type=str, default=None, help='テナントID')
        parser.add_argument('--dry-run', action='store_true', help='実際には保存しない')

    def handle(self, *args, **options):
        contract_csv = options.get('contract_csv')
        item_csv = options.get('item_csv')
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
        self.stdout.write(f'Dry run: {dry_run}')

        # Contract old_idをインポート
        if contract_csv:
            self._import_contract_old_ids(contract_csv, tenant, dry_run)

        # StudentItem old_idをインポート
        if item_csv:
            self._import_item_old_ids(item_csv, tenant, dry_run)

    def _import_contract_old_ids(self, csv_file, tenant, dry_run):
        """ユーザー契約情報からContract.old_idをインポート"""
        self.stdout.write(f'\n=== Contract old_id インポート ===')
        self.stdout.write(f'CSVファイル: {csv_file}')

        updated_count = 0
        not_found_count = 0
        errors = []

        # contract_noからContractを取得するキャッシュ
        contract_cache = {}
        for c in Contract.objects.filter(tenant_id=tenant.id):
            contract_cache[c.contract_no] = c

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'総行数: {len(rows)}')

        for row in rows:
            try:
                # 受講ID = contract_no (UC...)
                contract_no = row.get('受講ID', '').strip()
                # 契約ID = old_id (24GOK_...)
                old_id = row.get('契約ID', '').strip()

                if not contract_no or not old_id:
                    continue

                contract = contract_cache.get(contract_no)
                if not contract:
                    not_found_count += 1
                    continue

                # old_idが既に設定されている場合はスキップ
                if contract.old_id and contract.old_id != contract_no:
                    continue

                contract.old_id = old_id
                if not dry_run:
                    contract.save(update_fields=['old_id'])
                updated_count += 1

            except Exception as e:
                errors.append(f"受講ID {row.get('受講ID', 'unknown')}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f'''
Contract old_id インポート完了:
- 更新: {updated_count}件
- 未発見: {not_found_count}件
- エラー: {len(errors)}件
'''))

        if errors[:10]:
            self.stderr.write('エラー詳細（最初の10件）:')
            for err in errors[:10]:
                self.stderr.write(f'  {err}')

    def _import_item_old_ids(self, csv_file, tenant, dry_run):
        """T5追加請求からStudentItem.old_idをインポート"""
        self.stdout.write(f'\n=== StudentItem old_id インポート ===')
        self.stdout.write(f'CSVファイル: {csv_file}')

        updated_count = 0
        not_found_count = 0
        already_set_count = 0
        errors = []

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'総行数: {len(rows)}')

        # 請求ID (AB...) でStudentItemを検索
        for row in rows:
            try:
                # 請求ID = StudentItem識別子 (AB...)
                item_id = row.get('請求ID', '').strip()
                # 対象　請求ID = old_id (24GYJ_1000247_61)
                old_id = row.get('対象　請求ID', '').strip()

                if not item_id or not old_id:
                    continue

                # StudentItemを検索（item_idで）
                item = StudentItem.objects.filter(
                    tenant_id=tenant.id,
                    old_id=item_id  # ABで始まるIDで検索
                ).first()

                if not item:
                    # billing_refで検索
                    item = StudentItem.objects.filter(
                        tenant_id=tenant.id
                    ).filter(
                        notes__icontains=item_id
                    ).first()

                if not item:
                    not_found_count += 1
                    continue

                # 既に旧形式のold_idが設定されている場合はスキップ
                if item.old_id and item.old_id.startswith('24'):
                    already_set_count += 1
                    continue

                item.old_id = old_id
                if not dry_run:
                    item.save(update_fields=['old_id'])
                updated_count += 1

            except Exception as e:
                errors.append(f"請求ID {row.get('請求ID', 'unknown')}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f'''
StudentItem old_id インポート完了:
- 更新: {updated_count}件
- 未発見: {not_found_count}件
- 既設定: {already_set_count}件
- エラー: {len(errors)}件
'''))

        if errors[:10]:
            self.stderr.write('エラー詳細（最初の10件）:')
            for err in errors[:10]:
                self.stderr.write(f'  {err}')

"""
ユーザー契約情報CSVから既存のConfirmedBillingのitems_snapshotを更新するコマンド

Usage:
    # ドライラン
    python manage.py update_from_user_contracts --csv /path/to/csv --dry-run

    # 実行
    python manage.py update_from_user_contracts --csv /path/to/csv
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ConfirmedBilling


class Command(BaseCommand):
    help = 'ユーザー契約情報CSVからitems_snapshotを更新'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            required=True,
            help='ユーザー契約情報CSVファイルのパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='対象年（指定しない場合は全て）'
        )
        parser.add_argument(
            '--month',
            type=int,
            help='対象月（指定しない場合は全て）'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options['dry_run']
        year = options.get('year')
        month = options.get('month')

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # CSVを読み込んでマッピングを作成
        self.stdout.write(f'CSVファイルを読み込み中: {csv_path}')
        contracts_map = self.load_csv(csv_path)
        self.stdout.write(f'契約情報を{len(contracts_map)}件読み込みました')

        # 対象のConfirmedBillingを取得
        queryset = ConfirmedBilling.objects.all()
        if year:
            queryset = queryset.filter(year=year)
        if month:
            queryset = queryset.filter(month=month)

        total_count = queryset.count()
        updated_count = 0
        skipped_count = 0

        self.stdout.write(f'対象請求データ: {total_count}件')

        for billing in queryset:
            try:
                result = self.update_snapshot(billing, contracts_map, dry_run)
                if result:
                    updated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'エラー: {billing.billing_no} - {e}')
                )

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
対象件数: {total_count}件
更新件数: {updated_count}件
スキップ: {skipped_count}件
'''))

    def load_csv(self, csv_path):
        """CSVを読み込んで契約IDと受講IDの両方をキーにしたマップを作成"""
        contracts_map = {}

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                contract_id = row.get('契約ID', '').strip()
                course_id = row.get('受講ID', '').strip()

                if not contract_id and not course_id:
                    continue

                info = {
                    'course_id': course_id,
                    'guardian_id': row.get('保護者ID', '').strip(),
                    'student_id': row.get('生徒ID', '').strip(),
                    'contract_id': contract_id,
                    'contract_name': row.get('契約名', '').strip(),
                    'brand_name': row.get('Class用ブランド名', '').strip(),
                    'grade': row.get('契約学年', '').strip(),
                }

                # 契約IDをキーに登録（同じ契約IDは最初のエントリを使用）
                if contract_id and contract_id not in contracts_map:
                    contracts_map[contract_id] = info

                # 受講IDもキーに登録（ユニークなので上書きOK）
                if course_id:
                    contracts_map[course_id] = info

        return contracts_map

    def update_snapshot(self, billing, contracts_map, dry_run) -> bool:
        """items_snapshotを更新"""
        items_snapshot = billing.items_snapshot or []

        if not items_snapshot:
            return False

        updated = False
        new_items = []

        for item in items_snapshot:
            new_item = dict(item)
            old_id = item.get('old_id', '')

            # old_idでマッピングを検索
            if old_id and old_id in contracts_map:
                contract_info = contracts_map[old_id]

                # ブランド名を更新
                if contract_info['brand_name']:
                    new_item['brand_name'] = contract_info['brand_name']

                # 契約名を更新
                if contract_info['contract_name']:
                    new_item['course_name'] = contract_info['contract_name']
                    if not new_item.get('product_name'):
                        new_item['product_name'] = contract_info['contract_name']

                # 契約IDを更新
                if contract_info['contract_id']:
                    new_item['contract_no'] = contract_info['contract_id']

                updated = True
                self.stdout.write(
                    f'  更新: {billing.billing_no} - {old_id} → {contract_info["brand_name"]} / {contract_info["contract_name"]}'
                )

            new_items.append(new_item)

        if not updated:
            return False

        if dry_run:
            self.stdout.write(f'  [ドライラン] {billing.billing_no}: items_snapshot 更新')
        else:
            with transaction.atomic():
                billing.items_snapshot = new_items
                billing.save(update_fields=['items_snapshot'])
            self.stdout.write(self.style.SUCCESS(f'  更新完了: {billing.billing_no}'))

        return True

"""
T1 保護者マスタCSVインポートコマンド

Usage:
    python manage.py import_t1_guardian /path/to/T1_guardian.csv --dry-run
    python manage.py import_t1_guardian /path/to/T1_guardian.csv
"""
import csv
from django.core.management.base import BaseCommand
from django.db import transaction, models
from apps.students.models import Guardian
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'T1 保護者マスタCSVをインポート'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='CSVファイルのパス')
        parser.add_argument('--dry-run', action='store_true', help='実際には保存しない')
        parser.add_argument('--clear', action='store_true', help='既存データを削除してからインポート')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        clear = options.get('clear', False)

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stderr.write(self.style.ERROR('テナントが見つかりません'))
            return

        self.stdout.write(f'テナント: {tenant.tenant_name}')
        self.stdout.write(f'CSVファイル: {csv_file}')
        self.stdout.write(f'Dry run: {dry_run}')

        # 既存データ削除
        if clear and not dry_run:
            count = Guardian.objects.all().delete()[0]
            self.stdout.write(f'既存保護者データ削除: {count}件')

        created_count = 0
        updated_count = 0
        errors = []

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'総行数: {len(rows)}')

        for row in rows:
            try:
                guardian_no = row.get('保護者番号', '').strip()
                old_id = row.get('旧システムID', '').strip() or guardian_no

                if not guardian_no:
                    continue

                # 既存チェック
                guardian = Guardian.objects.filter(
                    models.Q(tenant_id=tenant.id) | models.Q(tenant_ref=tenant)
                ).filter(
                    models.Q(old_id=old_id) | models.Q(guardian_no=guardian_no)
                ).first()

                created = guardian is None
                if created:
                    guardian = Guardian(tenant_ref=tenant, tenant_id=tenant.id)

                # フィールド設定
                guardian.guardian_no = guardian_no
                guardian.old_id = old_id
                guardian.last_name = row.get('姓', '') or ''
                guardian.first_name = row.get('名', '') or ''
                guardian.last_name_kana = row.get('姓（カナ）', '') or ''
                guardian.first_name_kana = row.get('名（カナ）', '') or ''
                guardian.last_name_roman = row.get('姓（ローマ字）', '') or ''
                guardian.first_name_roman = row.get('名（ローマ字）', '') or ''
                guardian.email = row.get('メールアドレス', '') or ''
                guardian.phone = row.get('電話番号', '') or ''
                guardian.mobile_phone = row.get('携帯電話', '') or ''
                guardian.workplace = row.get('勤務先', '') or ''
                guardian.workplace_phone = row.get('勤務先電話番号', '') or ''
                guardian.postal_code = (row.get('郵便番号', '') or '').replace('-', '').replace('ー', '')
                guardian.prefecture = row.get('都道府県', '') or ''
                guardian.city = row.get('市区町村', '') or ''
                guardian.address1 = row.get('住所1', '') or ''
                guardian.address2 = row.get('住所2', '') or ''
                guardian.notes = row.get('備考', '') or ''

                if not dry_run:
                    guardian.save()

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                errors.append(f"{row.get('保護者番号', '?')}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
新規作成: {created_count}件
更新: {updated_count}件
エラー: {len(errors)}件
'''))

        if errors[:10]:
            self.stderr.write('エラー詳細（最初の10件）:')
            for err in errors[:10]:
                self.stderr.write(f'  {err}')

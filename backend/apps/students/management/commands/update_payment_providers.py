"""
保護者の決済代行会社（payment_provider）をCSVから更新するコマンド

Usage:
    python manage.py update_payment_providers /path/to/T1_保護者銀行情報.csv

CSVの「CSV出力パターン」列を使用して、JACCS/UFJファクターを判定します。
"""
import csv
from django.core.management.base import BaseCommand
from apps.students.models import Guardian


class Command(BaseCommand):
    help = '保護者の決済代行会社（payment_provider）をCSVから更新'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='CSVファイルのパス')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には更新せず、更新内容を表示のみ',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']

        updated_count = 0
        not_found_count = 0
        skipped_count = 0
        errors = []

        self.stdout.write(f"CSVファイルを読み込み中: {csv_file}")

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                guardian_id = row.get('保護者ID', '').strip()
                csv_pattern = row.get('CSV出力パターン', '').strip().lower()
                debit_start = row.get('引落開始月', '').strip()

                if not guardian_id:
                    skipped_count += 1
                    continue

                # payment_providerの値を決定
                if csv_pattern == 'ufjfactors':
                    payment_provider = 'ufjfactors'
                elif csv_pattern == 'jaccs':
                    payment_provider = 'jaccs'
                elif csv_pattern == 'chukyo_finance':
                    payment_provider = 'chukyo_finance'
                else:
                    # CSV出力パターンが空または不明な場合はスキップ
                    skipped_count += 1
                    continue

                # 保護者を検索（guardian_noまたはold_idで）
                guardian = Guardian.objects.filter(guardian_no=guardian_id).first()
                if not guardian:
                    guardian = Guardian.objects.filter(old_id=guardian_id).first()

                if not guardian:
                    not_found_count += 1
                    if not_found_count <= 10:  # 最初の10件のみ表示
                        errors.append(f"保護者ID {guardian_id} が見つかりません")
                    continue

                # 更新
                if dry_run:
                    self.stdout.write(
                        f"[DRY-RUN] {guardian.guardian_no} ({guardian.last_name}{guardian.first_name}): "
                        f"payment_provider={payment_provider}, debit_start_date={debit_start}"
                    )
                else:
                    guardian.payment_provider = payment_provider
                    if debit_start:
                        guardian.debit_start_date = debit_start
                    guardian.save(update_fields=['payment_provider', 'debit_start_date'])

                updated_count += 1

        # 結果表示
        self.stdout.write(self.style.SUCCESS(f"\n=== 処理結果 ==="))
        self.stdout.write(f"更新: {updated_count}件")
        self.stdout.write(f"見つからず: {not_found_count}件")
        self.stdout.write(f"スキップ: {skipped_count}件")

        if errors:
            self.stdout.write(self.style.WARNING(f"\n=== エラー（一部） ==="))
            for err in errors[:10]:
                self.stdout.write(f"  {err}")
            if len(errors) > 10:
                self.stdout.write(f"  ... 他{len(errors) - 10}件")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY-RUN モード] 実際の更新は行われていません"))

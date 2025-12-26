"""
契約データから入会日を取得して生徒のenrollment_dateを更新するコマンド

Usage:
    python manage.py import_enrollment_dates /path/to/T4_contract_data.csv --dry-run
    python manage.py import_enrollment_dates /path/to/T4_contract_data.csv
"""
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.students.models import Student


class Command(BaseCommand):
    help = '契約データから入会日（最初の契約開始日）を取得して生徒を更新'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='CSVファイルのパス')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='既存の入会日を上書きする'
        )

    def parse_date(self, date_str):
        """日付文字列をパース"""
        if not date_str or date_str.strip() == '':
            return None

        date_str = date_str.strip()

        # 様々な日付形式に対応
        formats = [
            '%Y/%m/%d',
            '%Y-%m-%d',
            '%Y年%m月%d日',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        overwrite = options['overwrite']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # CSVを読み込んで生徒ごとの最初の契約開始日を取得
        student_enrollment_dates = {}  # {student_id: earliest_start_date}

        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    student_id = row.get('生徒ID', '').strip()
                    start_date_str = row.get('開始日', '').strip()

                    if not student_id:
                        continue

                    start_date = self.parse_date(start_date_str)
                    if not start_date:
                        continue

                    # 2100年などの無効な日付をスキップ
                    if start_date.year > 2030:
                        continue

                    # 既存の日付より早い場合は更新
                    if student_id not in student_enrollment_dates:
                        student_enrollment_dates[student_id] = start_date
                    elif start_date < student_enrollment_dates[student_id]:
                        student_enrollment_dates[student_id] = start_date

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'ファイルが見つかりません: {csv_file}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'CSVの読み込みエラー: {e}'))
            return

        self.stdout.write(f'CSVから {len(student_enrollment_dates)} 件の生徒入会日を取得')

        # 生徒を更新
        updated_count = 0
        skipped_count = 0
        not_found_count = 0

        for old_id, enrollment_date in student_enrollment_dates.items():
            # old_idで生徒を検索
            student = Student.objects.filter(old_id=old_id).first()

            if not student:
                not_found_count += 1
                continue

            # 既存の入会日がある場合
            if student.enrollment_date and not overwrite:
                skipped_count += 1
                continue

            # 更新
            if dry_run:
                self.stdout.write(
                    f'  [ドライラン] {student.full_name} (ID: {old_id}): '
                    f'入会日 {student.enrollment_date} → {enrollment_date}'
                )
            else:
                student.enrollment_date = enrollment_date
                student.save(update_fields=['enrollment_date'])

            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
更新: {updated_count}件
スキップ（既存入会日あり）: {skipped_count}件
生徒が見つからない: {not_found_count}件
'''))

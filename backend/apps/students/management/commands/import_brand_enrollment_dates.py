"""
契約データからブランドごとの入会日を取得してStudentSchoolを更新するコマンド

Usage:
    python manage.py import_brand_enrollment_dates /path/to/T4_contract_data.csv --dry-run
    python manage.py import_brand_enrollment_dates /path/to/T4_contract_data.csv
"""
import csv
from datetime import datetime
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.students.models import Student, StudentSchool
from apps.schools.models import Brand, School
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = '契約データからブランドごとの入会日を取得してStudentSchoolを更新・作成'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='CSVファイルのパス')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )

    def parse_date(self, date_str):
        """日付文字列をパース"""
        if not date_str or date_str.strip() == '':
            return None

        date_str = date_str.strip()
        formats = ['%Y/%m/%d', '%Y-%m-%d', '%Y年%m月%d日']

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # ブランドマッピング
        brand_map = {}
        for b in Brand.objects.all():
            brand_map[b.brand_name] = b
            if b.brand_code:
                brand_map[b.brand_code] = b

        # デフォルト校舎
        default_school = School.objects.first()

        # CSVから生徒ごと・ブランドごとの最初の契約開始日を取得
        student_brand_dates = {}  # {student_id: {brand_name: earliest_start_date}}

        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    student_id = row.get('生徒ID', '').strip()
                    brand_name = row.get('Class用ブランド名', '').strip()
                    start_date = self.parse_date(row.get('開始日', ''))

                    if not student_id or not brand_name or not start_date:
                        continue

                    # 無効な日付をスキップ
                    if start_date.year > 2030:
                        continue

                    if student_id not in student_brand_dates:
                        student_brand_dates[student_id] = {}

                    # 既存の日付より早い場合は更新
                    if brand_name not in student_brand_dates[student_id]:
                        student_brand_dates[student_id][brand_name] = start_date
                    elif start_date < student_brand_dates[student_id][brand_name]:
                        student_brand_dates[student_id][brand_name] = start_date

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'ファイルが見つかりません: {csv_file}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'CSVの読み込みエラー: {e}'))
            return

        # 統計
        total_records = sum(len(brands) for brands in student_brand_dates.values())
        self.stdout.write(f'CSVから {len(student_brand_dates)} 人の生徒、{total_records} 件のブランド入会日を取得')

        # 更新・作成
        created_count = 0
        updated_count = 0
        skipped_count = 0
        not_found_students = 0
        not_found_brands = set()

        for old_id, brand_dates in student_brand_dates.items():
            # 生徒を検索
            student = Student.objects.filter(old_id=old_id).first()
            if not student:
                not_found_students += 1
                continue

            for brand_name, enrollment_date in brand_dates.items():
                # ブランドを検索
                brand = brand_map.get(brand_name)
                if not brand:
                    not_found_brands.add(brand_name)
                    continue

                # 既存のStudentSchoolを検索
                existing = StudentSchool.objects.filter(
                    student=student,
                    brand=brand
                ).first()

                if existing:
                    # 既存のstart_dateより早い場合は更新
                    if existing.start_date is None or enrollment_date < existing.start_date:
                        if dry_run:
                            self.stdout.write(
                                f'  [更新] {student.full_name} - {brand_name}: '
                                f'{existing.start_date} → {enrollment_date}'
                            )
                        else:
                            existing.start_date = enrollment_date
                            existing.save(update_fields=['start_date'])
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    # 新規作成
                    school = student.primary_school or default_school
                    if dry_run:
                        self.stdout.write(
                            f'  [新規] {student.full_name} - {brand_name}: {enrollment_date}'
                        )
                    else:
                        StudentSchool.objects.create(
                            tenant_id=tenant.id,
                            tenant_ref=tenant,
                            student=student,
                            school=school,
                            brand=brand,
                            start_date=enrollment_date,
                            enrollment_status='active',
                            is_primary=False
                        )
                    created_count += 1

        if not_found_brands:
            self.stdout.write(self.style.WARNING(f'\n見つからないブランド: {", ".join(sorted(not_found_brands))}'))

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
新規作成: {created_count}件
更新: {updated_count}件
スキップ（既存の日付が早い）: {skipped_count}件
生徒が見つからない: {not_found_students}件
'''))

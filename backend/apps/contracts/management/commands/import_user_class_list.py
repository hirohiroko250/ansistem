"""
OZA User Class Listから生徒クラス所属を更新するコマンド

Usage:
    python manage.py import_user_class_list /path/to/file.xlsx --dry-run
    python manage.py import_user_class_list /path/to/file.xlsx
"""
import pandas as pd
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contracts.models import Contract, Course
from apps.students.models import Student, Guardian
from apps.schools.models import Brand, School
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'OZA User Class Listから生徒クラス所属を更新'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Excelファイルパス')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='既存の契約を削除してから作成'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        dry_run = options['dry_run']
        clear = options['clear']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # Excel読み込み
        try:
            df = pd.read_excel(file_path)
            self.stdout.write(f'読み込み: {len(df)}件')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ファイル読み込みエラー: {e}'))
            return

        # 校舎マッピング
        school_map = {}
        for school in School.objects.all():
            school_map[school.school_code] = school
            if school.school_name:
                school_map[school.school_name] = school

        # ブランドマッピング
        brand_map = {}
        for brand in Brand.objects.all():
            brand_map[brand.brand_code] = brand
            if brand.brand_name:
                brand_map[brand.brand_name] = brand

        # 生徒マッピング（old_id -> Student）
        student_map = {}
        for student in Student.objects.all():
            if student.old_id:
                student_map[str(student.old_id)] = student

        # 曜日マッピング
        day_map = {
            '月': 1, '火': 2, '水': 3, '木': 4, '金': 5, '土': 6, '日': 0
        }

        # 既存契約を収集（重複防止用）
        existing = set(
            Contract.objects.values_list('tenant_id', 'contract_no', 'student_id')
        )

        created_count = 0
        updated_count = 0
        not_found_count = 0
        skipped_count = 0

        for idx, row in df.iterrows():
            try:
                student_old_id = str(int(row['生徒ID'])) if pd.notna(row['生徒ID']) else None
                if not student_old_id:
                    continue

                student = student_map.get(student_old_id)
                if not student:
                    not_found_count += 1
                    if not_found_count <= 10:
                        self.stdout.write(f'  生徒見つからず: old_id={student_old_id}')
                    continue

                # ブランド
                brand_code = row.get('ブランドID', '')
                brand = brand_map.get(brand_code)
                if not brand:
                    brand_name = row.get('ブランド名', '')
                    brand = brand_map.get(brand_name)

                if not brand:
                    skipped_count += 1
                    continue

                # 校舎
                school_code = row.get('校舎ID', '')
                school = school_map.get(school_code)
                if not school:
                    school_name = row.get('校舎名', '')
                    school = school_map.get(school_name)
                if not school:
                    school = School.objects.first()

                # 契約番号を生成（ブランド+生徒ID）
                contract_no = f"{brand.brand_code}_{student_old_id}"

                # 曜日・時間
                day_str = row.get('曜日', '')
                day_of_week = day_map.get(day_str)

                start_time = None
                if pd.notna(row.get('開始時間')):
                    try:
                        if isinstance(row['開始時間'], str):
                            start_time = datetime.strptime(row['開始時間'], '%H:%M:%S').time()
                        else:
                            start_time = row['開始時間']
                    except:
                        pass

                # 開始日・終了日
                start_date = None
                if pd.notna(row.get('ユーザークラス開始日')):
                    try:
                        start_date = pd.to_datetime(row['ユーザークラス開始日']).date()
                    except:
                        pass
                if not start_date:
                    start_date = datetime.now().date()

                end_date = None
                if pd.notna(row.get('ユーザークラス終了日')):
                    try:
                        end_date = pd.to_datetime(row['ユーザークラス終了日']).date()
                    except:
                        pass

                # 重複チェック
                key = (tenant.id, contract_no, student.id)
                if key in existing:
                    skipped_count += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f'  [ドライラン] {student.full_name}: {brand.brand_name} @ {school.school_name if school else "?"} ({day_str})'
                    )
                else:
                    with transaction.atomic():
                        contract, created = Contract.objects.update_or_create(
                            tenant_id=tenant.id,
                            contract_no=contract_no,
                            student=student,
                            defaults={
                                'tenant_ref': tenant,
                                'old_id': contract_no,
                                'guardian': student.guardians.first() if hasattr(student, 'guardians') else None,
                                'school': school,
                                'brand': brand,
                                'status': 'active',
                                'contract_date': start_date,
                                'start_date': start_date,
                                'end_date': end_date,
                                'day_of_week': day_of_week,
                                'start_time': start_time,
                            }
                        )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                existing.add(key)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'エラー (row {idx}): {e}'))
                continue

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
新規作成: {created_count}件
更新: {updated_count}件
生徒見つからず: {not_found_count}件
スキップ: {skipped_count}件
'''))

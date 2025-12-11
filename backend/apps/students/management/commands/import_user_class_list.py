"""
UserClassList Excelファイルから生徒のクラス所属情報をインポート

Usage:
    python manage.py import_user_class_list '/path/to/UserClassList.xlsx'
    python manage.py import_user_class_list '/path/to/UserClassList.xlsx' --dry-run
"""
import re
import pandas as pd
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.students.models import Student, Guardian, StudentGuardian, StudentSchool
from apps.schools.models import School, Brand
from apps.lessons.models import LessonSchedule, TimeSlot, GroupLessonEnrollment
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'UserClassList Excelファイルから生徒のクラス所属情報をインポート'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Excelファイルのパス')
        parser.add_argument('--dry-run', action='store_true', help='実際には保存せずに処理内容を表示')
        parser.add_argument('--tenant-code', type=str, default='100000', help='テナントコード')

    def handle(self, *args, **options):
        file_path = options['file_path']
        dry_run = options['dry_run']
        tenant_code = options['tenant_code']

        # テナント取得
        try:
            tenant = Tenant.objects.get(tenant_code=tenant_code)
            tenant_id = tenant.id
            self.stdout.write(f'テナント: {tenant_code} ({tenant_id})')
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'テナント {tenant_code} が見つかりません'))
            return

        self.stdout.write(f'ファイル読み込み中: {file_path}')
        df = pd.read_excel(file_path)

        self.stdout.write(f'行数: {len(df)}')
        self.stdout.write(f'カラム: {df.columns.tolist()}')

        # 統計
        stats = {
            'guardians_created': 0,
            'guardians_updated': 0,
            'students_created': 0,
            'students_updated': 0,
            'student_schools_created': 0,
            'enrollments_created': 0,
            'errors': [],
        }

        # 曜日マッピング
        day_mapping = {
            '月': 0, '火': 1, '水': 2, '木': 3, '金': 4, '土': 5, '日': 6
        }

        with transaction.atomic():
            for idx, row in df.iterrows():
                try:
                    # ===== 保護者の作成/更新 =====
                    guardian_id = str(row['保護者ID']).strip() if pd.notna(row['保護者ID']) else None
                    if not guardian_id:
                        stats['errors'].append(f'行{idx+2}: 保護者IDが空')
                        continue

                    guardian_last_name = str(row['保護者名1']).strip() if pd.notna(row['保護者名1']) else ''
                    guardian_first_name = str(row['保護者名2']).strip() if pd.notna(row['保護者名2']) else ''
                    guardian_email = str(row['保護者メールアドレス1']).strip() if pd.notna(row['保護者メールアドレス1']) else ''
                    emergency_tel = str(row['緊急TEL']).strip() if pd.notna(row['緊急TEL']) else ''

                    guardian, created = Guardian.objects.update_or_create(
                        tenant_id=tenant_id,
                        guardian_no=guardian_id,
                        defaults={
                            'last_name': guardian_last_name,
                            'first_name': guardian_first_name,
                            'email': guardian_email,
                            'phone': emergency_tel,
                        }
                    )
                    if created:
                        stats['guardians_created'] += 1
                    else:
                        stats['guardians_updated'] += 1

                    # ===== 生徒の作成/更新 =====
                    student_id = str(row['生徒ID']).strip() if pd.notna(row['生徒ID']) else None
                    if not student_id:
                        stats['errors'].append(f'行{idx+2}: 生徒IDが空')
                        continue

                    student_last_name = str(row['生徒名1']).strip() if pd.notna(row['生徒名1']) else ''
                    student_first_name = str(row['生徒名2']).strip() if pd.notna(row['生徒名2']) else ''
                    grade_text = str(row['学年']).strip() if pd.notna(row['学年']) else ''
                    gender_raw = str(row['性別']).strip() if pd.notna(row['性別']) else ''
                    gender = 'male' if gender_raw == '男' else 'female' if gender_raw == '女' else ''
                    romaji = str(row['ローマ字読み']).strip() if pd.notna(row['ローマ字読み']) else ''

                    # 入会日・退会日
                    start_date_raw = row['開始日'] if pd.notna(row['開始日']) else None
                    withdrawal_date_raw = row['退会日'] if pd.notna(row['退会日']) else None

                    enrollment_date = None
                    if start_date_raw:
                        if isinstance(start_date_raw, datetime):
                            enrollment_date = start_date_raw.date()
                        elif isinstance(start_date_raw, str):
                            enrollment_date = datetime.strptime(start_date_raw, '%Y-%m-%d').date()

                    withdrawal_date = None
                    if withdrawal_date_raw:
                        if isinstance(withdrawal_date_raw, datetime):
                            withdrawal_date = withdrawal_date_raw.date()
                        elif isinstance(withdrawal_date_raw, str):
                            try:
                                withdrawal_date = datetime.strptime(withdrawal_date_raw.split()[0], '%Y-%m-%d').date()
                            except:
                                pass

                    # ステータス判定
                    is_suspended = str(row['休会中']).strip() == '○' if pd.notna(row['休会中']) else False
                    if withdrawal_date:
                        status = 'withdrawn'
                    elif is_suspended:
                        status = 'suspended'
                    else:
                        status = 'enrolled'

                    student, created = Student.objects.update_or_create(
                        tenant_id=tenant_id,
                        student_no=student_id,
                        defaults={
                            'last_name': student_last_name,
                            'first_name': student_first_name,
                            'last_name_kana': romaji.split()[0] if romaji and ' ' in romaji else romaji,
                            'first_name_kana': romaji.split()[1] if romaji and ' ' in romaji else '',
                            'grade_text': grade_text,
                            'gender': gender,
                            'status': status,
                            'enrollment_date': enrollment_date,
                            'withdrawal_date': withdrawal_date,
                            'guardian': guardian,
                        }
                    )
                    if created:
                        stats['students_created'] += 1
                    else:
                        stats['students_updated'] += 1

                    # ===== 生徒-保護者関連 =====
                    StudentGuardian.objects.get_or_create(
                        tenant_id=tenant_id,
                        student=student,
                        guardian=guardian,
                        defaults={
                            'is_primary': True,
                            'is_emergency_contact': True,
                            'is_billing_target': True,
                        }
                    )

                    # ===== 校舎・ブランド =====
                    school_name_raw = str(row['校舎名']).strip() if pd.notna(row['校舎名']) else None
                    brand_name_raw = str(row['ブランド名']).strip() if pd.notna(row['ブランド名']) else None

                    school = None
                    brand = None

                    if school_name_raw:
                        # 校舎名から校舎を検索
                        # "尾張旭校Owariasahi" → "尾張旭校" にマッチ
                        # ローマ字部分を除去（日本語の後ろのアルファベットを削除）
                        school_name_jp = re.sub(r'[A-Za-z]+$', '', school_name_raw).strip()

                        # まず完全一致
                        school = School.objects.filter(tenant_id=tenant_id, school_name=school_name_jp).first()
                        if not school:
                            # 部分一致（「校」の前の文字列で検索）
                            if '校' in school_name_jp:
                                base_name = school_name_jp.split('校')[0]
                                school = School.objects.filter(tenant_id=tenant_id, school_name__startswith=base_name).first()
                        if not school:
                            # さらに部分一致
                            school = School.objects.filter(tenant_id=tenant_id, school_name__icontains=school_name_jp.replace('校', '')).first()
                        if not school:
                            self.stdout.write(self.style.WARNING(f'行{idx+2}: 校舎 {school_name_raw} → {school_name_jp} が見つかりません'))

                    if brand_name_raw:
                        # 完全一致を最初に試す
                        brand = Brand.objects.filter(tenant_id=tenant_id, brand_name=brand_name_raw).first()
                        if not brand:
                            # 部分一致
                            brand = Brand.objects.filter(tenant_id=tenant_id, brand_name__icontains=brand_name_raw).first()
                        if not brand:
                            self.stdout.write(self.style.WARNING(f'行{idx+2}: ブランド {brand_name_raw} が見つかりません'))

                    # ===== 生徒所属（StudentSchool） =====
                    if school and brand:
                        user_class_start_raw = row['ユーザークラス開始日'] if pd.notna(row['ユーザークラス開始日']) else None
                        user_class_start = None
                        if user_class_start_raw:
                            if isinstance(user_class_start_raw, datetime):
                                user_class_start = user_class_start_raw.date()
                            elif isinstance(user_class_start_raw, str):
                                user_class_start = datetime.strptime(user_class_start_raw.split()[0], '%Y-%m-%d').date()

                        user_class_end_raw = row['ユーザークラス終了日'] if pd.notna(row['ユーザークラス終了日']) else None
                        user_class_end = None
                        if user_class_end_raw:
                            if isinstance(user_class_end_raw, datetime):
                                user_class_end = user_class_end_raw.date()
                            elif isinstance(user_class_end_raw, str):
                                try:
                                    user_class_end = datetime.strptime(user_class_end_raw.split()[0], '%Y-%m-%d').date()
                                except:
                                    pass

                        ss, ss_created = StudentSchool.objects.update_or_create(
                            tenant_id=tenant_id,
                            student=student,
                            school=school,
                            brand=brand,
                            defaults={
                                'start_date': user_class_start or enrollment_date or datetime.now().date(),
                                'end_date': user_class_end,
                                'is_primary': True,
                                'enrollment_status': 'active' if status == 'enrolled' else 'ended',
                            }
                        )
                        if ss_created:
                            stats['student_schools_created'] += 1

                        # 生徒の主所属を更新
                        if not student.primary_school:
                            student.primary_school = school
                            student.primary_brand = brand
                            student.save()

                    # ===== 曜日・時間帯情報 =====
                    day_of_week_str = str(row['曜日']).strip() if pd.notna(row['曜日']) else None
                    start_time_str = str(row['開始時間']).strip() if pd.notna(row['開始時間']) else None
                    class_name = str(row['クラス名']).strip() if pd.notna(row['クラス名']) else ''

                    if school and day_of_week_str and start_time_str and day_of_week_str in day_mapping:
                        day_of_week = day_mapping[day_of_week_str]

                        # TimeSlotを探す or 作成
                        slot_name = str(row['開講時間']).strip() if pd.notna(row['開講時間']) else ''

                        # GroupLessonEnrollmentを作成（後でスケジュールと紐づけ）
                        # このExcelはクラス所属のマスタなので、実際のスケジュールとは別に管理
                        # TODO: ClassScheduleモデルとの紐づけを検討

                except Exception as e:
                    stats['errors'].append(f'行{idx+2}: {str(e)}')
                    self.stdout.write(self.style.ERROR(f'行{idx+2}: {str(e)}'))

            if dry_run:
                self.stdout.write(self.style.WARNING('DRY RUN - ロールバックします'))
                raise Exception('Dry run - rolling back')

        # 結果表示
        self.stdout.write(self.style.SUCCESS(f'\n===== インポート結果 ====='))
        self.stdout.write(f'保護者作成: {stats["guardians_created"]}')
        self.stdout.write(f'保護者更新: {stats["guardians_updated"]}')
        self.stdout.write(f'生徒作成: {stats["students_created"]}')
        self.stdout.write(f'生徒更新: {stats["students_updated"]}')
        self.stdout.write(f'生徒所属作成: {stats["student_schools_created"]}')

        if stats['errors']:
            self.stdout.write(self.style.WARNING(f'\nエラー件数: {len(stats["errors"])}'))
            for error in stats['errors'][:10]:
                self.stdout.write(self.style.WARNING(f'  - {error}'))
            if len(stats['errors']) > 10:
                self.stdout.write(self.style.WARNING(f'  ... 他 {len(stats["errors"]) - 10} 件'))

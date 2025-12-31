"""
T2 生徒マスタCSVインポートコマンド

Usage:
    python manage.py import_t2_student /path/to/T2_student.csv --dry-run
    python manage.py import_t2_student /path/to/T2_student.csv
"""
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction, models
from apps.students.models import Student, Guardian
from apps.schools.models import School, Brand
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'T2 生徒マスタCSVをインポート'

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

        # 校舎マッピング
        school_map = {}
        for s in School.objects.all():
            school_map[s.school_name] = s
            if s.school_code:
                school_map[s.school_code] = s

        # ブランドマッピング
        brand_map = {}
        for b in Brand.objects.all():
            brand_map[b.brand_name] = b
            if b.brand_code:
                brand_map[b.brand_code] = b

        # 既存データ削除
        if clear and not dry_run:
            count = Student.objects.all().delete()[0]
            self.stdout.write(f'既存生徒データ削除: {count}件')

        created_count = 0
        updated_count = 0
        errors = []

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'総行数: {len(rows)}')

        for row in rows:
            try:
                student_no = row.get('生徒番号', '').strip()
                old_id = row.get('旧システムID', '').strip() or student_no

                if not student_no:
                    continue

                # 既存チェック
                student = Student.objects.filter(
                    models.Q(tenant_id=tenant.id) | models.Q(tenant_ref=tenant)
                ).filter(
                    models.Q(old_id=old_id) | models.Q(student_no=student_no)
                ).first()

                created = student is None
                if created:
                    student = Student(tenant_ref=tenant, tenant_id=tenant.id)

                # フィールド設定
                student.student_no = student_no
                student.old_id = old_id
                student.last_name = row.get('姓', '') or ''
                student.first_name = row.get('名', '') or ''
                student.last_name_kana = row.get('姓（カナ）', '') or ''
                student.first_name_kana = row.get('名（カナ）', '') or ''
                student.last_name_roman = row.get('姓（ローマ字）', '') or ''
                student.first_name_roman = row.get('名（ローマ字）', '') or ''
                student.nickname = row.get('ニックネーム', '') or ''
                student.display_name = row.get('表示名', '') or ''
                student.email = row.get('メールアドレス', '') or ''
                student.phone = row.get('電話番号', '') or ''
                student.line_id = row.get('LINE ID', '') or ''
                student.school_name = row.get('在籍学校名', '') or ''
                student.grade_text = row.get('学年', '') or ''
                student.notes = row.get('備考', '') or ''

                # 生年月日
                birth_date_str = row.get('生年月日', '')
                if birth_date_str:
                    try:
                        student.birth_date = datetime.strptime(birth_date_str, '%Y/%m/%d').date()
                    except ValueError:
                        try:
                            student.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            pass

                # 性別
                gender = row.get('性別', '')
                if gender in ['男', '男性']:
                    student.gender = 'male'
                elif gender in ['女', '女性']:
                    student.gender = 'female'

                # ステータス
                status = row.get('ステータス', '')
                if status == '在籍中' or status == '入会':
                    student.status = 'enrolled'
                elif status == '休会' or status == '休会中':
                    student.status = 'suspended'
                elif status == '退会':
                    student.status = 'withdrawn'
                elif status == '体験':
                    student.status = 'trial'
                else:
                    student.status = 'registered'

                # 入塾日・退塾日
                enroll_date_str = row.get('入塾日', '')
                if enroll_date_str:
                    try:
                        student.enrollment_date = datetime.strptime(enroll_date_str, '%Y/%m/%d').date()
                    except ValueError:
                        pass

                withdraw_date_str = row.get('退塾日', '')
                if withdraw_date_str:
                    try:
                        student.withdrawal_date = datetime.strptime(withdraw_date_str, '%Y/%m/%d').date()
                    except ValueError:
                        pass

                student.withdrawal_reason = row.get('退塾理由', '') or ''

                # 主所属校舎
                primary_school_name = row.get('主所属校舎', '')
                if primary_school_name:
                    school = school_map.get(primary_school_name)
                    if school:
                        student.primary_school = school

                # 主所属ブランド
                primary_brand_name = row.get('主所属ブランド', '')
                if primary_brand_name:
                    brand = brand_map.get(primary_brand_name)
                    if brand:
                        student.primary_brand = brand

                if not dry_run:
                    student.save()

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                errors.append(f"{row.get('生徒番号', '?')}: {str(e)}")

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

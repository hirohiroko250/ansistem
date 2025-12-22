"""
T2 個人・生徒情報インポートコマンド
CSVファイルから保護者と生徒のデータをインポートする
"""
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction, models
from apps.students.models import Guardian, Student
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'T2 個人・生徒情報CSVをインポート'

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

        guardian_count = 0
        student_count = 0
        guardian_updated = 0
        student_updated = 0
        errors = []

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'総行数: {len(rows)}')

        # まず保護者を作成（保護者ID == 個人IDの行）
        guardian_rows = [r for r in rows if r['保護者ID'] == r['個人ID']]
        self.stdout.write(f'保護者行数: {len(guardian_rows)}')

        for row in guardian_rows:
            try:
                with transaction.atomic():
                    guardian, created = self._import_guardian(row, tenant, dry_run)
                    if created:
                        guardian_count += 1
                    else:
                        guardian_updated += 1
            except Exception as e:
                errors.append(f"保護者 {row['保護者ID']}: {str(e)}")

        # 次に生徒を作成（保護者ID != 個人IDの行）
        student_rows = [r for r in rows if r['保護者ID'] != r['個人ID']]
        self.stdout.write(f'生徒行数: {len(student_rows)}')

        for row in student_rows:
            try:
                with transaction.atomic():
                    student, created = self._import_student(row, tenant, dry_run)
                    if created:
                        student_count += 1
                    else:
                        student_updated += 1
            except Exception as e:
                errors.append(f"生徒 {row['個人ID']}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f'''
インポート完了:
- 保護者: {guardian_count}件 新規, {guardian_updated}件 更新
- 生徒: {student_count}件 新規, {student_updated}件 更新
- エラー: {len(errors)}件
'''))

        if errors[:10]:
            self.stderr.write('エラー詳細（最初の10件）:')
            for err in errors[:10]:
                self.stderr.write(f'  {err}')

    def _parse_date(self, date_str):
        """日付文字列をパース"""
        if not date_str or date_str.strip() == '':
            return None
        try:
            # YYYY/MM/DD 形式
            return datetime.strptime(date_str, '%Y/%m/%d').date()
        except ValueError:
            try:
                # YYYY-MM-DD 形式
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return None

    def _parse_gender(self, gender_str):
        """性別をパース"""
        if not gender_str:
            return ''
        if gender_str in ['男', '男性']:
            return 'male'
        elif gender_str in ['女', '女性']:
            return 'female'
        return 'other'

    def _import_guardian(self, row, tenant, dry_run):
        """保護者をインポート"""
        guardian_id = row['保護者ID']

        # 既存の保護者を検索（old_id または guardian_no で）
        # tenant_ref または tenant_id でテナントをフィルタ
        guardian = Guardian.objects.filter(
            models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
        ).filter(
            models.Q(old_id=guardian_id) | models.Q(guardian_no=guardian_id)
        ).first()

        created = guardian is None
        if created:
            guardian = Guardian(tenant_ref=tenant)

        # フィールド設定
        guardian.old_id = guardian_id
        guardian.guardian_no = guardian_id
        guardian.last_name = row.get('苗字', '') or ''
        guardian.first_name = row.get('お名前', '') or ''
        guardian.last_name_kana = row.get('苗字(ヨミ)', '') or ''
        guardian.first_name_kana = row.get('お名前(ヨミ)', '') or ''
        guardian.last_name_roman = row.get('苗字(ローマ字)', '') or ''
        guardian.first_name_roman = row.get('お名前(ローマ字)', '') or ''
        guardian.birth_date = self._parse_date(row.get('生年月日', ''))
        guardian.email = row.get('メールアドレス', '') or ''
        guardian.phone = row.get('電話1番号', '') or ''
        guardian.postal_code = (row.get('郵便番号', '') or '').replace('-', '')
        guardian.prefecture = row.get('都道府県', '') or ''
        guardian.city = row.get('市区町村', '') or ''
        guardian.address1 = row.get('番地', '') or ''
        guardian.address2 = row.get('建物・部屋番号', '') or ''
        guardian.workplace = row.get('勤務先1', '') or ''
        guardian.workplace2 = row.get('勤務先2', '') or ''

        if not dry_run:
            guardian.save()

        return guardian, created

    def _import_student(self, row, tenant, dry_run):
        """生徒をインポート"""
        student_id = row['個人ID']
        guardian_id = row['保護者ID']

        # 既存の生徒を検索（old_id または student_no で）
        # tenant_ref または tenant_id でテナントをフィルタ
        student = Student.objects.filter(
            models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
        ).filter(
            models.Q(old_id=student_id) | models.Q(student_no=student_id)
        ).first()

        created = student is None
        if created:
            student = Student(tenant_ref=tenant)

        # 保護者を検索
        guardian = Guardian.objects.filter(
            models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
        ).filter(
            models.Q(old_id=guardian_id) | models.Q(guardian_no=guardian_id)
        ).first()

        # フィールド設定
        student.old_id = student_id
        student.student_no = student_id
        student.last_name = row.get('苗字', '') or ''
        student.first_name = row.get('お名前', '') or ''
        student.last_name_kana = row.get('苗字(ヨミ)', '') or ''
        student.first_name_kana = row.get('お名前(ヨミ)', '') or ''
        student.last_name_roman = row.get('苗字(ローマ字)', '') or ''
        student.first_name_roman = row.get('お名前(ローマ字)', '') or ''
        student.nickname = row.get('ニックネーム', '') or ''
        student.birth_date = self._parse_date(row.get('生年月日', ''))
        student.gender = self._parse_gender(row.get('性別', ''))
        student.email = row.get('メールアドレス', '') or ''
        student.phone = row.get('電話1番号', '') or ''
        student.postal_code = (row.get('郵便番号', '') or '').replace('-', '')
        student.prefecture = row.get('都道府県', '') or ''
        student.city = row.get('市区町村', '') or ''
        student.address1 = row.get('番地', '') or ''
        student.address2 = row.get('建物・部屋番号', '') or ''
        student.school_name = row.get('現在の学校名', '') or ''
        student.grade_text = row.get('現在の学年', '') or ''
        student.guardian = guardian

        if not dry_run:
            student.save()

        return student, created

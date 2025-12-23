"""
ユーザー契約情報インポートコマンド
CSVファイルから契約データをインポートする
"""
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction, models
from apps.contracts.models import Contract
from apps.students.models import Guardian, Student
from apps.schools.models import Brand, School
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'ユーザー契約情報CSVをインポート'

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

        new_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        # ブランドマッピングをキャッシュ
        self.brand_cache = {}
        for brand in Brand.objects.filter(
            models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
        ):
            self.brand_cache[brand.brand_name] = brand

        # 保護者・生徒キャッシュ
        self.guardian_cache = {}
        self.student_cache = {}

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f'総行数: {len(rows)}')

        for row in rows:
            try:
                with transaction.atomic():
                    result = self._import_contract(row, tenant, dry_run)
                    if result == 'new':
                        new_count += 1
                    elif result == 'updated':
                        updated_count += 1
                    elif result == 'skipped':
                        skipped_count += 1
            except Exception as e:
                errors.append(f"受講ID {row.get('受講ID', 'unknown')}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f'''
インポート完了:
- 新規: {new_count}件
- 更新: {updated_count}件
- スキップ: {skipped_count}件
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
            return datetime.strptime(date_str, '%Y/%m/%d').date()
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return None

    def _get_guardian(self, guardian_id, tenant):
        """保護者を取得（キャッシュ使用）"""
        if guardian_id not in self.guardian_cache:
            guardian = Guardian.objects.filter(
                models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
            ).filter(
                models.Q(old_id=guardian_id) | models.Q(guardian_no=guardian_id)
            ).first()
            self.guardian_cache[guardian_id] = guardian
        return self.guardian_cache.get(guardian_id)

    def _get_student(self, student_id, tenant):
        """生徒を取得（キャッシュ使用）"""
        if student_id not in self.student_cache:
            student = Student.objects.filter(
                models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
            ).filter(
                models.Q(old_id=student_id) | models.Q(student_no=student_id)
            ).first()
            self.student_cache[student_id] = student
        return self.student_cache.get(student_id)

    def _get_brand(self, brand_name):
        """ブランドを取得（キャッシュ使用）"""
        return self.brand_cache.get(brand_name)

    def _import_contract(self, row, tenant, dry_run):
        """契約をインポート"""
        contract_old_id = row.get('受講ID', '')
        contract_id = row.get('契約ID', '')
        guardian_id = row.get('保護者ID', '')
        student_id = row.get('生徒ID', '')

        if not contract_old_id or not student_id:
            return 'skipped'

        # 生徒・保護者を取得
        student = self._get_student(student_id, tenant)
        guardian = self._get_guardian(guardian_id, tenant)

        if not student:
            return 'skipped'

        # ブランドを取得
        brand_name = row.get('Class用ブランド名', '')
        brand = self._get_brand(brand_name)

        # 既存の契約を検索
        contract = Contract.objects.filter(
            models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
        ).filter(
            models.Q(old_id=contract_old_id) | models.Q(contract_no=contract_old_id)
        ).first()

        created = contract is None
        if created:
            contract = Contract(tenant_ref=tenant)

        # フィールド設定
        contract.old_id = contract_old_id
        contract.contract_no = contract_id or contract_old_id
        contract.student = student
        contract.guardian = guardian

        if brand:
            contract.brand = brand
        else:
            # デフォルトブランドを取得
            default_brand = Brand.objects.filter(
                models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
            ).first()
            if default_brand:
                contract.brand = default_brand

        # 校舎を設定（必須）
        if not contract.school:
            default_school = School.objects.filter(
                models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id),
                brand=contract.brand
            ).first()
            if not default_school:
                default_school = School.objects.filter(
                    models.Q(tenant_ref=tenant) | models.Q(tenant_id=tenant.id)
                ).first()
            if default_school:
                contract.school = default_school

        # brand/schoolがない場合はスキップ
        if not contract.brand or not contract.school:
            return 'skipped'

        # 日付
        start_date = self._parse_date(row.get('開始日', ''))
        end_date = self._parse_date(row.get('終了日', ''))

        if start_date:
            contract.start_date = start_date
            contract.contract_date = start_date
        if end_date:
            contract.end_date = end_date

        # ステータス判定
        withdrawal_date = row.get('全退会日', '')
        brand_withdrawal_date = row.get('ブランド退会日', '')

        if withdrawal_date or brand_withdrawal_date:
            contract.status = Contract.Status.CANCELLED
        else:
            contract.status = Contract.Status.ACTIVE

        if not dry_run:
            contract.save()

        return 'new' if created else 'updated'

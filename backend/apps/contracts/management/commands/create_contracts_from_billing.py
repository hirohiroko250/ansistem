"""
請求確定データ（ConfirmedBilling）から契約を作成するコマンド

Usage:
    python manage.py create_contracts_from_billing --dry-run
    python manage.py create_contracts_from_billing
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ConfirmedBilling
from apps.contracts.models import Contract
from apps.students.models import Student
from apps.schools.models import Brand, School
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = '請求確定データから契約を作成'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # デフォルト校舎
        default_school = School.objects.first()

        # デフォルトブランド
        default_brand = Brand.objects.first()

        # ブランドマッピング
        brand_map = {}
        for b in Brand.objects.all():
            brand_map[b.brand_code] = b
            brand_map[b.brand_name] = b

        # 既存の契約（contract_no + student_id の組み合わせ）を取得
        existing_contracts = set(
            Contract.objects.values_list('contract_no', 'student_id')
        )
        self.stdout.write(f'既存契約: {len(existing_contracts)}件')

        # 全ての請求を取得（items_snapshotがあるもの）
        billings = ConfirmedBilling.objects.exclude(
            items_snapshot=[]
        ).select_related('student', 'guardian')

        self.stdout.write(f'items_snapshotがある請求: {billings.count()}件')

        created_count = 0
        skipped_count = 0
        seen_contracts = set()  # 重複防止

        for billing in billings:
            if not billing.items_snapshot:
                continue

            student = billing.student
            guardian = billing.guardian

            if not student:
                continue

            # items_snapshotからユニークな契約番号を抽出
            contract_nos = set()
            for item in billing.items_snapshot:
                contract_no = item.get('contract_no')
                # nan や空文字をスキップ
                if not contract_no or contract_no == 'nan' or str(contract_no).lower() == 'nan':
                    continue
                # (contract_no, student_id) の組み合わせでチェック
                key = (contract_no, student.id)
                if key not in existing_contracts and key not in seen_contracts:
                    contract_nos.add(contract_no)

            for contract_no in contract_nos:
                # 契約番号からブランドを推測（例: 24AEC_1000007 -> AEC）
                brand = None
                if '_' in contract_no:
                    prefix = contract_no.split('_')[0]
                    if prefix.startswith('24') or prefix.startswith('25'):
                        brand_code = prefix[2:]
                    else:
                        brand_code = prefix
                    brand = brand_map.get(brand_code)

                # items_snapshotから該当契約の情報を取得
                contract_items = [i for i in billing.items_snapshot if i.get('contract_no') == contract_no]

                # ブランド名からも取得を試みる
                if not brand and contract_items:
                    brand_name = contract_items[0].get('brand_name')
                    if brand_name:
                        brand = brand_map.get(brand_name)

                # ブランドが見つからない場合はデフォルトを使用
                if not brand:
                    brand = default_brand

                # 校舎を取得
                school = student.primary_school or default_school

                if dry_run:
                    self.stdout.write(
                        f'  [ドライラン] {student.full_name}: {contract_no} ({brand.brand_name if brand else "?"})'
                    )
                else:
                    with transaction.atomic():
                        Contract.objects.create(
                            tenant_id=tenant.id,
                            tenant_ref=tenant,
                            contract_no=contract_no,
                            old_id=contract_no,
                            student=student,
                            guardian=guardian,
                            school=school,
                            brand=brand,
                            status='active',
                            contract_date=billing.created_at.date() if billing.created_at else None,
                            start_date=billing.created_at.date() if billing.created_at else None,
                        )

                seen_contracts.add((contract_no, student.id))
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
契約作成: {created_count}件
'''))

"""
ContractにCourseを紐付けるマネジメントコマンド

contract_noの形式: 24SOR_1000038_205989
→ course_code: 24SOR_1000038 でマッチング

Usage:
    # ドライラン
    python manage.py link_contracts_to_courses --dry-run

    # 実行
    python manage.py link_contracts_to_courses

    # Courseがない場合に新規作成
    python manage.py link_contracts_to_courses --create-missing
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contracts.models import Contract, Course
from apps.schools.models import Brand
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'ContractにCourseを紐付け'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--create-missing',
            action='store_true',
            help='Courseがない場合に新規作成'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        create_missing = options.get('create_missing', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # Course.course_codeマップ作成
        course_map = {}
        for c in Course.objects.all():
            course_map[c.course_code] = c
        self.stdout.write(f'Course: {len(course_map)}件')

        # Brand.brand_codeマップ作成
        brand_map = {}
        for b in Brand.objects.all():
            brand_map[b.brand_code] = b
        default_brand = Brand.objects.filter(brand_code='DEFAULT').first() or Brand.objects.first()

        # 統計
        linked_count = 0
        created_count = 0
        skipped_already = 0
        skipped_no_course = 0

        contracts = Contract.objects.filter(course__isnull=True)
        total = contracts.count()
        self.stdout.write(f'courseなしContract: {total}件')

        for contract in contracts:
            # contract_noからcourse_codeを抽出
            parts = contract.contract_no.rsplit('_', 1)
            if len(parts) != 2:
                skipped_no_course += 1
                continue

            course_code = parts[0]
            course = course_map.get(course_code)

            if course:
                # Courseが存在する場合
                if dry_run:
                    self.stdout.write(
                        f'  [ドライラン] {contract.contract_no} → {course.course_name[:50]}'
                    )
                else:
                    contract.course = course
                    contract.save(update_fields=['course'])
                linked_count += 1
            elif create_missing:
                # Courseを新規作成
                # ブランドコード抽出: 24SOR_1000038 → SOR
                brand_code = None
                if '_' in course_code:
                    prefix = course_code.split('_')[0]
                    if prefix.startswith('24') and len(prefix) > 2:
                        brand_code = prefix[2:]
                    else:
                        brand_code = prefix
                brand = brand_map.get(brand_code) or default_brand

                # 契約名をnotes/CSVから取得（ここでは簡易的にcontract.notesを使用）
                course_name = f'{brand.brand_name} {contract.notes}' if contract.notes else f'{brand.brand_name} コース'

                if dry_run:
                    self.stdout.write(
                        f'  [ドライラン] 新規Course: {course_code} - {course_name[:50]}'
                    )
                else:
                    with transaction.atomic():
                        new_course = Course.objects.create(
                            tenant_id=tenant.id,
                            tenant_ref=tenant,
                            course_code=course_code,
                            course_name=course_name,
                            brand=brand,
                            is_active=True,
                        )
                        contract.course = new_course
                        contract.save(update_fields=['course'])
                        course_map[course_code] = new_course
                created_count += 1
                linked_count += 1
            else:
                skipped_no_course += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
紐付け: {linked_count}件
新規Course作成: {created_count}件
スキップ（Courseなし）: {skipped_no_course}件
'''))

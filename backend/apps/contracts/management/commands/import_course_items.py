"""
T3 CSVからコース商品構成・パック商品構成をインポートするコマンド

契約ID (24AEC_1000007) に対して、請求ID (24AEC_1000007_1, _2, _3...) が構成商品
"""
import csv
from collections import defaultdict
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import Course, Pack, Product, CourseItem, PackItem


class Command(BaseCommand):
    help = 'T3 CSVからコース商品構成・パック商品構成をインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='/app/data/T3_契約情報_202512021655_UTF8.csv',
            help='T3 CSVファイルパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存しない'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options['dry_run']

        self.stdout.write(f'CSV: {csv_path}')
        self.stdout.write(f'Dry Run: {dry_run}')

        # 既存のtenant_idを取得
        existing_course = Course.objects.first()
        if existing_course:
            tenant_id = str(existing_course.tenant_id)
            self.stdout.write(f'tenant_id: {tenant_id}')
        else:
            self.stdout.write(self.style.ERROR('既存のコースがありません'))
            return

        # コース・パックをコードでマッピング
        courses_by_code = {}
        for course in Course.objects.filter(tenant_id=tenant_id):
            courses_by_code[course.course_code] = course
        self.stdout.write(f'コース数: {len(courses_by_code)}')

        packs_by_code = {}
        for pack in Pack.objects.filter(tenant_id=tenant_id):
            packs_by_code[pack.pack_code] = pack
        self.stdout.write(f'パック数: {len(packs_by_code)}')

        # 商品をコードでマッピング
        products_by_code = {}
        for product in Product.objects.filter(tenant_id=tenant_id):
            products_by_code[product.product_code] = product
        self.stdout.write(f'商品数: {len(products_by_code)}')

        # CSVを読み込み、契約IDごとに商品をグループ化
        contract_items = defaultdict(list)

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                contract_id = row.get('契約ID', '').strip()
                billing_id = row.get('請求ID', '').strip()
                contract_type = row.get('契約種類', '1')

                if not contract_id or not billing_id:
                    continue

                contract_items[contract_id].append({
                    'billing_id': billing_id,
                    'contract_type': contract_type,
                    'item_type': row.get('請求カテゴリ名', ''),
                    'base_price': row.get('単価', '0'),
                })

        self.stdout.write(f'契約数: {len(contract_items)}')

        stats = {
            'course_items': 0,
            'pack_items': 0,
            'skipped': 0,
        }

        with transaction.atomic():
            for contract_id, items in contract_items.items():
                if not items:
                    continue

                contract_type = items[0]['contract_type']

                # コースコード・パックコードを生成（インポート時と同じロジック）
                course_code = contract_id.replace('24', 'C').replace('_', '')[:20]
                pack_code = contract_id.replace('24', 'PK').replace('_', '')[:20]

                # コースの場合（契約種類=1）
                if contract_type == '1' and course_code in courses_by_code:
                    course = courses_by_code[course_code]

                    for idx, item in enumerate(items):
                        # 商品コードを生成
                        product_code = item['billing_id'].replace('24', 'P').replace('_', '')[:20]
                        product = products_by_code.get(product_code)

                        if not product:
                            stats['skipped'] += 1
                            continue

                        if not dry_run:
                            course_item, created = CourseItem.objects.update_or_create(
                                tenant_id=tenant_id,
                                course=course,
                                product=product,
                                defaults={
                                    'quantity': 1,
                                    'sort_order': idx,
                                    'is_active': True,
                                }
                            )
                            if created:
                                stats['course_items'] += 1
                        else:
                            if stats['course_items'] < 20:
                                self.stdout.write(
                                    f'  [DRY] CourseItem: {course.course_name[:20]} <- {product.product_name[:30]}'
                                )
                            stats['course_items'] += 1

                # パックの場合（契約種類=3）
                elif contract_type == '3' and pack_code in packs_by_code:
                    pack = packs_by_code[pack_code]

                    for idx, item in enumerate(items):
                        product_code = item['billing_id'].replace('24', 'P').replace('_', '')[:20]
                        product = products_by_code.get(product_code)

                        if not product:
                            stats['skipped'] += 1
                            continue

                        if not dry_run:
                            pack_item, created = PackItem.objects.update_or_create(
                                tenant_id=tenant_id,
                                pack=pack,
                                product=product,
                                defaults={
                                    'quantity': 1,
                                    'sort_order': idx,
                                    'is_active': True,
                                }
                            )
                            if created:
                                stats['pack_items'] += 1
                        else:
                            if stats['pack_items'] < 20:
                                self.stdout.write(
                                    f'  [DRY] PackItem: {pack.pack_name[:20]} <- {product.product_name[:30]}'
                                )
                            stats['pack_items'] += 1

            if dry_run:
                raise Exception('Dry run - rolling back')

        self.stdout.write(self.style.SUCCESS(
            f"\n=== 完了 ===\n"
            f"CourseItem: {stats['course_items']}件\n"
            f"PackItem: {stats['pack_items']}件\n"
            f"Skipped: {stats['skipped']}件\n"
        ))

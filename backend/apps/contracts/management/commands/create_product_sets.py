"""
既存のProductデータからProductSetを自動作成するコマンド

ブランドごとに以下のセットを作成:
1. 入会セット（入会金 + バッグ）
2. 月額基本セット（授業料 + 月会費 + 設備費）
3. 教材セット（教材費）
4. 入会時フルセット（入会金 + バッグ + 初月授業料 + 初月月会費 + 初月設備費 + 教材費）
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import Product, ProductSet, ProductSetItem
from apps.schools.models import Brand
from collections import defaultdict


class Command(BaseCommand):
    help = '既存Productから商品セットを自動作成'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-id',
            type=str,
            default='3bec66b2-36ff-4206-9220-f2d7da1515ac',
            help='テナントID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存しない'
        )

    def handle(self, *args, **options):
        tenant_id = options['tenant_id']
        dry_run = options['dry_run']

        self.stdout.write(f'テナントID: {tenant_id}')
        self.stdout.write(f'Dry Run: {dry_run}')

        # ブランドごとに処理
        brands = Brand.objects.filter(tenant_id=tenant_id, is_active=True)

        sets_created = 0
        items_created = 0

        for brand in brands:
            products = Product.objects.filter(
                tenant_id=tenant_id,
                brand=brand,
                is_active=True
            )

            if products.count() == 0:
                continue

            self.stdout.write(f'\n=== {brand.brand_name} ({products.count()}件) ===')

            # 商品をitem_typeで分類
            by_type = defaultdict(list)
            for p in products:
                by_type[p.item_type].append(p)

            # 1. 入会セット作成
            enrollment_products = by_type.get('enrollment', [])
            bag_products = [p for p in by_type.get('other', []) if 'バッグ' in p.product_name]

            if enrollment_products:
                set_code = f'SET_{brand.brand_code}_ENROLL'
                set_name = f'{brand.brand_name}【入会セット】'

                if dry_run:
                    self.stdout.write(f'  [DRY] {set_name}')
                    self.stdout.write(f'    入会金: {len(enrollment_products)}件')
                    self.stdout.write(f'    バッグ: {len(bag_products)}件')
                else:
                    product_set, created = ProductSet.objects.update_or_create(
                        tenant_id=tenant_id,
                        set_code=set_code,
                        defaults={
                            'set_name': set_name,
                            'brand': brand,
                            'description': '入会時に必要な商品セット（入会金＋バッグ）',
                            'is_active': True,
                        }
                    )
                    if created:
                        sets_created += 1
                        self.stdout.write(self.style.SUCCESS(f'  作成: {set_name}'))

                    # 入会金を追加（最初の1件のみ）
                    if enrollment_products:
                        item, item_created = ProductSetItem.objects.update_or_create(
                            tenant_id=tenant_id,
                            product_set=product_set,
                            product=enrollment_products[0],
                            defaults={'quantity': 1, 'is_active': True}
                        )
                        if item_created:
                            items_created += 1

                    # バッグを追加（最初の1件のみ）
                    if bag_products:
                        item, item_created = ProductSetItem.objects.update_or_create(
                            tenant_id=tenant_id,
                            product_set=product_set,
                            product=bag_products[0],
                            defaults={'quantity': 1, 'is_active': True}
                        )
                        if item_created:
                            items_created += 1

            # 2. 月額基本セット作成
            tuition_products = by_type.get('tuition', [])
            monthly_fee_products = by_type.get('monthly_fee', [])
            facility_products = by_type.get('facility', [])

            if tuition_products or monthly_fee_products or facility_products:
                set_code = f'SET_{brand.brand_code}_MONTHLY'
                set_name = f'{brand.brand_name}【月額基本セット】'

                if dry_run:
                    self.stdout.write(f'  [DRY] {set_name}')
                    self.stdout.write(f'    授業料: {len(tuition_products)}件')
                    self.stdout.write(f'    月会費: {len(monthly_fee_products)}件')
                    self.stdout.write(f'    設備費: {len(facility_products)}件')
                else:
                    product_set, created = ProductSet.objects.update_or_create(
                        tenant_id=tenant_id,
                        set_code=set_code,
                        defaults={
                            'set_name': set_name,
                            'brand': brand,
                            'description': '毎月発生する基本料金セット（授業料＋月会費＋設備費）',
                            'is_active': True,
                        }
                    )
                    if created:
                        sets_created += 1
                        self.stdout.write(self.style.SUCCESS(f'  作成: {set_name}'))

                    # 授業料を追加（複数の授業料コースがある場合は代表的なものを1件）
                    if tuition_products:
                        # 「週1」か「レギュラー」を含むものを優先
                        main_tuition = None
                        for p in tuition_products:
                            if '週1' in p.product_name or 'レギュラー' in p.product_name:
                                main_tuition = p
                                break
                        if not main_tuition:
                            main_tuition = tuition_products[0]

                        item, item_created = ProductSetItem.objects.update_or_create(
                            tenant_id=tenant_id,
                            product_set=product_set,
                            product=main_tuition,
                            defaults={'quantity': 1, 'is_active': True}
                        )
                        if item_created:
                            items_created += 1

                    # 月会費を追加
                    if monthly_fee_products:
                        # 「入会時」を含まないものを優先
                        main_monthly = None
                        for p in monthly_fee_products:
                            if '入会時' not in p.product_name:
                                main_monthly = p
                                break
                        if not main_monthly:
                            main_monthly = monthly_fee_products[0]

                        item, item_created = ProductSetItem.objects.update_or_create(
                            tenant_id=tenant_id,
                            product_set=product_set,
                            product=main_monthly,
                            defaults={'quantity': 1, 'is_active': True}
                        )
                        if item_created:
                            items_created += 1

                    # 設備費を追加
                    if facility_products:
                        # 「入会時」を含まないものを優先
                        main_facility = None
                        for p in facility_products:
                            if '入会時' not in p.product_name:
                                main_facility = p
                                break
                        if not main_facility:
                            main_facility = facility_products[0]

                        item, item_created = ProductSetItem.objects.update_or_create(
                            tenant_id=tenant_id,
                            product_set=product_set,
                            product=main_facility,
                            defaults={'quantity': 1, 'is_active': True}
                        )
                        if item_created:
                            items_created += 1

            # 3. 教材セット作成
            textbook_products = by_type.get('textbook', [])

            if textbook_products:
                set_code = f'SET_{brand.brand_code}_TEXTBOOK'
                set_name = f'{brand.brand_name}【教材セット】'

                if dry_run:
                    self.stdout.write(f'  [DRY] {set_name}')
                    self.stdout.write(f'    教材費: {len(textbook_products)}件')
                else:
                    product_set, created = ProductSet.objects.update_or_create(
                        tenant_id=tenant_id,
                        set_code=set_code,
                        defaults={
                            'set_name': set_name,
                            'brand': brand,
                            'description': '教材費セット',
                            'is_active': True,
                        }
                    )
                    if created:
                        sets_created += 1
                        self.stdout.write(self.style.SUCCESS(f'  作成: {set_name}'))

                    # 教材を追加（代表的なもの1件）
                    main_textbook = None
                    for p in textbook_products:
                        if '入会時' not in p.product_name:
                            main_textbook = p
                            break
                    if not main_textbook:
                        main_textbook = textbook_products[0]

                    item, item_created = ProductSetItem.objects.update_or_create(
                        tenant_id=tenant_id,
                        product_set=product_set,
                        product=main_textbook,
                        defaults={'quantity': 1, 'is_active': True}
                    )
                    if item_created:
                        items_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n完了: ProductSet {sets_created}件, ProductSetItem {items_created}件作成'
        ))

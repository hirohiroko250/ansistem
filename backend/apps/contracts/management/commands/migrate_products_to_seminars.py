"""
講習会関連のProductをSeminarテーブルに移行するコマンド

Usage:
    python manage.py migrate_products_to_seminars --dry-run
    python manage.py migrate_products_to_seminars
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contracts.models import Product, Seminar, Course, CourseSeminar
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = '講習会関連のProductをSeminarテーブルに移行'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='既存のSeminarデータを削除してから移行'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clear = options['clear']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # 既存データ削除
        if clear and not dry_run:
            seminar_count = Seminar.objects.all().delete()[0]
            course_seminar_count = CourseSeminar.objects.all().delete()[0]
            self.stdout.write(f'既存データ削除: Seminar {seminar_count}件, CourseSeminar {course_seminar_count}件')

        # 講習会関連のitem_type
        seminar_types = ['seminar', 'seminar_spring', 'seminar_summer', 'seminar_winter']

        # 講習会商品を取得
        products = Product.objects.filter(item_type__in=seminar_types)
        self.stdout.write(f'講習会商品: {products.count()}件')

        # 必須講習会商品も取得（item_type=otherだが商品名に「必須講習会」を含む）
        required_products = Product.objects.filter(product_name__contains='必須講習会').exclude(item_type__in=seminar_types)
        self.stdout.write(f'必須講習会商品（other）: {required_products.count()}件')

        # 全講習会商品
        all_seminar_products = products.union(required_products)

        created_count = 0
        updated_count = 0
        course_link_count = 0

        # item_type から seminar_type へのマッピング
        type_map = {
            'seminar': 'other',
            'seminar_spring': 'spring',
            'seminar_summer': 'summer',
            'seminar_winter': 'winter',
        }

        for product in all_seminar_products:
            # seminar_type を決定
            if product.item_type in type_map:
                seminar_type = type_map[product.item_type]
            elif '春期' in product.product_name:
                seminar_type = 'spring'
            elif '夏期' in product.product_name:
                seminar_type = 'summer'
            elif '冬期' in product.product_name:
                seminar_type = 'winter'
            else:
                seminar_type = 'other'

            # 必須講習会かどうか
            is_required = '必須講習会' in product.product_name

            # 年度を推測（商品コードから）
            year = 2024  # デフォルト
            if product.product_code.startswith('24'):
                year = 2024
            elif product.product_code.startswith('25'):
                year = 2025

            if dry_run:
                self.stdout.write(
                    f'  [ドライラン] {product.product_code}: {product.product_name[:40]} -> {seminar_type}, 必須={is_required}'
                )
            else:
                with transaction.atomic():
                    seminar, created = Seminar.objects.update_or_create(
                        tenant_id=tenant.id,
                        seminar_code=product.product_code,
                        defaults={
                            'tenant_ref': tenant,
                            'seminar_name': product.product_name,
                            'seminar_name_short': product.product_name_short or '',
                            'old_id': product.product_code,
                            'seminar_type': seminar_type,
                            'is_required': is_required,
                            'brand': product.brand,
                            'grade': product.grade,
                            'year': year,
                            'base_price': product.base_price or Decimal('0'),
                            'per_ticket_price': product.per_ticket_price or Decimal('0'),
                            'tax_type': product.tax_type or '1',
                            # 月別価格
                            'billing_price_jan': product.billing_price_jan or Decimal('0'),
                            'billing_price_feb': product.billing_price_feb or Decimal('0'),
                            'billing_price_mar': product.billing_price_mar or Decimal('0'),
                            'billing_price_apr': product.billing_price_apr or Decimal('0'),
                            'billing_price_may': product.billing_price_may or Decimal('0'),
                            'billing_price_jun': product.billing_price_jun or Decimal('0'),
                            'billing_price_jul': product.billing_price_jul or Decimal('0'),
                            'billing_price_aug': product.billing_price_aug or Decimal('0'),
                            'billing_price_sep': product.billing_price_sep or Decimal('0'),
                            'billing_price_oct': product.billing_price_oct or Decimal('0'),
                            'billing_price_nov': product.billing_price_nov or Decimal('0'),
                            'billing_price_dec': product.billing_price_dec or Decimal('0'),
                            # 入会者用価格
                            'enrollment_price_jan': product.enrollment_price_jan or Decimal('0'),
                            'enrollment_price_feb': product.enrollment_price_feb or Decimal('0'),
                            'enrollment_price_mar': product.enrollment_price_mar or Decimal('0'),
                            'enrollment_price_apr': product.enrollment_price_apr or Decimal('0'),
                            'enrollment_price_may': product.enrollment_price_may or Decimal('0'),
                            'enrollment_price_jun': product.enrollment_price_jun or Decimal('0'),
                            'enrollment_price_jul': product.enrollment_price_jul or Decimal('0'),
                            'enrollment_price_aug': product.enrollment_price_aug or Decimal('0'),
                            'enrollment_price_sep': product.enrollment_price_sep or Decimal('0'),
                            'enrollment_price_oct': product.enrollment_price_oct or Decimal('0'),
                            'enrollment_price_nov': product.enrollment_price_nov or Decimal('0'),
                            'enrollment_price_dec': product.enrollment_price_dec or Decimal('0'),
                            # マイル・割引
                            'mile': product.mile or 0,
                            'discount_max': product.discount_max or 0,
                            'is_active': product.is_active,
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                    # 必須講習会の場合、コースとの紐づけを試みる
                    if is_required and product.brand:
                        # 同じブランドのコースを探す
                        courses = Course.objects.filter(brand=product.brand)
                        for course in courses:
                            # コース名の一部が講習会名に含まれているか確認
                            if course.course_name and course.course_name[:10] in product.product_name:
                                CourseSeminar.objects.get_or_create(
                                    tenant_id=tenant.id,
                                    course=course,
                                    seminar=seminar,
                                    defaults={
                                        'tenant_ref': tenant,
                                        'is_required': True,
                                    }
                                )
                                course_link_count += 1
                                break

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
Seminar新規作成: {created_count}件
Seminar更新: {updated_count}件
CourseSeminar紐づけ: {course_link_count}件
'''))

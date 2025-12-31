"""
T3 CSVまたはXLSXからCourse, Product, Packにデータを投入するコマンド
"""
import csv
import uuid
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import Course, Product, Pack
from apps.schools.models import Brand, School, Grade


class Command(BaseCommand):
    help = 'T3 CSVまたはXLSXからCourse, Product, Packに実データを投入'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            required=False,
            help='T3 CSVファイルパス'
        )
        parser.add_argument(
            '--xlsx',
            type=str,
            required=False,
            help='T3 XLSXファイルパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存しない'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='既存のProductを削除してから投入'
        )

    def handle(self, *args, **options):
        csv_path = options.get('csv')
        xlsx_path = options.get('xlsx')
        dry_run = options['dry_run']
        clear = options['clear']

        if not csv_path and not xlsx_path:
            self.stderr.write(self.style.ERROR('--csv または --xlsx を指定してください'))
            return

        file_path = xlsx_path or csv_path
        self.stdout.write(f'ファイル: {file_path}')
        self.stdout.write(f'Dry Run: {dry_run}')
        self.stdout.write(f'Clear: {clear}')

        # 既存のtenant_idを取得
        existing_course = Course.objects.first()
        if existing_course:
            tenant_id = existing_course.tenant_id
            self.stdout.write(f'既存のtenant_idを使用: {tenant_id}')
        else:
            self.stdout.write(self.style.ERROR('既存のコースがありません。'))
            return

        # 既存データ削除
        if clear and not dry_run:
            deleted_count = Product.objects.count()
            Product.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'既存のProduct {deleted_count}件を削除しました'))

        # DBから既存ブランドをbrand_codeでマッピング
        brands_by_code = self.get_brands_by_code(tenant_id)
        brands_by_name = self.get_brands_by_name(tenant_id)

        # 対象学年マスタを作成/取得
        grades = self.create_grades(tenant_id, dry_run)

        # ファイルを読み込み
        if xlsx_path:
            import pandas as pd
            df = pd.read_excel(xlsx_path)
            # NaN を空文字列に変換
            df = df.fillna('')
            rows = df.to_dict('records')
        else:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

        self.stdout.write(f'総行数: {len(rows)}')

        courses_created = 0
        products_created = 0
        products_updated = 0

        # 重複チェック用
        seen_courses = set()
        seen_products = set()

        for row in rows:
            # 有効・無効チェック
            is_active = row.get('有効・無効', '1') == '1'

            # コースを作成（授業料レコードのみ）
            if row.get('請求カテゴリ名') == '授業料':
                course_name = row.get('契約名', '')
                grade_name = row.get('対象学年', '')
                price = row.get('保護者表示用金額', '0') or '0'
                brand_code = row.get('契約ブランド記号', '')

                course_key = f"{course_name}_{grade_name}_{brand_code}"

                if course_key not in seen_courses and course_name:
                    seen_courses.add(course_key)

                    if not dry_run:
                        brand = brands_by_code.get(brand_code)
                        grade = grades.get(grade_name)

                        try:
                            price_decimal = Decimal(str(price).replace(',', ''))
                        except (InvalidOperation, ValueError):
                            price_decimal = Decimal('0')

                        course, created = Course.objects.update_or_create(
                            tenant_id=tenant_id,
                            course_code=f"C{len(seen_courses):05d}",
                            defaults={
                                'course_name': course_name[:100] if course_name else '',
                                'brand': brand,
                                'grade': grade,
                                'course_price': price_decimal,
                                'is_active': is_active,
                            }
                        )
                        if created:
                            courses_created += 1

            # プロダクト（商品）を作成
            product_name = row.get('明細表記', '') or row.get('契約名', '')
            product_code = row.get('請求ID', '') or row.get('契約ID', '')
            item_type_name = row.get('請求カテゴリ名', '')
            unit_price = row.get('単価', '0') or '0'  # 単価
            display_price = row.get('保護者表示用金額', '0') or '0'  # 保護者表示用金額
            brand_code = row.get('契約ブランド記号', '')
            brand_name = row.get('契約ブランド名', '')
            grade_name = row.get('対象学年', '')
            tax_type = row.get('税区分', '1')
            contract_name = row.get('契約名', '')
            mile = row.get('マイル', '0') or '0'
            discount_max = row.get('割引MAX(%)', '0') or '0'

            if product_code and product_code not in seen_products:
                seen_products.add(product_code)

                # item_type変換（請求カテゴリ区分も参照）
                category_code = row.get('請求カテゴリ区分', '')
                item_type = self.get_item_type(item_type_name, category_code)

                if not dry_run:
                    brand = brands_by_code.get(brand_code) or brands_by_name.get(brand_name)
                    grade = grades.get(grade_name)

                    # 金額パース用ヘルパー
                    def parse_price(val):
                        try:
                            return Decimal(str(val).replace(',', ''))
                        except (InvalidOperation, ValueError):
                            return Decimal('0')

                    product, created = Product.objects.update_or_create(
                        tenant_id=tenant_id,
                        product_code=product_code,
                        defaults={
                            'product_name': product_name[:100] if product_name else product_code,
                            'product_name_short': contract_name[:50] if contract_name else '',
                            'item_type': item_type,
                            'brand': brand,
                            'grade': grade,
                            'base_price': parse_price(display_price),  # 保護者表示用金額
                            'per_ticket_price': parse_price(unit_price),  # 単価
                            'mile': int(float(mile)) if mile else 0,
                            'discount_max': int(float(discount_max)) if discount_max else 0,
                            'tax_type': str(tax_type) if str(tax_type) in ['1', '2', '3'] else '1',
                            'is_active': is_active,
                            # 各月の請求金額
                            'billing_price_jan': parse_price(row.get('1月', '0')),
                            'billing_price_feb': parse_price(row.get('2月', '0')),
                            'billing_price_mar': parse_price(row.get('3月', '0')),
                            'billing_price_apr': parse_price(row.get('4月', '0')),
                            'billing_price_may': parse_price(row.get('5月', '0')),
                            'billing_price_jun': parse_price(row.get('6月', '0')),
                            'billing_price_jul': parse_price(row.get('7月', '0')),
                            'billing_price_aug': parse_price(row.get('8月', '0')),
                            'billing_price_sep': parse_price(row.get('9月', '0')),
                            'billing_price_oct': parse_price(row.get('10月', '0')),
                            'billing_price_nov': parse_price(row.get('11月', '0')),
                            'billing_price_dec': parse_price(row.get('12月', '0')),
                            # 入会者用金額
                            'enrollment_price_jan': parse_price(row.get('1月入会者', '0')),
                            'enrollment_price_feb': parse_price(row.get('2月入会者', '0')),
                            'enrollment_price_mar': parse_price(row.get('3月入会者', '0')),
                            'enrollment_price_apr': parse_price(row.get('4月入会者', '0')),
                            'enrollment_price_may': parse_price(row.get('5月入会者', '0')),
                            'enrollment_price_jun': parse_price(row.get('6月入会者', '0')),
                            'enrollment_price_jul': parse_price(row.get('7月入会者', '0')),
                            'enrollment_price_aug': parse_price(row.get('8月入会者', '0')),
                            'enrollment_price_sep': parse_price(row.get('9月入会者', '0')),
                            'enrollment_price_oct': parse_price(row.get('10月入会者', '0')),
                            'enrollment_price_nov': parse_price(row.get('11月入会者', '0')),
                            'enrollment_price_dec': parse_price(row.get('12月入会者', '0')),
                        }
                    )
                    if created:
                        products_created += 1
                    else:
                        products_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'完了: Course {courses_created}件, Product 新規{products_created}件 更新{products_updated}件'
        ))

    def get_brands_by_code(self, tenant_id):
        """DBから既存のブランドをbrand_codeでマッピングして取得"""
        brands = {}
        for brand in Brand.objects.filter(is_active=True):
            if brand.brand_code:
                brands[brand.brand_code] = brand
        self.stdout.write(f'取得したブランド数(コード): {len(brands)}')
        return brands

    def get_brands_by_name(self, tenant_id):
        """DBから既存のブランドをbrand_nameでマッピングして取得"""
        brands = {}
        for brand in Brand.objects.filter(is_active=True):
            if brand.brand_name:
                brands[brand.brand_name] = brand
        self.stdout.write(f'取得したブランド数(名前): {len(brands)}')
        return brands

    def get_item_type(self, item_type_name, category_code):
        """請求カテゴリ名と区分コードからitem_typeを決定"""
        # 請求カテゴリ区分マッピング
        category_map = {
            '1': 'tuition',  # 授業料
            '2': 'monthly_fee',  # 月会費
            '3': 'facility',  # 設備費
            '4': 'textbook',  # 教材費
            '5': 'expense',  # 諸経費
            '6': 'enrollment',  # 入会金
            '10': 'management',  # 総合指導管理費
            '85': 'enrollment_tuition',  # 入会時授業料
            '86': 'enrollment_monthly_fee',  # 入会時月会費
            '87': 'enrollment_facility',  # 入会時設備費
            '88': 'enrollment_textbook',  # 入会時教材費
            '89': 'enrollment_expense',  # 入会時諸経費
            '90': 'enrollment_management',  # 入会時総合指導管理費
        }

        if category_code and category_code in category_map:
            return category_map[category_code]

        # 請求カテゴリ名マッピング
        item_type_map = {
            '授業料': 'tuition',
            '月会費': 'monthly_fee',
            '設備費': 'facility',
            '教材費': 'textbook',
            '諸経費': 'expense',
            '入会金': 'enrollment',
            '総合指導管理費': 'management',
            '入会時授業料': 'enrollment_tuition',
            '入会時授業料A': 'enrollment_tuition',
            '入会時授業料B': 'enrollment_tuition',
            '入会時月会費': 'enrollment_monthly_fee',
            '入会時設備費': 'enrollment_facility',
            '入会時教材費': 'enrollment_textbook',
            '入会時諸経費': 'enrollment_expense',
            '入会時総合指導管理費': 'enrollment_management',
            '講習会': 'seminar',
            '春期講習会': 'seminar_spring',
            '夏期講習会': 'seminar_summer',
            '冬期講習会': 'seminar_winter',
            'テスト対策費': 'test_prep',
            '模試代': 'mock_exam',
            '検定料': 'certification_fee_1',
            '追加授業料': 'extra_tuition',
            'バッグ': 'bag',
            'そろばん本体代': 'abacus',
            'おやつ': 'snack',
            'お弁当': 'lunch',
            '送迎費': 'transportation',
            '預り料': 'custody',
        }

        return item_type_map.get(item_type_name, 'other')

    def create_grades(self, tenant_id, dry_run):
        """対象学年マスタを作成"""
        grade_data = [
            ('G001', '年少~年長', 'preschool'),
            ('G002', '年長~小4', 'elementary'),
            ('G003', '小3~中1', 'elementary'),
            ('G004', '小3~高1', 'elementary'),
            ('G005', '小4~高3', 'elementary'),
            ('G006', '小6~高3', 'junior_high'),
            ('G007', '小1', 'elementary'),
            ('G008', '小2', 'elementary'),
            ('G009', '小3', 'elementary'),
            ('G010', '小4', 'elementary'),
            ('G011', '小5', 'elementary'),
            ('G012', '小6', 'elementary'),
            ('G013', '中1', 'junior_high'),
            ('G014', '中2', 'junior_high'),
            ('G015', '中3', 'junior_high'),
            ('G016', '高1', 'high_school'),
            ('G017', '高2', 'high_school'),
            ('G018', '高3', 'high_school'),
            ('G019', '年中', 'preschool'),
            ('G020', '年長', 'preschool'),
        ]

        grades = {}
        for code, name, category in grade_data:
            if not dry_run:
                grade, _ = Grade.objects.update_or_create(
                    tenant_id=tenant_id,
                    grade_code=code,
                    defaults={
                        'grade_name': name,
                        'category': category,
                        'is_active': True,
                    }
                )
                grades[name] = grade
            else:
                grades[name] = None

        # 既存のGradeも取得して追加
        for grade in Grade.objects.all():
            if grade.grade_name and grade.grade_name not in grades:
                grades[grade.grade_name] = grade

        return grades

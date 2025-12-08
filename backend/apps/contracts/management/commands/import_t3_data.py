"""
T3 CSVからCourse, Product, Packにデータを投入するコマンド
"""
import csv
import uuid
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import Course, Product, Pack
from apps.schools.models import Brand, School, Grade


class Command(BaseCommand):
    help = 'T3 CSVからCourse, Product, Packに実データを投入'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/T3_契約情報_202511272049_UTF8.csv',
            help='T3 CSVファイルパス'
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            default='100000',
            help='テナントID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存しない'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options['dry_run']

        self.stdout.write(f'CSVファイル: {csv_path}')
        self.stdout.write(f'Dry Run: {dry_run}')

        # 既存のtenant_idを取得
        existing_course = Course.objects.first()
        if existing_course:
            tenant_id = existing_course.tenant_id
            self.stdout.write(f'既存のtenant_idを使用: {tenant_id}')
        else:
            self.stdout.write(self.style.ERROR('既存のコースがありません。'))
            return

        # DBから既存ブランドをbrand_codeでマッピング
        brands_by_code = self.get_brands_by_code(tenant_id)

        # 対象学年マスタを作成/取得
        grades = self.create_grades(tenant_id, dry_run)

        # CSVを読み込み、コースとプロダクトを作成
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            courses_created = 0
            products_created = 0

            # 重複チェック用
            seen_courses = set()
            seen_products = set()

            for row in reader:
                # コースを作成（授業料レコードのみ）
                if row.get('請求カテゴリ名') == '授業料':
                    course_name = row.get('契約名', '')
                    grade_name = row.get('対象学年', '')
                    price = row.get('保護者表示用金額', '0')
                    brand_code = row.get('契約ブランド記号', '')

                    course_key = f"{course_name}_{grade_name}_{brand_code}"

                    if course_key not in seen_courses and course_name:
                        seen_courses.add(course_key)

                        if not dry_run:
                            brand = brands_by_code.get(brand_code)
                            grade = grades.get(grade_name)

                            course, created = Course.objects.update_or_create(
                                tenant_id=tenant_id,
                                course_code=f"C{len(seen_courses):05d}",
                                defaults={
                                    'course_name': course_name,
                                    'brand': brand,
                                    'grade': grade,
                                    'course_price': Decimal(price) if price else Decimal('0'),
                                    'is_active': True,
                                }
                            )
                            if created:
                                courses_created += 1
                        else:
                            self.stdout.write(f'[DRY] Course: {course_name} | 学年: {grade_name} | 授業料: {price}円')
                            courses_created += 1

                # プロダクト（商品）を作成
                product_name = row.get('明細表記', '') or row.get('契約名', '')
                product_code = row.get('契約ID', '')
                item_type_name = row.get('請求カテゴリ名', '')
                base_price = row.get('単価', '0')
                brand_code = row.get('契約ブランド記号', '')
                grade_name = row.get('対象学年', '')

                if product_code and product_code not in seen_products:
                    seen_products.add(product_code)

                    # item_type変換
                    item_type_map = {
                        '授業料': 'tuition',
                        '月会費': 'monthly_fee',
                        '設備費': 'facility',
                        '教材費': 'textbook',
                        '入会金': 'enrollment',
                    }
                    item_type = item_type_map.get(item_type_name, 'other')

                    if not dry_run:
                        brand = brands_by_code.get(brand_code)
                        grade = grades.get(grade_name)

                        product, created = Product.objects.update_or_create(
                            tenant_id=tenant_id,
                            product_code=product_code,
                            defaults={
                                'product_name': product_name[:100] if product_name else product_code,
                                'item_type': item_type,
                                'brand': brand,
                                'grade': grade,
                                'base_price': Decimal(base_price) if base_price else Decimal('0'),
                                'is_active': True,
                            }
                        )
                        if created:
                            products_created += 1
                    else:
                        if products_created < 20:
                            self.stdout.write(f'[DRY] Product: {product_name[:50]} | 種別: {item_type_name} | 単価: {base_price}円')
                        products_created += 1

        self.stdout.write(self.style.SUCCESS(f'完了: Course {courses_created}件, Product {products_created}件'))

    def get_brands_by_code(self, tenant_id):
        """DBから既存のブランドをbrand_codeでマッピングして取得"""
        brands = {}
        # tenant_idを無視して全てのアクティブなブランドを取得
        for brand in Brand.objects.filter(is_active=True):
            brands[brand.brand_code] = brand
        self.stdout.write(f'取得したブランド数: {len(brands)}')
        return brands

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

        return grades

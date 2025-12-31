"""
T3/T7/T8 データから契約関連の全データをインポートするコマンド
- T7: チケットマスタ
- T3: 商品（Product）
- T8: コース・パック・チケット紐付け
"""
import csv
import uuid
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import (
    Course, Product, Pack, PackCourse, CourseItem, PackItem,
    Ticket, CourseTicket, PackTicket, ProductPrice
)
from apps.schools.models import Brand, Grade


class Command(BaseCommand):
    help = 'T3/T7/T8からCourse, Product, Pack, Ticket等の全データをインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            '--t3-csv',
            type=str,
            default='/app/data/T3_契約情報_202512021655_UTF8.csv',
            help='T3 CSVファイルパス'
        )
        parser.add_argument(
            '--t7-csv',
            type=str,
            default='/app/data/T7_チケット情報_202511282031_UTF8.csv',
            help='T7 CSVファイルパス'
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            default='',
            help='テナントID（空の場合は既存データから取得）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存しない'
        )
        parser.add_argument(
            '--skip-tickets',
            action='store_true',
            help='チケットインポートをスキップ'
        )
        parser.add_argument(
            '--skip-products',
            action='store_true',
            help='商品インポートをスキップ'
        )

    def handle(self, *args, **options):
        t3_csv = options['t3_csv']
        t7_csv = options['t7_csv']
        dry_run = options['dry_run']
        skip_tickets = options['skip_tickets']
        skip_products = options['skip_products']

        self.stdout.write(f'T3 CSV: {t3_csv}')
        self.stdout.write(f'T7 CSV: {t7_csv}')
        self.stdout.write(f'Dry Run: {dry_run}')

        # tenant_id取得
        tenant_id = options['tenant_id']
        if not tenant_id:
            existing = Course.objects.first() or Brand.objects.first()
            if existing:
                tenant_id = str(existing.tenant_id)
                self.stdout.write(f'既存のtenant_idを使用: {tenant_id}')
            else:
                tenant_id = str(uuid.uuid4())
                self.stdout.write(f'新規tenant_idを生成: {tenant_id}')

        # ブランドマッピング取得
        brands_by_code = self.get_brands_by_code()
        self.stdout.write(f'ブランド数: {len(brands_by_code)}')

        # 学年マスタ取得/作成
        grades = self.ensure_grades(tenant_id, dry_run)

        stats = {
            'tickets': 0,
            'products': 0,
            'courses': 0,
            'packs': 0,
            'course_tickets': 0,
            'pack_tickets': 0,
        }

        with transaction.atomic():
            # Step 1: T7からチケットをインポート
            if not skip_tickets:
                stats['tickets'] = self.import_tickets(t7_csv, tenant_id, brands_by_code, dry_run)

            # Step 2: T3から商品をインポート
            if not skip_products:
                result = self.import_products_and_courses(
                    t3_csv, tenant_id, brands_by_code, grades, dry_run
                )
                stats['products'] = result['products']
                stats['courses'] = result['courses']
                stats['packs'] = result['packs']

            if dry_run:
                raise Exception('Dry run - rolling back')

        self.stdout.write(self.style.SUCCESS(
            f"\n=== 完了 ===\n"
            f"Tickets: {stats['tickets']}\n"
            f"Products: {stats['products']}\n"
            f"Courses: {stats['courses']}\n"
            f"Packs: {stats['packs']}\n"
        ))

    def get_brands_by_code(self):
        """DBからブランドをbrand_codeでマッピング"""
        brands = {}
        for brand in Brand.objects.filter(is_active=True):
            brands[brand.brand_code] = brand
        return brands

    def ensure_grades(self, tenant_id, dry_run):
        """学年マスタを確保"""
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

    def import_tickets(self, csv_path, tenant_id, brands_by_code, dry_run):
        """T7 CSVからチケットをインポート"""
        self.stdout.write('\n=== チケットインポート (T7) ===')

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                count = 0

                for row in reader:
                    ticket_id = row.get('チケットID', '').strip()
                    if not ticket_id:
                        continue

                    # ChプレフィックスをTに変換
                    ticket_code = ticket_id.replace('Ch', 'T')

                    ticket_type_raw = row.get('ticket種類', '1')
                    ticket_type_map = {
                        '1：授業': '1',
                        '5：講習会': '5',
                        '6：模試': '6',
                        '7:テスト対策': '7',
                        '8：自宅受講': '8',
                    }
                    ticket_type = ticket_type_map.get(ticket_type_raw, '0')

                    ticket_category_raw = row.get('ticket区別', '1')
                    ticket_category = '1' if ticket_category_raw == '1' else '0'

                    transfer_day_raw = row.get('振替曜日', '')
                    transfer_day = int(transfer_day_raw) if transfer_day_raw.isdigit() else None

                    annual_weekly = int(row.get('年間/週', '42') or '42')
                    max_per_lesson = int(row.get('Max値', '1') or '1')
                    total_tickets = int(row.get('※ﾁｹｯﾄ枚数', '42') or '42')
                    calendar_flag = int(row.get('カレンダーフラグ', '2') or '2')
                    year_carryover = row.get('年マタギ利用', '') == 'OK'

                    if not dry_run:
                        ticket, created = Ticket.objects.update_or_create(
                            tenant_id=tenant_id,
                            ticket_code=ticket_code,
                            defaults={
                                'ticket_name': row.get('チケット名', ticket_code)[:200],
                                'ticket_type': ticket_type,
                                'ticket_category': ticket_category,
                                'transfer_day': transfer_day,
                                'transfer_group': row.get('振替Group', '')[:50],
                                'consumption_symbol': row.get('消化記号', '')[:10],
                                'annual_weekly': annual_weekly,
                                'max_per_lesson': max_per_lesson,
                                'total_tickets': total_tickets,
                                'calendar_flag': calendar_flag,
                                'year_carryover': year_carryover,
                                'is_active': True,
                            }
                        )
                        if created:
                            count += 1
                    else:
                        if count < 10:
                            self.stdout.write(f'  [DRY] Ticket: {ticket_code} - {row.get("チケット名", "")[:30]}')
                        count += 1

                self.stdout.write(f'  チケット: {count}件')
                return count

        except FileNotFoundError:
            self.stdout.write(self.style.WARNING(f'  T7 CSVが見つかりません: {csv_path}'))
            return 0

    def import_products_and_courses(self, csv_path, tenant_id, brands_by_code, grades, dry_run):
        """T3 CSVから商品・コース・パックをインポート"""
        self.stdout.write('\n=== 商品・コースインポート (T3) ===')

        result = {'products': 0, 'courses': 0, 'packs': 0}

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                seen_products = set()
                seen_courses = set()
                seen_packs = set()

                # item_type変換マップ
                item_type_map = {
                    '授業料': 'tuition',
                    '月会費': 'monthly_fee',
                    '設備費': 'facility',
                    '教材費': 'textbook',
                    '諸経費': 'expense',
                    '入会金': 'enrollment',
                    '入会時授業料A': 'enrollment_tuition',
                    '入会時授業料1': 'enrollment_tuition',
                    '入会時授業料2': 'enrollment_tuition',
                    '入会時授業料3': 'enrollment_tuition',
                    '入会時月会費': 'enrollment_monthly_fee',
                    '入会時設備費': 'enrollment_facility',
                    '入会時教材費': 'enrollment_textbook',
                    '入会時諸経費': 'enrollment_expense',
                    '講習会': 'seminar',
                    '春期講習': 'seminar_spring',
                    '夏期講習': 'seminar_summer',
                    '冬期講習': 'seminar_winter',
                    'テスト対策': 'test_prep',
                    '模試': 'mock_exam',
                    'バッグ': 'bag',
                    'おやつ': 'snack',
                    'お弁当': 'lunch',
                    '保育回数券': 'childcare_ticket',
                    '預り料': 'custody',
                    '送迎費': 'transportation',
                    '総合指導管理費': 'management',
                }

                for row in reader:
                    contract_id = row.get('契約ID', '').strip()
                    billing_id = row.get('請求ID', '').strip()
                    contract_name = row.get('契約名', '').strip()
                    item_type_name = row.get('請求カテゴリ名', '').strip()
                    brand_code = row.get('契約ブランド記号', '').strip()
                    grade_name = row.get('対象学年', '').strip()
                    contract_type = row.get('契約種類', '1')

                    if not contract_id or not billing_id:
                        continue

                    # ブランドと学年取得
                    brand = brands_by_code.get(brand_code)
                    grade = grades.get(grade_name)

                    # 商品コード生成（請求IDから）
                    product_code = billing_id.replace('24', 'P').replace('_', '')[:20]

                    # item_type判定
                    item_type = item_type_map.get(item_type_name, 'other')

                    # 価格取得
                    try:
                        base_price = Decimal(row.get('単価', '0') or '0')
                    except (InvalidOperation, ValueError):
                        base_price = Decimal('0')

                    try:
                        display_price = Decimal(row.get('保護者表示用金額', '0') or '0')
                    except (InvalidOperation, ValueError):
                        display_price = Decimal('0')

                    try:
                        discount_max = int(row.get('割引MAX(%)', '0') or '0')
                    except (ValueError, TypeError):
                        discount_max = 0

                    # 月別価格
                    monthly_prices = {}
                    for m in range(1, 13):
                        try:
                            monthly_prices[m] = Decimal(row.get(f'{m}月', '0') or '0')
                        except (InvalidOperation, ValueError):
                            monthly_prices[m] = Decimal('0')

                    # 入会者別価格
                    enrollment_prices = {}
                    for m in range(1, 13):
                        try:
                            enrollment_prices[m] = Decimal(row.get(f'{m}月入会者', '0') or '0')
                        except (InvalidOperation, ValueError):
                            enrollment_prices[m] = Decimal('0')

                    # チケット要不要
                    requires_ticket = row.get('チケット要不要', '0') == '1'

                    # 日割りフラグ
                    prorate_flag = row.get('日割りフラグ', '0') == '1'
                    prorate_base_day = int(row.get('日割り基準日', '0') or '0')

                    # 商品をインポート
                    if billing_id not in seen_products:
                        seen_products.add(billing_id)

                        if not dry_run:
                            product, created = Product.objects.update_or_create(
                                tenant_id=tenant_id,
                                product_code=product_code,
                                defaults={
                                    'product_name': (row.get('明細表記', '') or contract_name)[:100],
                                    'item_type': item_type,
                                    'brand': brand,
                                    'grade': grade,
                                    'base_price': base_price,
                                    'discount_max': discount_max,
                                    'is_active': row.get('有効・無効', '1') == '1',
                                }
                            )

                            # ProductPriceも作成（月別・入会者別価格）
                            ProductPrice.objects.update_or_create(
                                tenant_id=tenant_id,
                                product=product,
                                defaults={
                                    # 請求月別価格
                                    'billing_price_jan': monthly_prices.get(1),
                                    'billing_price_feb': monthly_prices.get(2),
                                    'billing_price_mar': monthly_prices.get(3),
                                    'billing_price_apr': monthly_prices.get(4),
                                    'billing_price_may': monthly_prices.get(5),
                                    'billing_price_jun': monthly_prices.get(6),
                                    'billing_price_jul': monthly_prices.get(7),
                                    'billing_price_aug': monthly_prices.get(8),
                                    'billing_price_sep': monthly_prices.get(9),
                                    'billing_price_oct': monthly_prices.get(10),
                                    'billing_price_nov': monthly_prices.get(11),
                                    'billing_price_dec': monthly_prices.get(12),
                                    # 入会者別価格
                                    'enrollment_price_jan': enrollment_prices.get(1),
                                    'enrollment_price_feb': enrollment_prices.get(2),
                                    'enrollment_price_mar': enrollment_prices.get(3),
                                    'enrollment_price_apr': enrollment_prices.get(4),
                                    'enrollment_price_may': enrollment_prices.get(5),
                                    'enrollment_price_jun': enrollment_prices.get(6),
                                    'enrollment_price_jul': enrollment_prices.get(7),
                                    'enrollment_price_aug': enrollment_prices.get(8),
                                    'enrollment_price_sep': enrollment_prices.get(9),
                                    'enrollment_price_oct': enrollment_prices.get(10),
                                    'enrollment_price_nov': enrollment_prices.get(11),
                                    'enrollment_price_dec': enrollment_prices.get(12),
                                    'is_active': True,
                                }
                            )

                            if created:
                                result['products'] += 1
                        else:
                            if result['products'] < 10:
                                self.stdout.write(f'  [DRY] Product: {product_code} - {item_type_name} - {base_price}円')
                            result['products'] += 1

                    # コース（契約種類=1 かつ 授業料）
                    if contract_type == '1' and item_type == 'tuition':
                        course_key = f"{contract_id}_{brand_code}"
                        if course_key not in seen_courses:
                            seen_courses.add(course_key)

                            course_code = contract_id.replace('24', 'C').replace('_', '')[:20]

                            if not dry_run:
                                course, created = Course.objects.update_or_create(
                                    tenant_id=tenant_id,
                                    course_code=course_code,
                                    defaults={
                                        'course_name': contract_name[:100],
                                        'brand': brand,
                                        'grade': grade,
                                        'course_price': display_price,
                                        'is_active': True,
                                    }
                                )
                                if created:
                                    result['courses'] += 1
                            else:
                                if result['courses'] < 10:
                                    self.stdout.write(f'  [DRY] Course: {course_code} - {contract_name[:30]}')
                                result['courses'] += 1

                    # パック（契約種類=3）
                    elif contract_type == '3':
                        pack_key = f"{contract_id}_{brand_code}"
                        if pack_key not in seen_packs and item_type == 'tuition':
                            seen_packs.add(pack_key)

                            pack_code = contract_id.replace('24', 'PK').replace('_', '')[:20]

                            if not dry_run:
                                pack, created = Pack.objects.update_or_create(
                                    tenant_id=tenant_id,
                                    pack_code=pack_code,
                                    defaults={
                                        'pack_name': contract_name[:100],
                                        'brand': brand,
                                        'grade': grade,
                                        'pack_price': display_price,
                                        'is_active': True,
                                    }
                                )
                                if created:
                                    result['packs'] += 1
                            else:
                                if result['packs'] < 10:
                                    self.stdout.write(f'  [DRY] Pack: {pack_code} - {contract_name[:30]}')
                                result['packs'] += 1

                self.stdout.write(f'  商品: {result["products"]}件')
                self.stdout.write(f'  コース: {result["courses"]}件')
                self.stdout.write(f'  パック: {result["packs"]}件')
                return result

        except FileNotFoundError:
            self.stdout.write(self.style.WARNING(f'  T3 CSVが見つかりません: {csv_path}'))
            return result

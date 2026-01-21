"""
2026年2月請求データインポート
T4, T5, T6からStudentItem/StudentDiscountを作成
billing_month = '2026-02' に固定
"""
import csv
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import StudentItem, StudentDiscount, Course, Pack, Product, Contract
from apps.students.models import Student, Guardian
from apps.schools.models import Brand, School
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = '2026年2月請求データをインポート'

    BILLING_MONTH = '2026-02'
    DATA_DIR = '/Users/hirosesuzu/Library/CloudStorage/GoogleDrive-katsu44sky@gmail.com/マイドライブ/OZAシステム/月謝DATA/2月DATA'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存せず、何が作成されるかを表示'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='インポート前に既存の2026-02データを削除'
        )
        parser.add_argument(
            '--t4-only',
            action='store_true',
            help='T4（契約情報）のみインポート'
        )
        parser.add_argument(
            '--t5-only',
            action='store_true',
            help='T5（追加請求）のみインポート'
        )
        parser.add_argument(
            '--t6-only',
            action='store_true',
            help='T6（割引情報）のみインポート'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clear = options['clear']
        t4_only = options['t4_only']
        t5_only = options['t5_only']
        t6_only = options['t6_only']

        # 何も指定されていない場合は全部
        import_all = not (t4_only or t5_only or t6_only)

        # デフォルトテナントを取得
        self.default_tenant = Tenant.objects.first()
        if not self.default_tenant:
            self.stdout.write(self.style.ERROR("テナントが見つかりません"))
            return

        # キャッシュを作成
        self._build_caches()

        # 既存データを削除
        if clear and not dry_run:
            self._clear_existing_data()

        # インポート実行
        if import_all or t4_only:
            self.import_t4_contracts(dry_run)

        if import_all or t5_only:
            self.import_t5_charges(dry_run)

        if import_all or t6_only:
            self.import_t6_discounts(dry_run)

        self.stdout.write(self.style.SUCCESS("\n=== インポート完了 ==="))

    def _build_caches(self):
        """キャッシュを作成"""
        self.students_by_old_id = {
            s.old_id: s for s in Student.objects.select_related('tenant').all() if s.old_id
        }
        self.guardians_by_old_id = {
            g.old_id: g for g in Guardian.objects.all() if g.old_id
        }
        self.courses_by_code = {
            c.course_code: c for c in Course.objects.all() if c.course_code
        }
        self.packs_by_code = {
            p.pack_code: p for p in Pack.objects.all() if p.pack_code
        }
        self.brands_by_name = {
            b.brand_name: b for b in Brand.objects.all()
        }
        self.brands_by_short_name = {
            b.brand_name_short: b for b in Brand.objects.all() if b.brand_name_short
        }
        self.products_by_code = {
            p.product_code: p for p in Product.objects.all() if p.product_code
        }
        self.contracts_by_student_course = {}
        for c in Contract.objects.select_related('student', 'course').all():
            if c.student and c.course:
                key = (c.student.id, c.course.id)
                self.contracts_by_student_course[key] = c

        self.stdout.write(f"キャッシュ作成完了:")
        self.stdout.write(f"  生徒: {len(self.students_by_old_id)}件")
        self.stdout.write(f"  保護者: {len(self.guardians_by_old_id)}件")
        self.stdout.write(f"  コース: {len(self.courses_by_code)}件")
        self.stdout.write(f"  パック: {len(self.packs_by_code)}件")
        self.stdout.write(f"  ブランド: {len(self.brands_by_name)}件")
        self.stdout.write(f"  商品: {len(self.products_by_code)}件")
        self.stdout.write(f"  契約: {len(self.contracts_by_student_course)}件")

    def _clear_existing_data(self):
        """既存の2026-02データを削除"""
        deleted_items = StudentItem.objects.filter(billing_month=self.BILLING_MONTH).delete()
        deleted_discounts = StudentDiscount.objects.filter(
            start_date__year=2026, start_date__month=2
        ).delete()
        self.stdout.write(self.style.WARNING(
            f"既存データ削除: StudentItem {deleted_items[0]}件, StudentDiscount {deleted_discounts[0]}件"
        ))

    def _get_brand(self, brand_name):
        """ブランドを取得"""
        brand = self.brands_by_name.get(brand_name)
        if not brand:
            brand = self.brands_by_short_name.get(brand_name)
        return brand

    def _parse_date(self, date_str):
        """日付をパース"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y/%m/%d').date()
        except ValueError:
            return None

    def import_t4_contracts(self, dry_run):
        """T4: ユーザー契約情報をインポート"""
        csv_path = f"{self.DATA_DIR}/T4_ユーザー契約情報_202601141851_UTF8.csv"
        self.stdout.write(f"\n=== T4 ユーザー契約情報インポート ===")
        self.stdout.write(f"ファイル: {csv_path}")

        created_count = 0
        skipped_count = 0
        no_student_count = 0
        no_product_count = 0
        items_to_create = []

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"CSV行数: {len(rows)}")

        for i, row in enumerate(rows):
            course_id = row.get('受講ID', '').strip()
            student_old_id = row.get('生徒ID', '').strip()
            contract_id = row.get('契約ID', '').strip()
            contract_name = row.get('契約名', '').strip()
            brand_name = row.get('Class用ブランド名', '').strip()
            start_date_str = row.get('開始日', '').strip()
            end_date_str = row.get('終了日', '').strip()

            if not course_id or not student_old_id:
                skipped_count += 1
                continue

            # 終了日が2026年2月より前ならスキップ
            end_date = self._parse_date(end_date_str)
            if end_date and end_date < date(2026, 2, 1):
                skipped_count += 1
                continue

            # 生徒を検索
            student = self.students_by_old_id.get(student_old_id)
            if not student:
                no_student_count += 1
                skipped_count += 1
                continue

            # ブランドを取得
            brand = self._get_brand(brand_name)

            # コースを検索
            course = self.courses_by_code.get(contract_id)

            # 契約を検索
            contract = None
            if student and course:
                contract = self.contracts_by_student_course.get((student.id, course.id))

            # 商品を検索（授業料・月会費・設備費の3つ）
            item_types = [
                ('_1', 'tuition', '授業料'),
                ('_2', 'monthly_fee', '月会費'),
                ('_3', 'facility', '設備費'),
            ]

            found_products = []
            for suffix, item_type, label in item_types:
                product_code = f"{contract_id}{suffix}"
                product = self.products_by_code.get(product_code)
                if product and product.base_price and product.base_price > 0:
                    found_products.append((product, item_type, label))

            # 商品が見つからない場合は契約IDそのものを試す
            if not found_products:
                product = self.products_by_code.get(contract_id)
                if product and product.base_price and product.base_price > 0:
                    found_products.append((product, product.item_type or 'tuition', '授業料'))

            if not found_products:
                no_product_count += 1
                # 商品がなくてもスキップせず、金額0で作成
                continue

            tenant_id = student.tenant_id if student.tenant_id else self.default_tenant.id

            # 見つかった商品ごとにStudentItemを作成
            for idx, (product, item_type, label) in enumerate(found_products):
                old_id = course_id if idx == 0 else f"{course_id}_{idx+1}"

                item = StudentItem(
                    tenant_id=tenant_id,
                    old_id=old_id,
                    student=student,
                    contract=contract,
                    product=product,
                    brand=brand,
                    course=course,
                    start_date=self._parse_date(start_date_str),
                    billing_month=self.BILLING_MONTH,  # 固定
                    quantity=1,
                    unit_price=product.base_price or Decimal('0'),
                    discount_amount=Decimal('0'),
                    final_price=product.base_price or Decimal('0'),
                    is_billed=False,  # 未請求
                    notes=f'{contract_id}: {contract_name} ({label})',
                )
                items_to_create.append(item)
                created_count += 1

            if (i + 1) % 2000 == 0:
                self.stdout.write(f"  処理中... {i + 1}/{len(rows)}件")

        self.stdout.write(f"作成予定: {len(items_to_create)}件")
        self.stdout.write(f"  スキップ: {skipped_count}件")
        self.stdout.write(f"  (生徒なし: {no_student_count}件, 商品なし: {no_product_count}件)")

        if not dry_run and items_to_create:
            self.stdout.write('データベースに保存中...')
            with transaction.atomic():
                StudentItem.objects.bulk_create(items_to_create, batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f'T4: {len(items_to_create)}件保存完了'))

    def import_t5_charges(self, dry_run):
        """T5: 追加請求をインポート"""
        csv_path = f"{self.DATA_DIR}/T5_追加請求_202601141850_UTF8.csv"
        self.stdout.write(f"\n=== T5 追加請求インポート ===")
        self.stdout.write(f"ファイル: {csv_path}")

        created_count = 0
        skipped_count = 0
        no_student_count = 0
        items_to_create = []

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"CSV行数: {len(rows)}")

        # ヘッダー確認
        if rows:
            self.stdout.write(f"カラム: {list(rows[0].keys())[:10]}...")

        for i, row in enumerate(rows):
            # 有無チェック
            umu = row.get('有無', '').strip()
            if umu != '1':
                skipped_count += 1
                continue

            # 請求月チェック（2026/02のみ対象）
            billing_date_str = row.get('開始日', '').strip()
            billing_date = self._parse_date(billing_date_str)
            if billing_date:
                if billing_date.year != 2026 or billing_date.month != 2:
                    skipped_count += 1
                    continue

            student_old_id = row.get('生徒ID', '').strip()
            charge_id = row.get('請求ID', '').strip()

            if not student_old_id:
                skipped_count += 1
                continue

            # 生徒を検索
            student = self.students_by_old_id.get(student_old_id)
            if not student:
                no_student_count += 1
                skipped_count += 1
                continue

            # ブランドを取得
            brand_name = row.get('対象　同ブランド', '').strip()
            brand = self._get_brand(brand_name)

            # 金額をパース
            amount_str = row.get('金額', '0').strip()
            try:
                amount = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                amount = Decimal('0')

            if amount == 0:
                skipped_count += 1
                continue

            # 商品名
            product_name = row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）', '').strip()

            tenant_id = student.tenant_id if student.tenant_id else self.default_tenant.id

            item = StudentItem(
                tenant_id=tenant_id,
                old_id=charge_id,
                student=student,
                product=None,
                brand=brand,
                billing_month=self.BILLING_MONTH,
                quantity=1,
                unit_price=amount,
                discount_amount=Decimal('0'),
                final_price=amount,
                is_billed=False,
                notes=product_name,
            )
            items_to_create.append(item)
            created_count += 1

            if (i + 1) % 2000 == 0:
                self.stdout.write(f"  処理中... {i + 1}/{len(rows)}件")

        self.stdout.write(f"作成予定: {len(items_to_create)}件")
        self.stdout.write(f"  スキップ: {skipped_count}件, 生徒なし: {no_student_count}件")

        if not dry_run and items_to_create:
            self.stdout.write('データベースに保存中...')
            with transaction.atomic():
                StudentItem.objects.bulk_create(items_to_create, batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f'T5: {len(items_to_create)}件保存完了'))

    def import_t6_discounts(self, dry_run):
        """T6: 割引情報をインポート"""
        csv_path = f"{self.DATA_DIR}/T6_割引情報_202601141850_UTF8.csv"
        self.stdout.write(f"\n=== T6 割引情報インポート ===")
        self.stdout.write(f"ファイル: {csv_path}")

        created_count = 0
        skipped_count = 0
        no_target_count = 0
        discounts_to_create = []

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"CSV行数: {len(rows)}")

        for i, row in enumerate(rows):
            # 有無チェック
            umu = row.get('有無', '').strip()
            if umu != '1':
                skipped_count += 1
                continue

            # 期間チェック（2026/02が範囲内か）
            start_date_str = row.get('開始日', '').strip()
            end_date_str = row.get('終了日', '').strip()
            start_date = self._parse_date(start_date_str)
            end_date = self._parse_date(end_date_str)

            # 2026年2月1日が範囲内かチェック
            feb_date = date(2026, 2, 1)
            if start_date and start_date > feb_date:
                skipped_count += 1
                continue
            if end_date and end_date < feb_date:
                skipped_count += 1
                continue

            discount_id = row.get('割引ID', '').strip()
            student_old_id = row.get('生徒ID', '').strip()
            guardian_old_id = row.get('保護者ID', '').strip()

            # 対象（生徒または保護者）を検索
            student = self.students_by_old_id.get(student_old_id) if student_old_id else None
            guardian = self.guardians_by_old_id.get(guardian_old_id) if guardian_old_id else None

            if not student and not guardian:
                no_target_count += 1
                skipped_count += 1
                continue

            # ブランドを取得
            brand_name = row.get('対象　同ブランド', '').strip()
            brand = self._get_brand(brand_name)

            # 金額をパース
            amount_str = row.get('金額', '0').strip()
            try:
                amount = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                amount = Decimal('0')

            # 割引単位
            unit = row.get('割引単位', '円').strip()
            discount_unit = 'percent' if unit == '%' else 'yen'

            # 割引名
            discount_name = row.get('顧客表記用割引名（契約、請求IDの割引は、そのすぐ下に表記）', '').strip()

            # 繰り返し・自動割引
            is_recurring = row.get('繰り返し', '') == '1'
            is_auto = row.get('自動割引', '') == '1'

            # 終了条件
            end_condition_map = {
                '１回だけ': 'once',
                '毎月': 'monthly',
                '終了日まで': 'until_end_date',
            }
            end_condition_str = row.get('終了条件', '').strip()
            end_condition = end_condition_map.get(end_condition_str, 'once')

            tenant_id = student.tenant_id if student else (guardian.tenant_id if guardian else self.default_tenant.id)

            discount = StudentDiscount(
                tenant_id=tenant_id,
                old_id=discount_id,
                student=student,
                guardian=guardian,
                brand=brand,
                discount_name=discount_name or f'割引 {discount_id}',
                amount=amount,
                discount_unit=discount_unit,
                start_date=start_date,
                end_date=end_date,
                is_recurring=is_recurring,
                is_auto=is_auto,
                end_condition=end_condition,
                is_active=True,
            )
            discounts_to_create.append(discount)
            created_count += 1

            if (i + 1) % 2000 == 0:
                self.stdout.write(f"  処理中... {i + 1}/{len(rows)}件")

        self.stdout.write(f"作成予定: {len(discounts_to_create)}件")
        self.stdout.write(f"  スキップ: {skipped_count}件, 対象なし: {no_target_count}件")

        if not dry_run and discounts_to_create:
            self.stdout.write('データベースに保存中...')
            with transaction.atomic():
                StudentDiscount.objects.bulk_create(discounts_to_create, batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f'T6: {len(discounts_to_create)}件保存完了'))

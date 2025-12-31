"""
StudentItemにユーザー契約情報をインポート
授業料・月会費・設備費を3行に分けて作成
"""
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import StudentItem, Course, Pack, Product, Contract
from apps.students.models import Student
from apps.schools.models import Brand, School
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'ユーザー契約情報をStudentItemにインポート（授業料・月会費・設備費を分離）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            help='ユーザー契約情報CSVファイルパス'
        )
        parser.add_argument(
            '--contracts-csv',
            type=str,
            help='T4契約情報CSVファイルパス（旧形式）'
        )
        parser.add_argument(
            '--billing-csv',
            type=str,
            help='T5追加請求CSVファイルパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存せず、何が作成されるかを表示'
        )
        parser.add_argument(
            '--include-all',
            action='store_true',
            help='マッチしないレコードも含めてインポート'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='インポート前に既存データを削除'
        )

    def handle(self, *args, **options):
        user_csv = options.get('csv')
        contracts_csv = options.get('contracts_csv')
        billing_csv = options.get('billing_csv')
        dry_run = options['dry_run']
        include_all = options['include_all']
        clear = options['clear']

        # デフォルトテナントを取得
        self.default_tenant = Tenant.objects.first()
        if not self.default_tenant:
            self.stdout.write(self.style.ERROR("テナントが見つかりません"))
            return

        # 既存データを削除
        if clear and not dry_run:
            deleted_count = StudentItem.objects.count()
            StudentItem.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"既存の{deleted_count}件を削除しました"))

        # キャッシュを作成
        self.students_by_old_id = {
            s.old_id: s for s in Student.objects.all() if s.old_id
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
        self.products_by_name = {}
        self.products_by_code = {}
        for p in Product.objects.all():
            if p.product_name:
                self.products_by_name[p.product_name] = p
            if p.product_code:
                self.products_by_code[p.product_code] = p

        self.stdout.write(f"キャッシュ作成完了:")
        self.stdout.write(f"  生徒: {len(self.students_by_old_id)}件")
        self.stdout.write(f"  コース: {len(self.courses_by_code)}件")
        self.stdout.write(f"  パック: {len(self.packs_by_code)}件")
        self.stdout.write(f"  ブランド: {len(self.brands_by_name)}件")
        self.stdout.write(f"  商品(コード): {len(self.products_by_code)}件")

        total_created = 0

        # 新形式: ユーザー契約情報CSVをインポート
        if user_csv:
            created = self.import_user_contracts(user_csv, dry_run)
            total_created += created

        # 旧形式: T4契約情報をインポート
        if contracts_csv:
            created = self.import_contracts(contracts_csv, dry_run, include_all)
            total_created += created

        # T5追加請求をインポート
        if billing_csv:
            created = self.import_billing(billing_csv, dry_run, include_all)
            total_created += created

        # サマリー
        self.stdout.write("\n=== サマリー ===")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] {total_created}件のStudentItemを作成予定"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{total_created}件のStudentItemを作成しました"
            ))

    def import_user_contracts(self, csv_path, dry_run):
        """ユーザー契約情報CSVをインポート（授業料・月会費・設備費を分離）"""
        self.stdout.write(f"\n=== ユーザー契約情報インポート ===")
        self.stdout.write(f"ファイル: {csv_path}")

        created_count = 0
        skipped_count = 0
        error_count = 0
        no_student_count = 0
        no_product_count = 0

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"CSV行数: {len(rows)}")

        items_to_create = []

        for i, row in enumerate(rows):
            try:
                course_id = row.get('受講ID', '').strip()
                student_old_id = row.get('生徒ID', '').strip()
                contract_id = row.get('契約ID', '').strip()
                contract_name = row.get('契約名', '').strip()
                brand_name = row.get('Class用ブランド名', '').strip()
                start_date_str = row.get('開始日', '').strip()

                if not course_id or not student_old_id:
                    skipped_count += 1
                    continue

                # 生徒を検索
                student = self.students_by_old_id.get(student_old_id)
                if not student:
                    no_student_count += 1
                    skipped_count += 1
                    continue

                # ブランドを取得
                brand = self.brands_by_name.get(brand_name)

                # 開始日をパース
                start_date = None
                if start_date_str:
                    try:
                        start_date = datetime.strptime(start_date_str, '%Y/%m/%d').date()
                    except ValueError:
                        pass

                billing_month = start_date.strftime('%Y-%m') if start_date else '2025-01'
                tenant_id = student.tenant_id if student else self.default_tenant.id

                # 商品を検索（授業料・月会費・設備費の3つを探す）
                item_types_to_find = [
                    ('_1', 'tuition', '授業料'),
                    ('_2', 'monthly_fee', '月会費'),
                    ('_3', 'facility', '設備費'),
                ]

                found_products = []
                for suffix, item_type, label in item_types_to_find:
                    product_code = f"{contract_id}{suffix}"
                    product = self.products_by_code.get(product_code)
                    if product:
                        found_products.append((product, item_type, label))

                # 商品が見つからない場合は契約IDそのものを試す
                if not found_products:
                    product = self.products_by_code.get(contract_id)
                    if product:
                        found_products.append((product, product.item_type or 'tuition', '授業料'))

                if not found_products:
                    no_product_count += 1
                    # 商品がなくてもStudentItemを作成（金額0で）
                    item = StudentItem(
                        tenant_id=tenant_id,
                        old_id=course_id,
                        student=student,
                        product=None,
                        brand=brand,
                        start_date=start_date,
                        billing_month=billing_month,
                        quantity=1,
                        unit_price=Decimal('0'),
                        discount_amount=Decimal('0'),
                        final_price=Decimal('0'),
                        notes=f'{contract_id}: {contract_name}',
                    )
                    items_to_create.append(item)
                    created_count += 1
                else:
                    # 見つかった商品ごとにStudentItemを作成
                    for idx, (product, item_type, label) in enumerate(found_products):
                        # old_idは最初の商品のみcourse_idを使い、残りは連番を追加
                        old_id = course_id if idx == 0 else f"{course_id}_{idx+1}"

                        item = StudentItem(
                            tenant_id=tenant_id,
                            old_id=old_id,
                            student=student,
                            product=product,
                            brand=brand,
                            start_date=start_date,
                            billing_month=billing_month,
                            quantity=1,
                            unit_price=product.base_price or Decimal('0'),
                            discount_amount=Decimal('0'),
                            final_price=product.base_price or Decimal('0'),
                            notes=f'{contract_id}: {contract_name} ({label})',
                        )
                        items_to_create.append(item)
                        created_count += 1

                if (i + 1) % 1000 == 0:
                    self.stdout.write(f"  処理中... {i + 1}/{len(rows)}件")

            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    self.stdout.write(self.style.ERROR(f"エラー: {e} - {row.get('受講ID', '')}"))

        self.stdout.write(f"作成予定: {len(items_to_create)}件")

        if not dry_run and items_to_create:
            self.stdout.write('データベースに保存中...')
            with transaction.atomic():
                StudentItem.objects.bulk_create(items_to_create, batch_size=1000)
            self.stdout.write(self.style.SUCCESS('保存完了'))

        self.stdout.write(f"作成: {created_count}件, スキップ: {skipped_count}件, エラー: {error_count}件")
        self.stdout.write(f"  (生徒なし: {no_student_count}件, 商品なし: {no_product_count}件)")
        return created_count

    def import_contracts(self, csv_path, dry_run, include_all):
        """T4契約情報をインポート（旧形式）"""
        self.stdout.write(f"\n=== T4契約情報インポート ===")
        self.stdout.write(f"ファイル: {csv_path}")

        created_count = 0
        skipped_count = 0
        error_count = 0
        no_student_count = 0
        no_course_count = 0

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"行数: {len(rows)}")

        for row in rows:
            try:
                # 生徒を検索
                student_old_id = row.get('生徒ID', '').strip()
                student = self.students_by_old_id.get(student_old_id)

                if not student:
                    no_student_count += 1
                    if not include_all:
                        skipped_count += 1
                        continue

                # 契約IDからコースまたはパックを検索
                contract_id = row.get('契約ID', '').strip()
                course = self.courses_by_code.get(contract_id)
                pack = self.packs_by_code.get(contract_id) if not course else None

                if not course and not pack:
                    no_course_count += 1
                    if not include_all:
                        skipped_count += 1
                        continue

                # ブランドを取得
                brand_name = row.get('Class用ブランド名', '').strip()
                brand = self.brands_by_name.get(brand_name)

                # 開始日をパース
                start_date_str = row.get('開始日', '').strip()
                start_date = None
                if start_date_str:
                    try:
                        start_date = datetime.strptime(start_date_str, '%Y/%m/%d').date()
                    except ValueError:
                        pass

                # 請求月を計算
                billing_month = None
                if start_date:
                    billing_month = start_date.strftime('%Y%m')

                # 備考に元データ情報を含める
                notes_parts = []
                if row.get('備考', '').strip():
                    notes_parts.append(row.get('備考', '').strip())
                if not student:
                    notes_parts.append(f"[旧生徒ID: {student_old_id}]")
                if not course and not pack:
                    notes_parts.append(f"[旧契約ID: {contract_id}]")
                notes_parts.append(f"[契約名: {row.get('契約名', '')}]")
                notes = ' '.join(notes_parts)

                # テナントIDを決定
                tenant_id = student.tenant_id if student else self.default_tenant.id

                # StudentItemを作成
                if not dry_run:
                    StudentItem.objects.create(
                        tenant_id=tenant_id,
                        old_id=row.get('受講ID', ''),
                        student=student,
                        course=course,
                        brand=brand,
                        start_date=start_date,
                        billing_month=billing_month,
                        quantity=1,
                        unit_price=Decimal('0'),
                        discount_amount=Decimal('0'),
                        final_price=Decimal('0'),
                        notes=notes,
                    )
                created_count += 1

            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    self.stdout.write(self.style.ERROR(f"エラー: {e} - {row.get('受講ID', '')}"))

        self.stdout.write(f"作成: {created_count}件, スキップ: {skipped_count}件, エラー: {error_count}件")
        self.stdout.write(f"  (生徒なし: {no_student_count}件, コース/パックなし: {no_course_count}件)")
        return created_count

    def import_billing(self, csv_path, dry_run, include_all):
        """T5追加請求をインポート"""
        self.stdout.write(f"\n=== T5追加請求インポート ===")
        self.stdout.write(f"ファイル: {csv_path}")

        created_count = 0
        skipped_count = 0
        error_count = 0
        no_student_count = 0
        inactive_count = 0

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"行数: {len(rows)}")

        for row in rows:
            try:
                # 有無チェック（include_allの場合はスキップしない）
                umu = row.get('有無', '').strip()
                if umu != '1':
                    inactive_count += 1
                    if not include_all:
                        skipped_count += 1
                        continue

                # 生徒を検索
                student_old_id = row.get('生徒ID', '').strip()
                student = self.students_by_old_id.get(student_old_id)

                if not student:
                    no_student_count += 1
                    if not include_all:
                        skipped_count += 1
                        continue

                # 契約IDからコースを検索
                contract_id = row.get('対象　契約ID', '').strip()
                course = self.courses_by_code.get(contract_id)

                # ブランドを取得
                brand_name = row.get('対象　同ブランド', '').strip()
                brand = self.brands_by_name.get(brand_name)

                # 商品名から商品を検索
                product_name = row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）', '').strip()
                product = None
                # 商品名でマッチを試みる
                for pname, prod in self.products_by_name.items():
                    if pname in product_name or product_name in pname:
                        product = prod
                        break

                # 金額をパース
                amount_str = row.get('金額', '0').strip()
                try:
                    amount = Decimal(amount_str)
                except (InvalidOperation, ValueError):
                    amount = Decimal('0')

                # 開始日をパース
                start_date_str = row.get('開始日', '').strip()
                start_date = None
                if start_date_str:
                    try:
                        start_date = datetime.strptime(start_date_str, '%Y/%m/%d').date()
                    except ValueError:
                        pass

                # 請求月を計算
                billing_month = None
                if start_date:
                    billing_month = start_date.strftime('%Y%m')

                # 備考に元データ情報を含める
                notes_parts = [product_name]
                if not student:
                    notes_parts.append(f"[旧生徒ID: {student_old_id}]")
                if umu != '1':
                    notes_parts.append(f"[有無: {umu}]")
                notes = ' '.join(notes_parts)

                # テナントIDを決定
                tenant_id = student.tenant_id if student else self.default_tenant.id

                # StudentItemを作成
                if not dry_run:
                    StudentItem.objects.create(
                        tenant_id=tenant_id,
                        old_id=row.get('請求ID', ''),
                        student=student,
                        product=product,
                        course=course,
                        brand=brand,
                        start_date=start_date,
                        billing_month=billing_month,
                        quantity=1,
                        unit_price=amount,
                        discount_amount=Decimal('0'),
                        final_price=amount,
                        notes=notes,
                    )
                created_count += 1

            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    self.stdout.write(self.style.ERROR(f"エラー: {e} - {row.get('請求ID', '')}"))

        self.stdout.write(f"作成: {created_count}件, スキップ: {skipped_count}件, エラー: {error_count}件")
        self.stdout.write(f"  (生徒なし: {no_student_count}件, 有無!=1: {inactive_count}件)")
        return created_count

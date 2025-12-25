"""
既存のConfirmedBillingのitems_snapshotに請求カテゴリ・契約名・ブランド名を追加するマネジメントコマンド

Usage:
    # ドライラン（変更しない）
    python manage.py update_items_snapshot --dry-run

    # 特定の年月に適用
    python manage.py update_items_snapshot --year 2025 --month 1

    # 全フィールド強制更新
    python manage.py update_items_snapshot --force

    # 実行
    python manage.py update_items_snapshot
"""
import re
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ConfirmedBilling
from apps.contracts.models import Product, StudentItem
from apps.schools.models import Brand


class Command(BaseCommand):
    help = '既存のConfirmedBillingのitems_snapshotに請求カテゴリ・契約名・ブランド名を追加'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='対象年（指定しない場合は全て）'
        )
        parser.add_argument(
            '--month',
            type=int,
            help='対象月（指定しない場合は全て）'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存の値があっても強制的に更新'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        year = options.get('year')
        month = options.get('month')
        force = options.get('force', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))
        if force:
            self.stdout.write(self.style.WARNING('=== 強制更新モード ==='))

        # 対象のConfirmedBillingを取得
        queryset = ConfirmedBilling.objects.all()

        if year:
            queryset = queryset.filter(year=year)
        if month:
            queryset = queryset.filter(month=month)

        total_count = queryset.count()
        updated_count = 0
        skipped_count = 0

        self.stdout.write(f'対象件数: {total_count}件')

        # 商品マスタを事前にキャッシュ
        products_by_code = {}
        products_by_id = {}
        for product in Product.objects.select_related('brand').all():
            if product.product_code:
                products_by_code[product.product_code] = product
            products_by_id[str(product.id)] = product

        # ブランドをコードでキャッシュ
        brands_by_code = {}
        for brand in Brand.objects.all():
            if brand.brand_code:
                brands_by_code[brand.brand_code] = brand

        # StudentItemも取得してキャッシュ（old_idからProduct情報を取得するため）
        student_items_by_old_id = {}
        student_items_by_id = {}
        for si in StudentItem.objects.select_related('product', 'product__brand', 'course', 'brand', 'contract').all():
            if si.old_id:
                student_items_by_old_id[si.old_id] = si
            student_items_by_id[str(si.id)] = si

        for billing in queryset:
            try:
                result = self.update_snapshot(
                    billing,
                    products_by_code,
                    products_by_id,
                    student_items_by_old_id,
                    student_items_by_id,
                    brands_by_code,
                    dry_run,
                    force
                )
                if result:
                    updated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'エラー: {billing.billing_no} - {e}')
                )

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
対象件数: {total_count}件
更新件数: {updated_count}件
スキップ: {skipped_count}件
'''))

    def update_snapshot(self, billing, products_by_code, products_by_id, student_items_by_old_id, student_items_by_id, brands_by_code, dry_run, force) -> bool:
        """items_snapshotを更新"""
        items_snapshot = billing.items_snapshot or []

        if not items_snapshot:
            return False

        updated = False
        new_items = []

        for item in items_snapshot:
            new_item = dict(item)

            # 強制更新でない場合、既にデータが揃っていればスキップ
            if not force:
                has_category = item.get('item_type_display') and item.get('item_type_display') not in ['other', 'その他', '']
                has_brand = item.get('brand_name')
                has_course = item.get('course_name')
                if has_category and has_brand and has_course:
                    new_items.append(new_item)
                    continue

            # StudentItem を特定
            student_item = None
            product = None

            # 1. student_item_id からStudentItem検索
            if item.get('student_item_id'):
                student_item = student_items_by_id.get(item['student_item_id'])

            # 2. id からStudentItem検索
            if not student_item and item.get('id'):
                student_item = student_items_by_id.get(item['id'])

            # 3. old_id から検索
            if not student_item and item.get('old_id'):
                student_item = student_items_by_old_id.get(item['old_id'])

            # StudentItemから情報を取得
            if student_item:
                product = student_item.product

                # ブランド名
                if not new_item.get('brand_name') or force:
                    if student_item.brand:
                        new_item['brand_name'] = student_item.brand.brand_name or ''
                    elif product and product.brand:
                        new_item['brand_name'] = product.brand.brand_name or ''

                # コース名（契約名）
                if not new_item.get('course_name') or force:
                    if student_item.course:
                        new_item['course_name'] = student_item.course.course_name or ''

                # 契約番号
                if not new_item.get('contract_no') or force:
                    if student_item.contract:
                        new_item['contract_no'] = student_item.contract.contract_no or ''
                        new_item['contract_id'] = str(student_item.contract.id) if student_item.contract.id else ''

                # 旧ID
                if not new_item.get('old_id') or force:
                    if student_item.old_id:
                        new_item['old_id'] = student_item.old_id

            # Product情報を取得（StudentItemがなくてもproduct_idから）
            if not product and item.get('product_id'):
                product = products_by_id.get(item['product_id'])

            # notesフィールドからブランドと商品名を抽出（他の方法で取得できなかった場合）
            # 形式: "24GYJ_1000247: 進学ジム 中3_ 2DaysFree"
            notes = item.get('notes', '') or ''
            if notes and (not new_item.get('brand_name') or not new_item.get('course_name')):
                # 旧IDパターン: 24XXX_XXXXXXX
                match = re.match(r'^(\d{2})([A-Z]{2,4})_(\d+)', notes)
                if match:
                    brand_code = match.group(2)  # GYJ, AEC, SOR, etc.
                    old_id_from_notes = f"{match.group(1)}{match.group(2)}_{match.group(3)}"

                    # ブランド名を取得
                    if not new_item.get('brand_name') or force:
                        brand = brands_by_code.get(brand_code)
                        if brand:
                            new_item['brand_name'] = brand.brand_name

                    # 旧IDを設定
                    if not new_item.get('old_id') or force:
                        new_item['old_id'] = old_id_from_notes

                    # コロン以降が商品名/コース名
                    if ': ' in notes:
                        course_desc = notes.split(': ', 1)[1]
                        if not new_item.get('course_name') or force:
                            new_item['course_name'] = course_desc
                        if not new_item.get('product_name') or force:
                            new_item['product_name'] = course_desc

            # notesフィールドをcourse_nameのフォールバックとして使用（notesは上で定義済み）
            if notes and (not new_item.get('course_name') or force):
                # notesをそのままcourse_nameとして使う（商品説明が入っている）
                new_item['course_name'] = notes
                if not new_item.get('product_name') or force:
                    new_item['product_name'] = notes

            if product:
                # 請求カテゴリを更新
                if not new_item.get('item_type') or new_item.get('item_type') == 'other' or force:
                    new_item['item_type'] = product.item_type or ''
                    new_item['item_type_display'] = product.get_item_type_display() if product.item_type else ''

                # 契約名（product_name_short）を更新
                if not new_item.get('product_name_short') or force:
                    new_item['product_name_short'] = product.product_name_short or ''

                # 商品名を更新
                if not new_item.get('product_name') or force:
                    new_item['product_name'] = product.product_name or ''

                # ブランド名（ProductのBrandから）
                if not new_item.get('brand_name') or force:
                    if product.brand:
                        new_item['brand_name'] = product.brand.brand_name or ''

                updated = True
                self.stdout.write(
                    f'  更新: {billing.billing_no} - {product.product_name} → {new_item.get("item_type_display", "")} ({new_item.get("brand_name", "")})'
                )
            else:
                # Product が見つからない場合
                # ブランド名がある場合は授業料をデフォルトに
                if new_item.get('brand_name'):
                    if not new_item.get('item_type') or new_item.get('item_type') == 'other':
                        new_item['item_type'] = 'tuition'
                        new_item['item_type_display'] = '授業料'
                    updated = True
                    self.stdout.write(
                        f'  更新(brand): {billing.billing_no} - {new_item.get("course_name", "")} ({new_item.get("brand_name", "")})'
                    )
                elif new_item.get('course_name'):
                    # コース名だけある場合も授業料をデフォルトに
                    if not new_item.get('item_type') or new_item.get('item_type') == 'other':
                        new_item['item_type'] = 'tuition'
                        new_item['item_type_display'] = '授業料'
                    updated = True
                    self.stdout.write(
                        f'  更新(notes): {billing.billing_no} - {new_item.get("course_name", "")}'
                    )
                else:
                    # 完全に情報が取れない場合
                    if not new_item.get('item_type') or new_item.get('item_type') == 'other':
                        new_item['item_type'] = 'other'
                        new_item['item_type_display'] = 'その他'
                        updated = True

            new_items.append(new_item)

        if not updated:
            return False

        if dry_run:
            self.stdout.write(f'  [ドライラン] {billing.billing_no}: items_snapshot 更新')
        else:
            with transaction.atomic():
                billing.items_snapshot = new_items
                billing.save(update_fields=['items_snapshot'])
            self.stdout.write(self.style.SUCCESS(f'  更新完了: {billing.billing_no}'))

        return True

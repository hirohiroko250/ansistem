"""
商品統合コマンド

重複している商品を統合して商品マスタを整理する
- ブランド×商品名×価格 で同じものを1つに統合
- 設備費・入会金はブランドごとに1つだけ残す
- CourseItem, PackItem の参照も更新
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from apps.contracts.models import Product, CourseItem, PackItem


class Command(BaseCommand):
    help = '重複商品を統合する'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際に削除せずに統合結果をプレビュー',
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            default='c2c9db40-7352-4d28-a554-bd82d6afb771',
            help='テナントID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tenant_id = options['tenant_id']

        self.stdout.write(f"テナント: {tenant_id}")
        self.stdout.write(f"ドライラン: {dry_run}")
        self.stdout.write("")

        # 統計
        total_before = Product.objects.filter(tenant_id=tenant_id).count()
        self.stdout.write(f"統合前の商品数: {total_before:,}件")

        # ブランド×商品名×価格でグループ化（first_idは取らない）
        duplicates = list(
            Product.objects
            .filter(tenant_id=tenant_id)
            .values('brand_id', 'product_name', 'base_price')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .order_by('-count')
        )

        total_groups = len(duplicates)
        self.stdout.write(f"重複グループ数: {total_groups:,}件")
        self.stdout.write("")

        # TOP 10 表示
        self.stdout.write("=== 重複が多い商品 TOP 10 ===")
        for i, dup in enumerate(duplicates[:10]):
            # ブランド名を取得
            brand_name = 'ブランドなし'
            if dup['brand_id']:
                first_product = Product.objects.filter(
                    tenant_id=tenant_id,
                    brand_id=dup['brand_id'],
                    product_name=dup['product_name'],
                    base_price=dup['base_price']
                ).select_related('brand').first()
                if first_product and first_product.brand:
                    brand_name = first_product.brand.brand_name

            self.stdout.write(
                f"  {i+1}. [{brand_name}] {dup['product_name']} "
                f"¥{dup['base_price']:,.0f} → {dup['count']:,}件"
            )
        self.stdout.write("")

        if dry_run:
            # プレビューのみ
            total_to_delete = sum(d['count'] - 1 for d in duplicates)
            total_after = total_before - total_to_delete
            self.stdout.write(f"削除予定: {total_to_delete:,}件")
            self.stdout.write(f"統合後の商品数: {total_after:,}件")
            self.stdout.write("")
            self.stdout.write("ドライランモードです。実際に削除するには --dry-run を外して実行してください。")
            return

        # 実際に統合
        with transaction.atomic():
            consolidated = 0
            deleted = 0
            updated_course_items = 0
            updated_pack_items = 0
            deleted_course_items = 0
            deleted_pack_items = 0

            for dup in duplicates:
                # このグループの全商品を取得
                products = list(
                    Product.objects
                    .filter(
                        tenant_id=tenant_id,
                        brand_id=dup['brand_id'],
                        product_name=dup['product_name'],
                        base_price=dup['base_price']
                    )
                    .order_by('created_at')
                )

                if len(products) < 2:
                    continue

                # 最初の商品を残す
                keep_product = products[0]
                delete_products = products[1:]

                # CourseItem, PackItem の参照を更新または削除
                for del_product in delete_products:
                    # CourseItem の処理
                    for ci in CourseItem.objects.filter(tenant_id=tenant_id, product=del_product):
                        # 既に同じcourse+keep_productの組み合わせが存在するかチェック
                        existing = CourseItem.objects.filter(
                            tenant_id=tenant_id,
                            course=ci.course,
                            product=keep_product
                        ).exists()
                        if existing:
                            # 重複するので削除
                            ci.delete()
                            deleted_course_items += 1
                        else:
                            # 参照を更新
                            ci.product = keep_product
                            ci.save()
                            updated_course_items += 1

                    # PackItem の処理
                    for pi in PackItem.objects.filter(tenant_id=tenant_id, product=del_product):
                        # 既に同じpack+keep_productの組み合わせが存在するかチェック
                        existing = PackItem.objects.filter(
                            tenant_id=tenant_id,
                            pack=pi.pack,
                            product=keep_product
                        ).exists()
                        if existing:
                            # 重複するので削除
                            pi.delete()
                            deleted_pack_items += 1
                        else:
                            # 参照を更新
                            pi.product = keep_product
                            pi.save()
                            updated_pack_items += 1

                # 重複商品を削除
                delete_ids = [p.id for p in delete_products]
                Product.objects.filter(id__in=delete_ids).delete()
                deleted += len(delete_ids)
                consolidated += 1

                if consolidated % 100 == 0:
                    self.stdout.write(f"  進捗: {consolidated:,}グループ処理完了...")

        total_after = Product.objects.filter(tenant_id=tenant_id).count()

        self.stdout.write("")
        self.stdout.write("=== 統合結果 ===")
        self.stdout.write(f"統合したグループ数: {consolidated:,}件")
        self.stdout.write(f"削除した商品数: {deleted:,}件")
        self.stdout.write(f"更新したCourseItem: {updated_course_items:,}件")
        self.stdout.write(f"削除したCourseItem（重複）: {deleted_course_items:,}件")
        self.stdout.write(f"更新したPackItem: {updated_pack_items:,}件")
        self.stdout.write(f"削除したPackItem（重複）: {deleted_pack_items:,}件")
        self.stdout.write(f"統合後の商品数: {total_after:,}件")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("商品統合が完了しました！"))

#!/usr/bin/env python
"""
パック商品（D列=4）からPackItemを生成

商品コードのプレフィックスでグループ化し、各パックに含まれる商品を登録
コースと同じロジックを使用
"""
import os
import sys
import django

sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
from collections import defaultdict
from apps.contracts.models import Product, Pack, PackItem
from apps.tenants.models import Tenant


EXCEL_PATH = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/商品テーブル.xlsx'


def get_tenant():
    return Tenant.objects.get(tenant_code='OZA')


def generate_pack_items():
    print("=" * 60)
    print("PackItem 自動生成")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    # Excel読み込み
    print(f"\nExcel読み込み中...")
    df = pd.read_excel(EXCEL_PATH, sheet_name='Product Export Dec 2 2025 (2)')

    # D列=4のパック商品をフィルタ
    pack_products = df[df['パックは４番'] == 4]
    print(f"パック商品数: {len(pack_products)}")

    # プレフィックスでグループ化
    prefix_groups = defaultdict(list)
    for idx, row in pack_products.iterrows():
        code = str(row.get('商品コード', '')).strip()
        if code and code != 'nan' and '_' in code:
            prefix = code.rsplit('_', 1)[0]
            suffix = code.rsplit('_', 1)[1]
            prefix_groups[prefix].append((suffix, code))

    print(f"パックプレフィックス数: {len(prefix_groups)}")

    # 統計
    pack_item_created = 0
    pack_item_updated = 0
    packs_not_found = 0
    products_not_found = 0
    errors = 0

    for prefix, items in prefix_groups.items():
        try:
            # パックを取得
            pack = Pack.objects.filter(
                tenant_id=tenant.id,
                pack_code=prefix
            ).first()

            if not pack:
                packs_not_found += 1
                continue

            # 各商品をPackItemとして登録
            for suffix, product_code in items:
                try:
                    suffix_num = int(suffix)
                except ValueError:
                    continue

                # _1〜_9 のみ通常の構成として登録（_50以上は入会時用）
                if 1 <= suffix_num <= 9:
                    product = Product.objects.filter(
                        tenant_id=tenant.id,
                        product_code=product_code
                    ).first()

                    if not product:
                        products_not_found += 1
                        continue

                    pack_item, created = PackItem.objects.update_or_create(
                        pack=pack,
                        product=product,
                        defaults={
                            'tenant_id': tenant.id,
                            'quantity': 1,
                            'sort_order': suffix_num,
                            'is_active': True,
                        }
                    )

                    if created:
                        pack_item_created += 1
                    else:
                        pack_item_updated += 1

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"エラー ({prefix}): {e}")

    print(f"\n=== 結果 ===")
    print(f"PackItem作成: {pack_item_created}")
    print(f"PackItem更新: {pack_item_updated}")
    print(f"パック未発見: {packs_not_found}")
    print(f"商品未発見: {products_not_found}")
    print(f"エラー: {errors}")

    # 確認
    print(f"\n=== 確認 ===")
    print(f"PackItem総数: {PackItem.objects.filter(tenant_id=tenant.id).count()}")

    # サンプル表示
    print(f"\n=== サンプル（最初の3パック）===")
    for pack in Pack.objects.filter(tenant_id=tenant.id).exclude(pack_items=None)[:3]:
        print(f"\n【{pack.pack_code}】{pack.pack_name}")
        print(f"  ブランド: {pack.brand.brand_name if pack.brand else 'なし'}")

        # パック内のコース
        print("  [含まれるコース]")
        for pc in pack.pack_courses.all().order_by('sort_order')[:3]:
            print(f"    └ {pc.course.course_name}")

        # パック独自の商品構成
        print("  [パック商品構成]")
        for item in pack.pack_items.all().order_by('sort_order'):
            print(f"    └ {item.sort_order}: {item.product.product_name} ({item.product.item_type}) ¥{item.product.base_price}")


if __name__ == '__main__':
    generate_pack_items()

#!/usr/bin/env python
"""
パック商品（D列=4）の料金をProductPriceにインポート
"""
import os
import sys
sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import pandas as pd
from decimal import Decimal
from apps.contracts.models import Product, ProductPrice
from apps.tenants.models import Tenant


XLSX_PATH = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/商品テーブル.xlsx'


def get_tenant():
    return Tenant.objects.get(tenant_code='OZA')


def safe_decimal(val):
    """安全にDecimalに変換"""
    if pd.isna(val) or val == '' or val is None:
        return Decimal('0')
    try:
        return Decimal(str(int(float(val))))
    except:
        return Decimal('0')


def import_pack_prices():
    print("=" * 60)
    print("パック商品料金インポート")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    # Excelを読み込み（D列=4のデータ）
    df = pd.read_excel(XLSX_PATH, sheet_name='T3_契約情報_202512021655_UTF8', header=None)

    # ヘッダー行をスキップしてデータ行のみ
    data_rows = df.iloc[1:]

    # D列（契約種類）が4のものを抽出
    pack_data = data_rows[data_rows.iloc[:, 4] == 4]
    print(f"パック商品データ数: {len(pack_data)}")

    # 現在のProductPrice件数
    current_count = ProductPrice.objects.filter(tenant_id=tenant.id).count()
    print(f"現在のProductPrice件数: {current_count}")

    created = 0
    updated = 0
    not_found = 0
    errors = 0

    # 列インデックス
    # 7: product_code（請求ID）
    # 33: base_price
    # 35-46: 1月~12月の請求料金
    # 47-58: 1月~12月の入会者料金

    for idx, row in pack_data.iterrows():
        try:
            product_code = str(row.iloc[7]).strip()
            if not product_code or product_code == 'nan':
                continue

            # 商品を検索
            product = Product.objects.filter(
                tenant_id=tenant.id,
                product_code=product_code
            ).first()

            if not product:
                not_found += 1
                if not_found <= 5:
                    print(f"  商品未発見: {product_code}")
                continue

            # 月別料金（請求）
            billing_prices = {
                'billing_price_jan': safe_decimal(row.iloc[35]),
                'billing_price_feb': safe_decimal(row.iloc[36]),
                'billing_price_mar': safe_decimal(row.iloc[37]),
                'billing_price_apr': safe_decimal(row.iloc[38]),
                'billing_price_may': safe_decimal(row.iloc[39]),
                'billing_price_jun': safe_decimal(row.iloc[40]),
                'billing_price_jul': safe_decimal(row.iloc[41]),
                'billing_price_aug': safe_decimal(row.iloc[42]),
                'billing_price_sep': safe_decimal(row.iloc[43]),
                'billing_price_oct': safe_decimal(row.iloc[44]),
                'billing_price_nov': safe_decimal(row.iloc[45]),
                'billing_price_dec': safe_decimal(row.iloc[46]),
            }

            # 月別料金（入会者）
            enrollment_prices = {
                'enrollment_price_jan': safe_decimal(row.iloc[47]),
                'enrollment_price_feb': safe_decimal(row.iloc[48]),
                'enrollment_price_mar': safe_decimal(row.iloc[49]),
                'enrollment_price_apr': safe_decimal(row.iloc[50]),
                'enrollment_price_may': safe_decimal(row.iloc[51]),
                'enrollment_price_jun': safe_decimal(row.iloc[52]),
                'enrollment_price_jul': safe_decimal(row.iloc[53]),
                'enrollment_price_aug': safe_decimal(row.iloc[54]),
                'enrollment_price_sep': safe_decimal(row.iloc[55]),
                'enrollment_price_oct': safe_decimal(row.iloc[56]),
                'enrollment_price_nov': safe_decimal(row.iloc[57]),
                'enrollment_price_dec': safe_decimal(row.iloc[58]),
            }

            # ProductPriceをupsert
            price, is_created = ProductPrice.objects.update_or_create(
                tenant_id=tenant.id,
                product=product,
                defaults={
                    **billing_prices,
                    **enrollment_prices,
                    'is_active': True,
                }
            )

            if is_created:
                created += 1
            else:
                updated += 1

            if (created + updated) % 5000 == 0:
                print(f"  処理中... {created + updated}件")

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  エラー: {row.iloc[7]} - {e}")

    print()
    print("=== 結果 ===")
    print(f"作成: {created}")
    print(f"更新: {updated}")
    print(f"商品未発見: {not_found}")
    print(f"エラー: {errors}")

    # 確認
    final_count = ProductPrice.objects.filter(tenant_id=tenant.id).count()
    print()
    print("=== 確認 ===")
    print(f"ProductPrice総数: {final_count}")

    # サンプル確認
    print()
    print("=== パック料金サンプル ===")
    from apps.contracts.models import Pack, PackItem
    pack = Pack.objects.filter(pack_code='24AEC_1000047').first()
    if pack:
        print(f"パック: {pack.pack_code}")
        items = PackItem.objects.filter(pack=pack).select_related('product')[:5]
        total = Decimal('0')
        for item in items:
            price = ProductPrice.objects.filter(product=item.product).first()
            if price and price.billing_price_jan:
                print(f"  {item.product.product_name}: {price.billing_price_jan}円")
                total += price.billing_price_jan
        print(f"  合計（1月）: {total}円")


if __name__ == '__main__':
    import_pack_prices()

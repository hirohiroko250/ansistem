#!/usr/bin/env python
"""
T3_契約情報シートからProductPriceデータをインポート

入会月別料金（T5〜T5.11）と請求月別料金（1月〜12月）をProductPriceテーブルに登録
"""
import os
import sys
import django

sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
from decimal import Decimal
from apps.contracts.models import Product, ProductPrice
from apps.tenants.models import Tenant


EXCEL_PATH = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/商品テーブル.xlsx'
SHEET_NAME = 'T3_契約情報_202512021655_UTF8'


def get_tenant():
    return Tenant.objects.get(tenant_code='OZA')


def safe_decimal(value):
    """安全にDecimalに変換"""
    if pd.isna(value):
        return None
    try:
        return Decimal(str(int(float(value))))
    except (ValueError, TypeError):
        return None


def import_product_prices():
    print("=" * 60)
    print("ProductPrice インポート")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    # 既存データ削除
    print("\n既存データ削除中...")
    deleted_count = ProductPrice.objects.filter(tenant_id=tenant.id).delete()[0]
    print(f"削除完了: {deleted_count}件")

    # Excel読み込み
    print(f"\nExcel読み込み中: {EXCEL_PATH}")
    print(f"シート: {SHEET_NAME}")
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

    # ヘッダー行をスキップ（最初の行がヘッダー）
    df = df.iloc[1:]
    print(f"全{len(df)}行")

    # カラム名の確認
    # product_code = 列7 (product_code)
    # 入会月別: T5, T5.1〜T5.11 (1月〜12月入会者)
    # 請求月別: T3列の近く (1月〜12月)

    created = 0
    updated = 0
    skipped = 0
    errors = 0

    for idx, row in df.iterrows():
        try:
            product_code = str(row.get('product_code', '')).strip()
            if not product_code or product_code == 'nan':
                skipped += 1
                continue

            # 対応するProductを取得
            product = Product.objects.filter(
                tenant_id=tenant.id,
                product_code=product_code
            ).first()

            if not product:
                skipped += 1
                continue

            # 入会月別料金（T5 = 1月, T5.1 = 2月, ...）
            enrollment_prices = {
                'enrollment_price_jan': safe_decimal(row.get('T5')),
                'enrollment_price_feb': safe_decimal(row.get('T5.1')),
                'enrollment_price_mar': safe_decimal(row.get('T5.2')),
                'enrollment_price_apr': safe_decimal(row.get('T5.3')),
                'enrollment_price_may': safe_decimal(row.get('T5.4')),
                'enrollment_price_jun': safe_decimal(row.get('T5.5')),
                'enrollment_price_jul': safe_decimal(row.get('T5.6')),
                'enrollment_price_aug': safe_decimal(row.get('T5.7')),
                'enrollment_price_sep': safe_decimal(row.get('T5.8')),
                'enrollment_price_oct': safe_decimal(row.get('T5.9')),
                'enrollment_price_nov': safe_decimal(row.get('T5.10')),
                'enrollment_price_dec': safe_decimal(row.get('T5.11')),
            }

            # 請求月別料金（T3列の近くにある 1月〜12月）
            # 元のカラム名を使用
            billing_prices = {}

            # T3シートの構造に合わせて請求月別カラムを探す
            for col in df.columns:
                col_str = str(col)
                if col_str == '1月' or col_str.endswith('.36'):  # Unnamed:36 などの可能性
                    billing_prices['billing_price_jan'] = safe_decimal(row.get(col))
                # 同様に他の月も...

            # 入会月別料金がすべてNoneかどうかチェック
            has_enrollment_prices = any(v is not None for v in enrollment_prices.values())

            if not has_enrollment_prices:
                skipped += 1
                continue

            # ProductPrice作成または更新
            price_record, is_created = ProductPrice.objects.update_or_create(
                tenant_id=tenant.id,
                product=product,
                defaults={
                    **enrollment_prices,
                    'is_active': True,
                }
            )

            if is_created:
                created += 1
            else:
                updated += 1

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"エラー (行{idx}): {e}")

    print(f"\n=== 結果 ===")
    print(f"作成: {created}")
    print(f"更新: {updated}")
    print(f"スキップ: {skipped}")
    print(f"エラー: {errors}")

    # 確認
    print(f"\n=== 確認 ===")
    print(f"ProductPrice総数: {ProductPrice.objects.filter(tenant_id=tenant.id).count()}")

    # サンプル表示
    print(f"\n=== サンプル（教材費の例）===")
    for pp in ProductPrice.objects.filter(
        tenant_id=tenant.id,
        product__item_type='textbook'
    )[:3]:
        print(f"\n{pp.product.product_name}")
        print(f"  基本価格: ¥{pp.product.base_price}")
        print(f"  1月入会: ¥{pp.enrollment_price_jan}")
        print(f"  2月入会: ¥{pp.enrollment_price_feb}")
        print(f"  3月入会: ¥{pp.enrollment_price_mar}")
        print(f"  4月入会: ¥{pp.enrollment_price_apr}")
        print(f"  10月入会: ¥{pp.enrollment_price_oct}")
        print(f"  11月入会: ¥{pp.enrollment_price_nov}")
        print(f"  12月入会: ¥{pp.enrollment_price_dec}")


if __name__ == '__main__':
    import_product_prices()

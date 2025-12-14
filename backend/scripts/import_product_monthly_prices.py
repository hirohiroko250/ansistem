#!/usr/bin/env python
"""
T3_契約情報CSVからProductモデルの月別料金フィールドに直接データを取り込むスクリプト

使用方法:
    python manage.py shell < scripts/import_product_monthly_prices.py

本番環境:
    docker exec -i oza_backend sh -c 'python manage.py shell < /app/scripts/import_product_monthly_prices.py'

事前準備:
    CSVファイルを /app/T3_契約情報.csv にコピーしてください
"""
import csv
import os
from decimal import Decimal
from apps.contracts.models import Product

CSV_PATH = '/app/T3_契約情報.csv'

print("=== Product 月別料金フィールド インポート ===")

if not os.path.exists(CSV_PATH):
    print(f"エラー: ファイルが見つかりません: {CSV_PATH}")
else:
    products = {p.product_code: p for p in Product.objects.all()}
    print(f"既存Product数: {len(products)}")

    updated_count = 0
    not_found_count = 0
    error_count = 0
    processed = set()

    def to_decimal(val):
        if not val or val == '':
            return None
        try:
            return Decimal(val)
        except:
            return None

    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                billing_id = row.get('請求ID', '').strip()
                if not billing_id or billing_id in processed:
                    continue
                processed.add(billing_id)

                product = products.get(billing_id)
                if not product:
                    not_found_count += 1
                    continue

                product.billing_price_jan = to_decimal(row.get('1月', ''))
                product.billing_price_feb = to_decimal(row.get('2月', ''))
                product.billing_price_mar = to_decimal(row.get('3月', ''))
                product.billing_price_apr = to_decimal(row.get('4月', ''))
                product.billing_price_may = to_decimal(row.get('5月', ''))
                product.billing_price_jun = to_decimal(row.get('6月', ''))
                product.billing_price_jul = to_decimal(row.get('7月', ''))
                product.billing_price_aug = to_decimal(row.get('8月', ''))
                product.billing_price_sep = to_decimal(row.get('9月', ''))
                product.billing_price_oct = to_decimal(row.get('10月', ''))
                product.billing_price_nov = to_decimal(row.get('11月', ''))
                product.billing_price_dec = to_decimal(row.get('12月', ''))

                product.enrollment_price_jan = to_decimal(row.get('1月入会者', ''))
                product.enrollment_price_feb = to_decimal(row.get('2月入会者', ''))
                product.enrollment_price_mar = to_decimal(row.get('3月入会者', ''))
                product.enrollment_price_apr = to_decimal(row.get('4月入会者', ''))
                product.enrollment_price_may = to_decimal(row.get('5月入会者', ''))
                product.enrollment_price_jun = to_decimal(row.get('6月入会者', ''))
                product.enrollment_price_jul = to_decimal(row.get('7月入会者', ''))
                product.enrollment_price_aug = to_decimal(row.get('8月入会者', ''))
                product.enrollment_price_sep = to_decimal(row.get('9月入会者', ''))
                product.enrollment_price_oct = to_decimal(row.get('10月入会者', ''))
                product.enrollment_price_nov = to_decimal(row.get('11月入会者', ''))
                product.enrollment_price_dec = to_decimal(row.get('12月入会者', ''))

                product.save()
                updated_count += 1

                if updated_count <= 20:
                    print(f"  更新: {billing_id}")
                elif updated_count % 10000 == 0:
                    print(f"  処理中... {updated_count} 件完了")

            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    print(f"  エラー: {e}")

    print(f"\n=== 完了 ===")
    print(f"更新: {updated_count}")
    print(f"見つからず: {not_found_count}")
    print(f"エラー: {error_count}")

    sample = Product.objects.exclude(billing_price_jan=None)[:3]
    for p in sample:
        print(f"  {p.product_code}: 1月請求={p.billing_price_jan} 1月入会者={p.enrollment_price_jan}")

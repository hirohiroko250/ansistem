#!/usr/bin/env python
"""
T3_契約情報CSVから月によって料金が異なるデータのみをProductPriceテーブルに取り込むスクリプト

使用方法:
    python manage.py shell < scripts/import_product_prices_varying_only.py

本番環境:
    docker exec -i oza_backend python manage.py shell < scripts/import_product_prices_varying_only.py

事前準備:
    CSVファイルを /tmp/T3_契約情報.csv にコピーしてください

対象データ:
    - 1月〜12月の料金が月によって異なるデータのみ
    - 全月同じ料金のデータはスキップ

CSVカラム構造:
    1月〜12月: 2ヶ月目以降の料金 (billing_price_*)
    1月入会者〜12月入会者: 初月料金 (enrollment_price_*)
"""
import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

import csv
from decimal import Decimal
from apps.contracts.models import Product, ProductPrice
from apps.tenants.models import Tenant

# CSVファイルパス
CSV_PATH = '/app/T3_契約情報.csv'


def main():
    print("=== ProductPrice 月別料金 インポート（変動データのみ）===")

    # CSVファイル確認
    if not os.path.exists(CSV_PATH):
        print(f"エラー: ファイルが見つかりません: {CSV_PATH}")
        print("ファイルを /tmp/T3_契約情報.csv にコピーしてください")
        return

    # 既存のProductをキャッシュ（product_codeでアクセス）
    products = {p.product_code: p for p in Product.objects.all()}
    print(f"既存Product数: {len(products)}")

    # 既存のProductPriceをキャッシュ
    existing_prices = {pp.product_id: pp for pp in ProductPrice.objects.all()}
    print(f"既存ProductPrice数: {len(existing_prices)}")

    # CSVを読み込み
    updated_count = 0
    created_count = 0
    not_found_count = 0
    skip_same_count = 0  # 月によって料金が同じためスキップ
    error_count = 0

    # 処理した請求IDを記録（重複防止）
    processed_billing_ids = set()

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                billing_id = row.get('請求ID', '').strip()

                if not billing_id:
                    continue

                # 重複スキップ
                if billing_id in processed_billing_ids:
                    continue
                processed_billing_ids.add(billing_id)

                # 月別料金を取得
                billing_values = [
                    row.get('1月', '').strip(),
                    row.get('2月', '').strip(),
                    row.get('3月', '').strip(),
                    row.get('4月', '').strip(),
                    row.get('5月', '').strip(),
                    row.get('6月', '').strip(),
                    row.get('7月', '').strip(),
                    row.get('8月', '').strip(),
                    row.get('9月', '').strip(),
                    row.get('10月', '').strip(),
                    row.get('11月', '').strip(),
                    row.get('12月', '').strip(),
                ]

                enrollment_values = [
                    row.get('1月入会者', '').strip(),
                    row.get('2月入会者', '').strip(),
                    row.get('3月入会者', '').strip(),
                    row.get('4月入会者', '').strip(),
                    row.get('5月入会者', '').strip(),
                    row.get('6月入会者', '').strip(),
                    row.get('7月入会者', '').strip(),
                    row.get('8月入会者', '').strip(),
                    row.get('9月入会者', '').strip(),
                    row.get('10月入会者', '').strip(),
                    row.get('11月入会者', '').strip(),
                    row.get('12月入会者', '').strip(),
                ]

                # 月によって料金が異なるかチェック
                billing_varies = len(set(billing_values)) > 1
                enrollment_varies = len(set(enrollment_values)) > 1

                # 全月同じ料金ならスキップ
                if not billing_varies and not enrollment_varies:
                    skip_same_count += 1
                    continue

                # ProductをProduct_codeで検索
                product = products.get(billing_id)
                if not product:
                    not_found_count += 1
                    if not_found_count <= 10:
                        print(f"  見つからず: {billing_id}")
                    continue

                # 数値に変換
                def to_decimal(val):
                    if not val or val == '':
                        return None
                    try:
                        return Decimal(val)
                    except:
                        return None

                billing_prices = {
                    'jan': row.get('1月', '0').strip(),
                    'feb': row.get('2月', '0').strip(),
                    'mar': row.get('3月', '0').strip(),
                    'apr': row.get('4月', '0').strip(),
                    'may': row.get('5月', '0').strip(),
                    'jun': row.get('6月', '0').strip(),
                    'jul': row.get('7月', '0').strip(),
                    'aug': row.get('8月', '0').strip(),
                    'sep': row.get('9月', '0').strip(),
                    'oct': row.get('10月', '0').strip(),
                    'nov': row.get('11月', '0').strip(),
                    'dec': row.get('12月', '0').strip(),
                }

                enrollment_prices = {
                    'jan': row.get('1月入会者', '0').strip(),
                    'feb': row.get('2月入会者', '0').strip(),
                    'mar': row.get('3月入会者', '0').strip(),
                    'apr': row.get('4月入会者', '0').strip(),
                    'may': row.get('5月入会者', '0').strip(),
                    'jun': row.get('6月入会者', '0').strip(),
                    'jul': row.get('7月入会者', '0').strip(),
                    'aug': row.get('8月入会者', '0').strip(),
                    'sep': row.get('9月入会者', '0').strip(),
                    'oct': row.get('10月入会者', '0').strip(),
                    'nov': row.get('11月入会者', '0').strip(),
                    'dec': row.get('12月入会者', '0').strip(),
                }

                billing_dec = {k: to_decimal(v) for k, v in billing_prices.items()}
                enrollment_dec = {k: to_decimal(v) for k, v in enrollment_prices.items()}

                # ProductPriceを取得または作成
                if product.id in existing_prices:
                    price_obj = existing_prices[product.id]
                    action = "更新"
                else:
                    price_obj = ProductPrice(
                        product=product,
                        tenant_id=product.tenant_id
                    )
                    action = "作成"

                # 請求月別料金を設定（2ヶ月目以降）
                price_obj.billing_price_jan = billing_dec['jan']
                price_obj.billing_price_feb = billing_dec['feb']
                price_obj.billing_price_mar = billing_dec['mar']
                price_obj.billing_price_apr = billing_dec['apr']
                price_obj.billing_price_may = billing_dec['may']
                price_obj.billing_price_jun = billing_dec['jun']
                price_obj.billing_price_jul = billing_dec['jul']
                price_obj.billing_price_aug = billing_dec['aug']
                price_obj.billing_price_sep = billing_dec['sep']
                price_obj.billing_price_oct = billing_dec['oct']
                price_obj.billing_price_nov = billing_dec['nov']
                price_obj.billing_price_dec = billing_dec['dec']

                # 入会月別料金を設定（初月）
                price_obj.enrollment_price_jan = enrollment_dec['jan']
                price_obj.enrollment_price_feb = enrollment_dec['feb']
                price_obj.enrollment_price_mar = enrollment_dec['mar']
                price_obj.enrollment_price_apr = enrollment_dec['apr']
                price_obj.enrollment_price_may = enrollment_dec['may']
                price_obj.enrollment_price_jun = enrollment_dec['jun']
                price_obj.enrollment_price_jul = enrollment_dec['jul']
                price_obj.enrollment_price_aug = enrollment_dec['aug']
                price_obj.enrollment_price_sep = enrollment_dec['sep']
                price_obj.enrollment_price_oct = enrollment_dec['oct']
                price_obj.enrollment_price_nov = enrollment_dec['nov']
                price_obj.enrollment_price_dec = enrollment_dec['dec']

                price_obj.save()

                if action == "更新":
                    updated_count += 1
                else:
                    created_count += 1
                    existing_prices[product.id] = price_obj

                if (updated_count + created_count) <= 20:
                    vary_type = []
                    if billing_varies:
                        vary_type.append('2ヶ月目以降変動')
                    if enrollment_varies:
                        vary_type.append('初月変動')
                    print(f"  {action}: {billing_id} ({'/'.join(vary_type)})")

            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    print(f"  エラー: {e}")

    print(f"\n=== 完了 ===")
    print(f"更新: {updated_count}")
    print(f"新規作成: {created_count}")
    print(f"スキップ（全月同じ料金）: {skip_same_count}")
    print(f"見つからず: {not_found_count}")
    print(f"エラー: {error_count}")

    # 更新後の確認
    print(f"\n=== 更新後の確認 ===")
    print(f"ProductPrice総数: {ProductPrice.objects.count()}")

    # 変動があるデータのサンプル表示
    sample_prices = ProductPrice.objects.exclude(
        billing_price_jan=None
    ).exclude(
        billing_price_apr=None
    )[:5]

    for p in sample_prices:
        jan = p.billing_price_jan or 0
        apr = p.billing_price_apr or 0
        if jan != apr:
            print(f"  {p.product.product_code}: 1月={jan} 4月={apr}")


if __name__ == '__main__':
    main()

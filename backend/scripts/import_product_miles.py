#!/usr/bin/env python
"""
T3_契約情報CSVからProductテーブルのマイル(mile)フィールドを更新するスクリプト

使用方法:
    python manage.py shell < scripts/import_product_miles.py

本番環境:
    docker exec -i oza_backend python manage.py shell < scripts/import_product_miles.py

事前準備:
    CSVファイルを /tmp/T3_契約情報.csv にコピーしてください

変換ルール:
    CSV請求ID: 24AEC_1000007_1
    ↓
    product_code: PAEC10000071

    1. 年度部分(24)を P に置換
    2. アンダースコアを削除
"""
import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

import csv
from decimal import Decimal
from apps.contracts.models import Product
from apps.tenants.models import Tenant

# CSVファイルパス
CSV_PATH = '/tmp/T3_契約情報.csv'


def convert_billing_id_to_product_code(billing_id):
    """
    請求ID（CSV形式）をproduct_code（DB形式）に変換

    例: 24AEC_1000007_1 → PAEC10000071
    """
    if not billing_id:
        return None

    # パターン: 24XXX_NNNNNNN_N
    parts = billing_id.split('_')
    if len(parts) < 3:
        return None

    # 年度部分を除去してPを付加
    brand_code = parts[0]  # 例: 24AEC
    if len(brand_code) >= 3:
        brand_without_year = brand_code[2:]  # AEC
    else:
        return None

    # 数字部分を結合
    contract_num = parts[1]  # 例: 1000007
    billing_num = parts[2]   # 例: 1

    # product_code生成: P + AEC + 1000007 + 1
    product_code = f"P{brand_without_year}{contract_num}{billing_num}"

    return product_code


def main():
    print("=== Product マイル インポート開始 ===")

    # CSVファイル確認
    if not os.path.exists(CSV_PATH):
        print(f"エラー: ファイルが見つかりません: {CSV_PATH}")
        print("ファイルを /tmp/T3_契約情報.csv にコピーしてください")
        return

    # テナント取得
    tenant = Tenant.objects.first()
    if not tenant:
        print("エラー: テナントが見つかりません")
        return
    print(f"テナント: {tenant.name} ({tenant.id})")

    # 既存のProductをキャッシュ（product_codeでアクセス）
    products = {p.product_code: p for p in Product.objects.filter(tenant=tenant)}
    print(f"既存Product数: {len(products)}")

    # CSVを読み込み
    updated_count = 0
    not_found_count = 0
    skip_count = 0
    error_count = 0

    # 処理した請求IDを記録（重複防止）
    processed_billing_ids = set()

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                billing_id = row.get('請求ID', '').strip()
                mile_str = row.get('マイル', '0').strip()

                if not billing_id:
                    continue

                # 重複スキップ
                if billing_id in processed_billing_ids:
                    continue
                processed_billing_ids.add(billing_id)

                # マイルを数値に変換
                try:
                    mile = int(mile_str) if mile_str else 0
                except ValueError:
                    mile = 0

                # マイルが0なら更新不要
                if mile == 0:
                    skip_count += 1
                    continue

                # 請求IDをproduct_codeに変換
                product_code = convert_billing_id_to_product_code(billing_id)
                if not product_code:
                    error_count += 1
                    continue

                # Productを更新
                if product_code in products:
                    product = products[product_code]
                    if product.mile != mile:
                        product.mile = Decimal(mile)
                        product.save(update_fields=['mile'])
                        updated_count += 1
                        if updated_count <= 20:
                            print(f"  更新: {product_code} ({product.product_name}) -> {mile}マイル")
                else:
                    not_found_count += 1
                    if not_found_count <= 10:
                        print(f"  見つからず: {billing_id} -> {product_code}")

            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    print(f"  エラー: {e}")

    print(f"\n=== 完了 ===")
    print(f"更新: {updated_count}")
    print(f"スキップ（マイル=0）: {skip_count}")
    print(f"見つからず: {not_found_count}")
    print(f"エラー: {error_count}")

    # 更新後の確認
    print(f"\n=== 更新後のマイル確認 ===")
    mile_products = Product.objects.filter(tenant=tenant, mile__gt=0)
    print(f"マイル > 0 のProduct数: {mile_products.count()}")
    for p in mile_products[:20]:
        print(f"  {p.product_code}: {p.product_name} -> {p.mile}マイル")


if __name__ == '__main__':
    main()

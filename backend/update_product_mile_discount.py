#!/usr/bin/env python
"""
商品テーブル.xlsx からマイルと割引Maxを更新するスクリプト
"""
import os
import sys
import django

# Djangoセットアップ
sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
from decimal import Decimal
from apps.contracts.models import Product
from apps.tenants.models import Tenant

# Excelファイルパス
EXCEL_PATH = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/商品テーブル.xlsx'


def update_mile_and_discount():
    """Excelからマイルと割引Maxを更新"""
    print("=" * 60)
    print("マイル・割引Max更新開始")
    print("=" * 60)

    # テナント取得
    tenant = Tenant.objects.get(tenant_code='OZA')
    print(f"テナント: {tenant.tenant_name}")

    # Excelファイル読み込み
    print(f"\nExcelファイル読み込み中: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name='Product Export Dec 2 2025 (2)')
    print(f"読み込み完了: {len(df)}行")

    # 更新統計
    updated_count = 0
    not_found_count = 0
    error_count = 0

    for idx, row in df.iterrows():
        try:
            # 商品コード取得
            product_code = str(row.get('商品コード', '')).strip()
            if not product_code or product_code == 'nan':
                continue

            # マイル取得
            mile_raw = row.get('マイル付与', 0)
            if pd.isna(mile_raw):
                mile = Decimal('0')
            else:
                try:
                    mile = Decimal(str(int(float(mile_raw))))
                except (ValueError, TypeError):
                    mile = Decimal('0')

            # 割引Max取得
            discount_max_raw = row.get('割引MAX(%)', 0)
            if pd.isna(discount_max_raw):
                discount_max = Decimal('0')
            else:
                try:
                    discount_max = Decimal(str(int(float(discount_max_raw))))
                except (ValueError, TypeError):
                    discount_max = Decimal('0')

            # 商品を検索して更新
            try:
                product = Product.objects.get(
                    tenant_id=tenant.id,
                    product_code=product_code
                )
                product.mile = mile
                product.discount_max = discount_max
                product.save()
                updated_count += 1
                if mile > 0 or discount_max > 0:
                    print(f"✅ 更新: {product_code} - マイル:{mile}, 割引Max:{discount_max}%")
            except Product.DoesNotExist:
                not_found_count += 1

        except Exception as e:
            error_count += 1
            print(f"❌ エラー (行{idx}): {e}")

    print("\n" + "=" * 60)
    print("更新完了")
    print("=" * 60)
    print(f"更新: {updated_count}件")
    print(f"未検出: {not_found_count}件")
    print(f"エラー: {error_count}件")

    # 確認：マイルまたは割引Maxが設定されている商品
    products_with_mile = Product.objects.filter(tenant_id=tenant.id, mile__gt=0).count()
    products_with_discount = Product.objects.filter(tenant_id=tenant.id, discount_max__gt=0).count()
    print(f"\nマイル設定あり: {products_with_mile}件")
    print(f"割引Max設定あり: {products_with_discount}件")


if __name__ == '__main__':
    update_mile_and_discount()

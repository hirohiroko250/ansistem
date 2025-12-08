#!/usr/bin/env python
"""
商品テーブル.xlsx からProductデータをインポートするスクリプト
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
from apps.schools.models import Brand
from apps.tenants.models import Tenant

# Excelファイルパス
EXCEL_PATH = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/商品テーブル.xlsx'

# item_type マッピング
ITEM_TYPE_MAP = {
    '授業料': 'tuition',
    '月会費': 'monthly_fee',
    '設備費': 'facility',
    '教材費': 'textbook',
    '諸経費': 'expense',
    '入会金': 'enrollment',
    '入会時授業料A': 'tuition',
    '入会時授業料B': 'tuition',
    '入会時授業料C': 'tuition',
    'その他': 'other',
}

# ブランドコードマッピング
BRAND_CODE_MAP = {
    'AEC': 'AEC',  # アンイングリッシュクラブ
    'SOR': 'SOR',  # そろばん（仮）
}


def get_or_create_tenant():
    """デフォルトテナントを取得または作成"""
    tenant, created = Tenant.objects.get_or_create(
        tenant_code='OZA',
        defaults={
            'tenant_name': 'おざシステム',
            'tenant_type': 'standalone',
            'is_active': True,
        }
    )
    if created:
        print(f"テナントを作成しました: {tenant.tenant_name}")
    return tenant


def get_or_create_brand(brand_code, tenant):
    """ブランドを取得または作成"""
    brand_names = {
        'AEC': 'アンイングリッシュクラブ',
        'SOR': 'そろばん',
    }

    brand, created = Brand.objects.get_or_create(
        tenant_id=tenant.id,
        brand_code=brand_code,
        defaults={
            'brand_name': brand_names.get(brand_code, brand_code),
            'brand_name_short': brand_code,
            'is_active': True,
        }
    )
    if created:
        print(f"ブランドを作成しました: {brand.brand_name}")
    return brand


def import_products():
    """Excelからproductデータをインポート"""
    print("=" * 60)
    print("商品データインポート開始")
    print("=" * 60)

    # テナント取得
    tenant = get_or_create_tenant()
    print(f"テナント: {tenant.tenant_name} (ID: {tenant.id})")

    # Excelファイル読み込み
    print(f"\nExcelファイル読み込み中: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name='Product Export Dec 2 2025 (2)')
    print(f"読み込み完了: {len(df)}行")

    # カラム名確認
    print(f"\nカラム: {list(df.columns)}")

    # インポート統計
    created_count = 0
    updated_count = 0
    error_count = 0

    for idx, row in df.iterrows():
        try:
            # Excelのカラム名に対応
            product_code = str(row.get('商品コード', '')).strip()
            if not product_code or product_code == 'nan':
                continue

            product_name = str(row.get('商品名', '')).strip()
            if not product_name or product_name == 'nan':
                continue

            # ブランド取得
            brand_code = str(row.get('ブランドコード', '')).strip()
            brand = None
            if brand_code and brand_code != 'nan':
                brand = get_or_create_brand(brand_code, tenant)

            # item_type変換
            item_type_raw = str(row.get('商品種別', '')).strip()
            item_type = ITEM_TYPE_MAP.get(item_type_raw, 'other')

            # 価格
            base_price = row.get('基本価格', 0)
            if pd.isna(base_price):
                base_price = 0
            try:
                base_price = Decimal(str(int(float(base_price))))
            except (ValueError, TypeError):
                base_price = Decimal('0')

            # 税率
            tax_rate = row.get('税率', 0.10)
            if pd.isna(tax_rate):
                tax_rate = 0.10
            tax_rate = Decimal(str(tax_rate))

            # 税込フラグ
            is_tax_included = row.get('税込', True)
            if pd.isna(is_tax_included):
                is_tax_included = True
            is_tax_included = bool(is_tax_included)

            # 一回きりフラグ（カラム名に対応）
            is_one_time = row.get('一回きり・・・設備費をカルチャーか、塾か', False)
            if pd.isna(is_one_time):
                is_one_time = False
            is_one_time = bool(is_one_time)

            # 商品名略称
            product_name_short = str(row.get('商品名略称', '')).strip()
            if product_name_short == 'nan':
                product_name_short = ''

            # 説明
            description = str(row.get('説明', '')).strip()
            if description == 'nan':
                description = ''

            # 商品作成または更新
            product, created = Product.objects.update_or_create(
                tenant_id=tenant.id,
                product_code=product_code,
                defaults={
                    'product_name': product_name,
                    'product_name_short': product_name_short,
                    'item_type': item_type,
                    'brand': brand,
                    'base_price': base_price,
                    'tax_rate': tax_rate,
                    'is_tax_included': is_tax_included,
                    'is_one_time': is_one_time,
                    'description': description,
                    'is_active': True,
                }
            )

            if created:
                created_count += 1
                print(f"✅ 作成: {product_code} - {product_name}")
            else:
                updated_count += 1
                print(f"🔄 更新: {product_code} - {product_name}")

        except Exception as e:
            error_count += 1
            print(f"❌ エラー (行{idx}): {e}")

    print("\n" + "=" * 60)
    print("インポート完了")
    print("=" * 60)
    print(f"作成: {created_count}件")
    print(f"更新: {updated_count}件")
    print(f"エラー: {error_count}件")
    print(f"合計: {Product.objects.filter(tenant_id=tenant.id).count()}件")

    return created_count, updated_count, error_count


if __name__ == '__main__':
    import_products()

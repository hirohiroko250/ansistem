#!/usr/bin/env python
"""
商品テーブル.xlsx から各テーブルにデータを振り分けてインポート

振り分けルール:
- Product: 通常商品（授業料、月会費、設備費、教材費、入会金、諸経費、その他物品）
- Seminar: 講習会関連
- Certification: 検定関連
"""
import os
import sys
import django

sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
from decimal import Decimal
from apps.contracts.models import Product, Seminar, Certification
from apps.schools.models import Brand
from apps.tenants.models import Tenant

EXCEL_PATH = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/商品テーブル.xlsx'

# =====================================================
# 振り分けルール
# =====================================================

# Product用の商品種別マッピング
PRODUCT_TYPE_MAP = {
    # 授業料系
    '授業料': 'tuition',
    '入会時授業料A': 'tuition',
    '入会時授業料1': 'tuition',
    '入会時授業料2': 'tuition',
    '入会時授業料3': 'tuition',
    '追加授業料': 'tuition',
    # 月会費系
    '月会費': 'monthly_fee',
    '入会時月会費': 'monthly_fee',
    # 設備費系
    '設備費': 'facility',
    '入会時設備費': 'facility',
    # 教材費系
    '教材費': 'textbook',
    '入会時教材費': 'textbook',
    '教材費1': 'textbook',
    # 入会金
    '入会金': 'enrollment',
    # 諸経費系
    '諸経費': 'expense',
    '入会時諸経費': 'expense',
    '総合指導管理費': 'expense',
    '入会時総合指導管理費': 'expense',
    # その他物品
    'バッグ': 'other',
    'そろばん本体代': 'other',
    'おやつ': 'other',
    'お弁当': 'other',
    '送迎費': 'other',
    '預り料': 'other',
    '保育回数券': 'other',
    '講師指名料': 'other',
    '家賃': 'other',
}

# Seminar用（講習会関連）
SEMINAR_TYPES = {
    '講習会': 'other',
    '必須講習会': 'other',
    '春期講習会': 'spring',
    '夏期講習会': 'summer',
    '冬期講習会': 'winter',
    '必須講座': 'special',
    'テスト対策費': 'special',
    '必須テスト対策費': 'special',
    '必須入試対策費': 'special',
    '模試代': 'special',
    '必須模試代': 'special',
}

# Certification用（検定関連）
CERTIFICATION_TYPES = {
    '検定料1': 'other',
    '検定料2': 'other',
    '検定料3': 'other',
    '検定料4': 'other',
}


def get_tenant():
    """テナントを取得"""
    return Tenant.objects.get(tenant_code='OZA')


def get_or_create_brand(brand_code, tenant):
    """ブランドを取得または作成"""
    if not brand_code or brand_code == 'nan':
        return None

    brand, created = Brand.objects.get_or_create(
        tenant_id=tenant.id,
        brand_code=brand_code,
        defaults={
            'brand_name': brand_code,
            'brand_name_short': brand_code,
            'is_active': True,
        }
    )
    if created:
        print(f"  ブランド作成: {brand_code}")
    return brand


def import_products(df, tenant):
    """通常商品をインポート"""
    print("\n=== Product インポート ===")

    # 対象行をフィルタ
    target_types = set(PRODUCT_TYPE_MAP.keys())
    mask = df['商品種別'].isin(target_types)
    product_df = df[mask]
    print(f"対象件数: {len(product_df)}")

    created = 0
    updated = 0
    errors = 0

    for idx, row in product_df.iterrows():
        try:
            product_code = str(row.get('商品コード', '')).strip()
            if not product_code or product_code == 'nan':
                continue

            product_name = str(row.get('商品名', '')).strip()
            if not product_name or product_name == 'nan':
                continue

            brand_code = str(row.get('ブランドコード', '')).strip()
            brand = get_or_create_brand(brand_code, tenant) if brand_code != 'nan' else None

            item_type_raw = str(row.get('商品種別', '')).strip()
            item_type = PRODUCT_TYPE_MAP.get(item_type_raw, 'other')

            base_price = row.get('基本価格', 0)
            if pd.isna(base_price):
                base_price = 0
            try:
                base_price = Decimal(str(int(float(base_price))))
            except:
                base_price = Decimal('0')

            tax_rate = row.get('税率', 0.10)
            if pd.isna(tax_rate):
                tax_rate = 0.10

            is_tax_included = row.get('税込', True)
            if pd.isna(is_tax_included):
                is_tax_included = True

            is_one_time = item_type in ['enrollment', 'textbook'] or '入会時' in item_type_raw

            product_name_short = str(row.get('商品名略称', '')).strip()
            if product_name_short == 'nan':
                product_name_short = ''

            description = str(row.get('説明', '')).strip()
            if description == 'nan':
                description = ''

            product, is_created = Product.objects.update_or_create(
                tenant_id=tenant.id,
                product_code=product_code,
                defaults={
                    'product_name': product_name,
                    'product_name_short': product_name_short,
                    'item_type': item_type,
                    'brand': brand,
                    'base_price': base_price,
                    'tax_rate': Decimal(str(tax_rate)),
                    'is_tax_included': bool(is_tax_included),
                    'is_one_time': is_one_time,
                    'description': description,
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
                print(f"  エラー: {e}")

    print(f"  作成: {created}, 更新: {updated}, エラー: {errors}")
    return created, updated, errors


def import_seminars(df, tenant):
    """講習会をインポート"""
    print("\n=== Seminar インポート ===")

    target_types = set(SEMINAR_TYPES.keys())
    mask = df['商品種別'].isin(target_types)
    seminar_df = df[mask]
    print(f"対象件数: {len(seminar_df)}")

    created = 0
    updated = 0
    errors = 0

    for idx, row in seminar_df.iterrows():
        try:
            seminar_code = str(row.get('商品コード', '')).strip()
            if not seminar_code or seminar_code == 'nan':
                continue

            seminar_name = str(row.get('商品名', '')).strip()
            if not seminar_name or seminar_name == 'nan':
                continue

            brand_code = str(row.get('ブランドコード', '')).strip()
            brand = get_or_create_brand(brand_code, tenant) if brand_code != 'nan' else None

            item_type_raw = str(row.get('商品種別', '')).strip()
            seminar_type = SEMINAR_TYPES.get(item_type_raw, 'other')

            base_price = row.get('基本価格', 0)
            if pd.isna(base_price):
                base_price = 0
            try:
                base_price = Decimal(str(int(float(base_price))))
            except:
                base_price = Decimal('0')

            description = str(row.get('説明', '')).strip()
            if description == 'nan':
                description = ''

            seminar, is_created = Seminar.objects.update_or_create(
                tenant_id=tenant.id,
                seminar_code=seminar_code,
                defaults={
                    'seminar_name': seminar_name,
                    'seminar_type': seminar_type,
                    'brand': brand,
                    'year': 2024,  # デフォルト年度
                    'base_price': base_price,
                    'description': description,
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
                print(f"  エラー: {e}")

    print(f"  作成: {created}, 更新: {updated}, エラー: {errors}")
    return created, updated, errors


def import_certifications(df, tenant):
    """検定をインポート"""
    print("\n=== Certification インポート ===")

    target_types = set(CERTIFICATION_TYPES.keys())
    mask = df['商品種別'].isin(target_types)
    cert_df = df[mask]
    print(f"対象件数: {len(cert_df)}")

    created = 0
    updated = 0
    errors = 0

    for idx, row in cert_df.iterrows():
        try:
            cert_code = str(row.get('商品コード', '')).strip()
            if not cert_code or cert_code == 'nan':
                continue

            cert_name = str(row.get('商品名', '')).strip()
            if not cert_name or cert_name == 'nan':
                continue

            brand_code = str(row.get('ブランドコード', '')).strip()
            brand = get_or_create_brand(brand_code, tenant) if brand_code != 'nan' else None

            exam_fee = row.get('基本価格', 0)
            if pd.isna(exam_fee):
                exam_fee = 0
            try:
                exam_fee = Decimal(str(int(float(exam_fee))))
            except:
                exam_fee = Decimal('0')

            description = str(row.get('説明', '')).strip()
            if description == 'nan':
                description = ''

            cert, is_created = Certification.objects.update_or_create(
                tenant_id=tenant.id,
                certification_code=cert_code,
                defaults={
                    'certification_name': cert_name,
                    'certification_type': 'other',
                    'brand': brand,
                    'year': 2024,
                    'exam_fee': exam_fee,
                    'description': description,
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
                print(f"  エラー: {e}")

    print(f"  作成: {created}, 更新: {updated}, エラー: {errors}")
    return created, updated, errors


def main():
    print("=" * 60)
    print("データインポート開始")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    print(f"\nExcel読み込み中: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name='Product Export Dec 2 2025 (2)')
    print(f"全{len(df)}行")

    # 各テーブルにインポート
    p_created, p_updated, p_errors = import_products(df, tenant)
    s_created, s_updated, s_errors = import_seminars(df, tenant)
    c_created, c_updated, c_errors = import_certifications(df, tenant)

    # 集計
    print("\n" + "=" * 60)
    print("インポート完了")
    print("=" * 60)
    print(f"Product:       {Product.objects.filter(tenant_id=tenant.id).count()}件")
    print(f"Seminar:       {Seminar.objects.filter(tenant_id=tenant.id).count()}件")
    print(f"Certification: {Certification.objects.filter(tenant_id=tenant.id).count()}件")

    # 未分類の件数
    all_types = set(PRODUCT_TYPE_MAP.keys()) | set(SEMINAR_TYPES.keys()) | set(CERTIFICATION_TYPES.keys())
    unclassified = df[~df['商品種別'].isin(all_types)]
    if len(unclassified) > 0:
        print(f"\n未分類: {len(unclassified)}件")
        print("未分類の商品種別:")
        for t in unclassified['商品種別'].unique():
            if pd.notna(t):
                print(f"  - {t}")


if __name__ == '__main__':
    main()

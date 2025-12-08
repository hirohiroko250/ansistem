#!/usr/bin/env python
"""
T3（契約情報）CSVインポートスクリプト - 請求ID単位版

請求IDを商品コードとしてProductを作成し、
契約ID→請求IDの親子関係をT52（ProductComposition）に作成する
"""
import os
import sys
import csv
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import transaction
from apps.contracts.models import Product, ProductComposition
from apps.schools.models import Brand

# テナントID（デフォルト）
DEFAULT_TENANT_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')


def parse_decimal(value, default=Decimal('0')):
    """数値をDecimalに変換"""
    if not value:
        return default
    try:
        value = str(value).replace(',', '')
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return default


def parse_int(value, default=0):
    """数値をintに変換"""
    if not value:
        return default
    try:
        return int(float(str(value).replace(',', '')))
    except (ValueError, TypeError):
        return default


def get_or_create_brand(brand_code, brand_name, tenant_id):
    """ブランドを取得または作成"""
    if not brand_code and not brand_name:
        return None

    if brand_code:
        brand = Brand.objects.filter(tenant_id=tenant_id, brand_code=brand_code).first()
        if brand:
            return brand

    if brand_name:
        brand = Brand.objects.filter(tenant_id=tenant_id, brand_name=brand_name).first()
        if brand:
            return brand

    code = brand_code or brand_name[:20].replace(' ', '_')
    name = brand_name or brand_code

    brand, created = Brand.objects.get_or_create(
        tenant_id=tenant_id,
        brand_code=code,
        defaults={
            'brand_name': name,
            'is_active': True
        }
    )
    return brand


def get_product_type(category_name, contract_name=''):
    """請求カテゴリ名から商品種別を判定"""
    if '設備費' in category_name:
        return 'facility'
    elif '教材費' in category_name or '教材' in category_name:
        return 'material'
    elif '入会金' in category_name:
        return 'other'
    elif '月会費' in category_name:
        return 'other'
    elif '授業料' in category_name:
        if '講習' in contract_name:
            return 'seasonal'
        return 'regular'
    elif 'バッグ' in category_name:
        return 'material'
    else:
        return 'other'


def get_billing_type(category_code):
    """請求カテゴリ区分から課金種別を判定"""
    # 1=月額, 6=一括 etc
    if category_code == '1':
        return 'monthly'
    elif category_code == '6':
        return 'one_time'
    else:
        return 'monthly'


def import_t3_by_billing_id(csv_path, tenant_id=DEFAULT_TENANT_ID):
    """T3 CSVを請求ID単位でインポート"""

    print(f"Importing T3 data (by billing ID) from: {csv_path}")
    print(f"Tenant ID: {tenant_id}")

    stats = {
        'total_rows': 0,
        'products_created': 0,
        'products_updated': 0,
        'parent_products_created': 0,
        'compositions_created': 0,
        'compositions_updated': 0,
        'skipped': 0,
        'errors': []
    }

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total rows to process: {len(rows)}")

    # 契約IDでグループ化（親商品と子商品の関係を把握）
    contract_groups = {}  # contract_id -> list of billing rows
    for row in rows:
        contract_id = row.get('契約ID', '')
        if not contract_id:
            continue
        if contract_id not in contract_groups:
            contract_groups[contract_id] = []
        contract_groups[contract_id].append(row)

    print(f"Contract groups (parent products): {len(contract_groups)}")

    with transaction.atomic():
        # Phase 1: 全ての請求IDを商品として作成
        print("\n=== Phase 1: Creating Products by Billing ID ===")

        product_cache = {}  # billing_id -> Product

        for row in rows:
            stats['total_rows'] += 1

            if stats['total_rows'] % 5000 == 0:
                print(f"  Processing row {stats['total_rows']}...")

            try:
                billing_id = row.get('請求ID', '')
                contract_id = row.get('契約ID', '')
                contract_name = row.get('契約名', '')
                category_name = row.get('請求カテゴリ名', '')

                if not billing_id:
                    stats['skipped'] += 1
                    continue

                # ブランド情報
                brand_code = row.get('契約ブランド記号', '')
                brand_name = row.get('契約ブランド名', '') or row.get('Class用ブランド名', '')
                brand = get_or_create_brand(brand_code, brand_name, tenant_id)

                # 商品名を決定
                # 明細表記があればそれを使用、なければ契約名＋カテゴリ名
                detail_name = row.get('明細表記', '')
                if detail_name:
                    product_name = detail_name
                else:
                    product_name = f"{contract_name}【{category_name}】" if category_name else contract_name

                # 価格情報
                unit_price = parse_decimal(row.get('単価', '0'))
                mile = parse_int(row.get('マイル', '0'))
                max_discount = parse_decimal(row.get('割引MAX(%)', '0'))

                # 商品種別
                product_type = get_product_type(category_name, contract_name)

                # 課金種別
                billing_category = row.get('請求カテゴリ区分', '')
                billing_type = get_billing_type(billing_category)

                # 商品を作成または更新
                product, created = Product.objects.update_or_create(
                    tenant_id=tenant_id,
                    product_code=billing_id,
                    defaults={
                        'product_name': product_name[:100],
                        'product_name_short': row.get('逆引き保護者用表記', '')[:50] if row.get('逆引き保護者用表記') else '',
                        'product_type': product_type,
                        'billing_type': billing_type,
                        'brand': brand,
                        'base_price': unit_price,
                        'mile': mile,
                        'max_discount_rate': max_discount,
                        'is_active': row.get('有効・無効', '1') == '1',
                        'description': category_name,  # カテゴリ名を説明に保存
                    }
                )

                product_cache[billing_id] = product

                if created:
                    stats['products_created'] += 1
                else:
                    stats['products_updated'] += 1

            except Exception as e:
                stats['errors'].append({
                    'row': stats['total_rows'],
                    'billing_id': billing_id,
                    'error': str(e)
                })

        print(f"Products created: {stats['products_created']}")
        print(f"Products updated: {stats['products_updated']}")

        # Phase 2: 親商品（契約ID）を作成
        print("\n=== Phase 2: Creating Parent Products (Contract ID) ===")

        parent_product_cache = {}  # contract_id -> Product

        for contract_id, billing_rows in contract_groups.items():
            try:
                # 親商品がまだない場合は作成
                # 請求番号1のデータを代表として使用
                representative_row = None
                for r in billing_rows:
                    if r.get('請求番号', '') == '1':
                        representative_row = r
                        break
                if not representative_row:
                    representative_row = billing_rows[0]

                # ブランド情報
                brand_code = representative_row.get('契約ブランド記号', '')
                brand_name = representative_row.get('契約ブランド名', '') or representative_row.get('Class用ブランド名', '')
                brand = get_or_create_brand(brand_code, brand_name, tenant_id)

                contract_name = representative_row.get('契約名', '')

                # 親商品を作成または更新
                parent_product, created = Product.objects.update_or_create(
                    tenant_id=tenant_id,
                    product_code=contract_id,
                    defaults={
                        'product_name': contract_name[:100] if contract_name else contract_id,
                        'product_name_short': contract_name[:50] if contract_name else '',
                        'product_type': 'regular',
                        'billing_type': 'monthly',
                        'brand': brand,
                        'base_price': 0,  # 親商品の価格は子商品の合計
                        'is_active': representative_row.get('有効・無効', '1') == '1',
                        'description': f"パック商品（{len(billing_rows)}個の費目を含む）",
                    }
                )

                parent_product_cache[contract_id] = parent_product

                if created:
                    stats['parent_products_created'] += 1

            except Exception as e:
                stats['errors'].append({
                    'type': 'parent_product',
                    'contract_id': contract_id,
                    'error': str(e)
                })

        print(f"Parent products created: {stats['parent_products_created']}")

        # Phase 3: T52（ProductComposition）親子関係を作成
        print("\n=== Phase 3: Creating T52 ProductComposition (Parent-Child Relations) ===")

        for contract_id, billing_rows in contract_groups.items():
            parent_product = parent_product_cache.get(contract_id)
            if not parent_product:
                continue

            sort_order = 0
            for row in sorted(billing_rows, key=lambda x: parse_int(x.get('請求番号', '0'))):
                billing_id = row.get('請求ID', '')
                child_product = product_cache.get(billing_id)

                if not child_product:
                    continue

                # 親と子が同じ場合はスキップ
                if parent_product.id == child_product.id:
                    continue

                sort_order += 1

                try:
                    composition, created = ProductComposition.objects.update_or_create(
                        tenant_id=tenant_id,
                        parent_product=parent_product,
                        child_product=child_product,
                        defaults={
                            'quantity': 1,
                            'sort_order': sort_order,
                            'is_active': True,
                            'notes': row.get('請求カテゴリ名', ''),
                        }
                    )

                    if created:
                        stats['compositions_created'] += 1
                    else:
                        stats['compositions_updated'] += 1

                except Exception as e:
                    stats['errors'].append({
                        'type': 'composition',
                        'parent': contract_id,
                        'child': billing_id,
                        'error': str(e)
                    })

        print(f"Compositions created: {stats['compositions_created']}")
        print(f"Compositions updated: {stats['compositions_updated']}")

    # 結果表示
    print("\n" + "=" * 50)
    print("Import Complete!")
    print("=" * 50)
    print(f"Total rows processed: {stats['total_rows']}")
    print(f"Products created (billing ID): {stats['products_created']}")
    print(f"Products updated (billing ID): {stats['products_updated']}")
    print(f"Parent products created (contract ID): {stats['parent_products_created']}")
    print(f"T52 Compositions created: {stats['compositions_created']}")
    print(f"T52 Compositions updated: {stats['compositions_updated']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {len(stats['errors'])}")

    if stats['errors']:
        print("\nFirst 10 errors:")
        for err in stats['errors'][:10]:
            print(f"  - {err}")

    return stats


if __name__ == '__main__':
    csv_path = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/T3_契約情報_202511272049_UTF8.csv'

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]

    import_t3_by_billing_id(csv_path)

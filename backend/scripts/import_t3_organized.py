#!/usr/bin/env python
"""
T3（契約情報）CSVインポートスクリプト - 整理版

契約IDを商品として登録し、
- T52: 月額費用の内訳（授業料、月会費、設備費）
- T5: 入会時費用（入会金、入会時授業料、バッグなど）
に振り分ける
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

from django.db import transaction, connection
from apps.contracts.models import Product, ProductComposition
from apps.schools.models import Brand

# テナントID（デフォルト）
DEFAULT_TENANT_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')

# 月額費用カテゴリ
MONTHLY_CATEGORIES = {
    '授業料', '月会費', '設備費', '総合指導管理費', '諸経費'
}

# 入会時費用カテゴリとその種別マッピング
INITIAL_FEE_CATEGORIES = {
    '入会金': 'enrollment',
    '入会時授業料A': 'initial_tuition',
    '入会時授業料1': 'initial_tuition',
    '入会時授業料2': 'initial_tuition',
    '入会時授業料3': 'initial_tuition',
    '入会時月会費': 'initial_monthly',
    '入会時設備費': 'initial_facility',
    '入会時教材費': 'initial_material',
    '入会時諸経費': 'initial_misc',
    '入会時総合指導管理費': 'initial_misc',
    'バッグ': 'bag',
    'そろばん本体代': 'equipment',
}


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
    """カテゴリから商品種別を判定"""
    if '講習' in contract_name or '講習' in category_name:
        return 'seasonal'
    elif '検定' in category_name or 'テスト' in category_name or '模試' in category_name:
        return 'special'
    else:
        return 'regular'


def import_t3_organized(csv_path, tenant_id=DEFAULT_TENANT_ID):
    """T3 CSVを整理してインポート"""

    print(f"Importing T3 data (organized) from: {csv_path}")
    print(f"Tenant ID: {tenant_id}")

    stats = {
        'total_rows': 0,
        'products_created': 0,
        'compositions_created': 0,
        'initial_fees_created': 0,
        'skipped': 0,
        'errors': []
    }

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total rows to process: {len(rows)}")

    # 契約IDでグループ化
    contract_groups = {}
    for row in rows:
        contract_id = row.get('契約ID', '')
        if not contract_id:
            continue
        if contract_id not in contract_groups:
            contract_groups[contract_id] = []
        contract_groups[contract_id].append(row)

    print(f"Contract groups (products): {len(contract_groups)}")

    with transaction.atomic():
        # Phase 1: 商品マスタ（契約ID単位）を作成
        print("\n=== Phase 1: Creating Products (by Contract ID) ===")

        product_cache = {}
        now = datetime.now()

        for contract_id, billing_rows in contract_groups.items():
            try:
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
                category_name = representative_row.get('請求カテゴリ名', '')

                # 商品種別
                product_type = get_product_type(category_name, contract_name)

                # 商品を作成
                product, created = Product.objects.update_or_create(
                    tenant_id=tenant_id,
                    product_code=contract_id,
                    defaults={
                        'product_name': contract_name[:100] if contract_name else contract_id,
                        'product_name_short': contract_name[:50] if contract_name else '',
                        'product_type': product_type,
                        'billing_type': 'monthly',
                        'brand': brand,
                        'base_price': 0,
                        'is_active': representative_row.get('有効・無効', '1') == '1',
                        'description': '',
                    }
                )

                product_cache[contract_id] = product

                if created:
                    stats['products_created'] += 1

            except Exception as e:
                stats['errors'].append({
                    'type': 'product',
                    'contract_id': contract_id,
                    'error': str(e)
                })

        print(f"Products created: {stats['products_created']}")

        # Phase 2: T52（月額内訳）とT5（入会時費用）を作成
        print("\n=== Phase 2: Creating T52 (Monthly) and T5 (Initial Fees) ===")

        for contract_id, billing_rows in contract_groups.items():
            product = product_cache.get(contract_id)
            if not product:
                continue

            monthly_total = Decimal('0')
            sort_order = 0

            for row in sorted(billing_rows, key=lambda x: parse_int(x.get('請求番号', '0'))):
                stats['total_rows'] += 1
                category_name = row.get('請求カテゴリ名', '')
                billing_id = row.get('請求ID', '')
                billing_number = parse_int(row.get('請求番号', '0'))
                amount = parse_decimal(row.get('単価', '0'))
                max_discount = parse_decimal(row.get('割引MAX(%)', '0'))
                detail_name = row.get('明細表記', '') or row.get('逆引き保護者用表記', '')

                if not category_name:
                    stats['skipped'] += 1
                    continue

                # 月額費用カテゴリ → T52
                if category_name in MONTHLY_CATEGORIES:
                    sort_order += 1

                    # 子商品を作成（または取得）
                    child_product, _ = Product.objects.update_or_create(
                        tenant_id=tenant_id,
                        product_code=billing_id,
                        defaults={
                            'product_name': detail_name[:100] if detail_name else f"{contract_id} {category_name}",
                            'product_type': 'facility' if '設備費' in category_name else 'other',
                            'billing_type': 'monthly',
                            'brand': product.brand,
                            'base_price': amount,
                            'is_active': True,
                            'description': category_name,
                        }
                    )

                    # T52 ProductComposition
                    try:
                        composition, created = ProductComposition.objects.update_or_create(
                            tenant_id=tenant_id,
                            parent_product=product,
                            child_product=child_product,
                            defaults={
                                'quantity': 1,
                                'sort_order': sort_order,
                                'is_active': True,
                                'notes': category_name,
                            }
                        )
                        if created:
                            stats['compositions_created'] += 1

                        monthly_total += amount
                    except Exception as e:
                        stats['errors'].append({
                            'type': 'composition',
                            'billing_id': billing_id,
                            'error': str(e)
                        })

                # 入会時費用カテゴリ → T5
                elif category_name in INITIAL_FEE_CATEGORIES:
                    fee_type = INITIAL_FEE_CATEGORIES.get(category_name, 'other')

                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(
                                'INSERT OR REPLACE INTO t05_initial_fees '
                                '(id, tenant_id, product_id, fee_code, fee_name, fee_type, '
                                'amount, max_discount_rate, billing_number, is_required, is_active, notes, '
                                'created_at, updated_at) '
                                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                                [
                                    str(uuid.uuid4()),
                                    str(tenant_id),
                                    str(product.id),
                                    billing_id,
                                    detail_name[:100] if detail_name else category_name,
                                    fee_type,
                                    int(amount),
                                    float(max_discount),
                                    billing_number,
                                    1,  # is_required
                                    1,  # is_active
                                    category_name,
                                    now,
                                    now,
                                ]
                            )
                        stats['initial_fees_created'] += 1
                    except Exception as e:
                        stats['errors'].append({
                            'type': 'initial_fee',
                            'billing_id': billing_id,
                            'error': str(e)
                        })

                # その他のカテゴリはスキップ（講習会、検定料など）
                else:
                    stats['skipped'] += 1

            # 商品の基本価格を月額合計で更新
            if monthly_total > 0:
                product.base_price = monthly_total
                product.save()

        print(f"T52 Compositions created: {stats['compositions_created']}")
        print(f"T5 Initial fees created: {stats['initial_fees_created']}")

    # 結果表示
    print("\n" + "=" * 50)
    print("Import Complete!")
    print("=" * 50)
    print(f"Total rows processed: {stats['total_rows']}")
    print(f"Products created (contract ID): {stats['products_created']}")
    print(f"T52 Compositions created (monthly fees): {stats['compositions_created']}")
    print(f"T5 Initial fees created: {stats['initial_fees_created']}")
    print(f"Skipped (other categories): {stats['skipped']}")
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

    import_t3_organized(csv_path)

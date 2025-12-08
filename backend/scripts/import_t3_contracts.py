#!/usr/bin/env python
"""
T3（契約情報）CSVインポートスクリプト

契約マスタデータをインポートし、T51パック組み合わせ情報も作成
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
from apps.contracts.models import Contract, Product, ContractPack
from apps.schools.models import Brand, School, Subject, Grade

# テナントID（デフォルト）
DEFAULT_TENANT_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')


def parse_date(date_str):
    """日付文字列をパース"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y/%m/%d').date()
    except ValueError:
        return None


def parse_decimal(value, default=Decimal('0')):
    """数値をDecimalに変換"""
    if not value:
        return default
    try:
        # カンマを除去
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

    # まずコードで検索
    if brand_code:
        brand = Brand.objects.filter(tenant_id=tenant_id, brand_code=brand_code).first()
        if brand:
            return brand

    # 名前で検索
    if brand_name:
        brand = Brand.objects.filter(tenant_id=tenant_id, brand_name=brand_name).first()
        if brand:
            return brand

    # 新規作成
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
    if created:
        print(f"  Created brand: {name}")
    return brand


def import_t3_csv(csv_path, tenant_id=DEFAULT_TENANT_ID):
    """T3 CSVをインポート"""

    print(f"Importing T3 data from: {csv_path}")
    print(f"Tenant ID: {tenant_id}")

    stats = {
        'total_rows': 0,
        'products_created': 0,
        'products_updated': 0,
        'brands_created': 0,
        'pack_relations': 0,
        'skipped': 0,
        'errors': []
    }

    # 契約IDとブランドコードのマッピング
    contract_brand_map = {}  # contract_id -> brand_code
    pack_relations = []  # (contract_id, required_brand_code)

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total rows to process: {len(rows)}")

    with transaction.atomic():
        # 第1パス: 商品とブランドの作成
        print("\n=== Phase 1: Creating Products ===")

        for row in rows:
            stats['total_rows'] += 1

            if stats['total_rows'] % 5000 == 0:
                print(f"  Processing row {stats['total_rows']}...")

            try:
                contract_id = row.get('契約ID', '')
                if not contract_id:
                    stats['skipped'] += 1
                    continue

                # ブランド情報
                brand_code = row.get('契約ブランド記号', '')
                brand_name = row.get('契約ブランド名', '') or row.get('Class用ブランド名', '')
                brand = get_or_create_brand(brand_code, brand_name, tenant_id)

                # 契約IDとブランドコードのマッピングを保存
                if brand_code:
                    contract_brand_map[contract_id] = brand_code

                # パック関連を記録
                required_id = row.get('必要契約ID', '')
                if required_id:
                    pack_relations.append((contract_id, required_id))

                # 商品情報
                contract_name = row.get('契約名', '')
                if not contract_name:
                    stats['skipped'] += 1
                    continue

                # 価格情報
                unit_price = parse_decimal(row.get('単価', '0'))
                mile = parse_int(row.get('マイル', '0'))
                max_discount = parse_decimal(row.get('割引MAX(%)', '0'))

                # 商品種別を判定
                category = row.get('請求カテゴリ名', '')
                if '設備費' in category:
                    product_type = 'facility'
                elif '教材' in category:
                    product_type = 'material'
                elif '講習' in contract_name:
                    product_type = 'seasonal'
                else:
                    product_type = 'regular'

                # 課金種別
                billing_category = row.get('請求カテゴリ区分', '')
                if billing_category == '1':
                    billing_type = 'monthly'
                elif billing_category == '6':
                    billing_type = 'one_time'
                else:
                    billing_type = 'monthly'

                # 商品を作成または更新
                product, created = Product.objects.update_or_create(
                    tenant_id=tenant_id,
                    product_code=contract_id,
                    defaults={
                        'product_name': contract_name,
                        'product_name_short': row.get('明細表記', '')[:50] if row.get('明細表記') else '',
                        'product_type': product_type,
                        'billing_type': billing_type,
                        'brand': brand,
                        'base_price': unit_price,
                        'mile': mile,
                        'max_discount_rate': max_discount,
                        'is_active': row.get('有効・無効', '1') == '1',
                        'description': row.get('逆引き保護者用表記', ''),
                    }
                )

                if created:
                    stats['products_created'] += 1
                else:
                    stats['products_updated'] += 1

            except Exception as e:
                stats['errors'].append({
                    'row': stats['total_rows'],
                    'contract_id': contract_id,
                    'error': str(e)
                })

        print(f"Products created: {stats['products_created']}")
        print(f"Products updated: {stats['products_updated']}")

        # 第2パス: パック関連の作成
        print(f"\n=== Phase 2: Creating Pack Relations ({len(pack_relations)} relations) ===")

        for contract_id, required_brand_code in pack_relations:
            try:
                # 契約（商品）を取得
                product = Product.objects.filter(
                    tenant_id=tenant_id,
                    product_code=contract_id
                ).first()

                if not product:
                    continue

                # 必要なブランドを持つ商品を検索
                # required_brand_code はブランドコード
                required_brand = Brand.objects.filter(
                    tenant_id=tenant_id,
                    brand_code=required_brand_code
                ).first()

                if required_brand:
                    # 商品に必要ブランド情報をJSONフィールドに保存
                    # （ContractPackは契約同士の関連なので、ここでは商品レベルで記録）
                    product.description = f"{product.description}\n[必要ブランド: {required_brand.brand_name}]"
                    product.save()
                    stats['pack_relations'] += 1

            except Exception as e:
                stats['errors'].append({
                    'type': 'pack_relation',
                    'contract_id': contract_id,
                    'required': required_brand_code,
                    'error': str(e)
                })

        print(f"Pack relations processed: {stats['pack_relations']}")

    # 結果表示
    print("\n" + "=" * 50)
    print("Import Complete!")
    print("=" * 50)
    print(f"Total rows processed: {stats['total_rows']}")
    print(f"Products created: {stats['products_created']}")
    print(f"Products updated: {stats['products_updated']}")
    print(f"Pack relations: {stats['pack_relations']}")
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

    import_t3_csv(csv_path)

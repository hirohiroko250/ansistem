"""
契約データ（T3）インポートスクリプト
使用方法: docker compose run --rm backend python scripts/import_contracts.py <csv_path>
"""
import sys
import os
import django
import csv
from decimal import Decimal
from datetime import datetime

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.contracts.models import Product
from apps.schools.models import Brand
from apps.tenants.models import Tenant


# サクセス系ブランド（TE・RA・COテナント）
SUCCESS_BRANDS = {
    'AES', 'AGS', 'BMS', 'FES', 'GOK', 'MPS', 'MWS', 'PRS',
    'SCC', 'SEL', 'SFE', 'SFJ', 'SHI', 'SHS', 'SJJ', 'SJU',
    'SKC', 'SKK', 'SOS', 'SUC', 'SHO', 'SEK',
    # 名前に「サクセス」が含まれるものもサクセステナントへ
}


def parse_decimal(value):
    """Decimalパース"""
    if not value or value == '':
        return None
    try:
        return Decimal(str(value).replace(',', ''))
    except:
        return None


def parse_date(value):
    """日付パース"""
    if not value or value == '':
        return None
    try:
        return datetime.strptime(value, '%Y/%m/%d').date()
    except:
        return None


def get_item_type(category_name, category_code):
    """請求カテゴリ名から商品種別を判定"""
    category = category_name.lower() if category_name else ''

    # 入会時系
    if '入会時授業料' in category_name:
        return Product.ItemType.ENROLLMENT_TUITION
    if '入会時月会費' in category_name:
        return Product.ItemType.ENROLLMENT_MONTHLY_FEE
    if '入会時設備費' in category_name:
        return Product.ItemType.ENROLLMENT_FACILITY
    if '入会時教材費' in category_name:
        return Product.ItemType.ENROLLMENT_TEXTBOOK
    if '入会時' in category_name and '諸経費' in category_name:
        return Product.ItemType.ENROLLMENT_EXPENSE
    if '入会時' in category_name and '管理費' in category_name:
        return Product.ItemType.ENROLLMENT_MANAGEMENT

    # 基本料金
    if '授業料' in category_name:
        return Product.ItemType.TUITION
    if '月会費' in category_name:
        return Product.ItemType.MONTHLY_FEE
    if '設備費' in category_name:
        return Product.ItemType.FACILITY
    if '教材費' in category_name:
        return Product.ItemType.TEXTBOOK
    if '入会金' in category_name:
        return Product.ItemType.ENROLLMENT

    # 講習・テスト
    if '必須講習' in category_name:
        return Product.ItemType.REQUIRED_SEMINAR
    if '講習' in category_name:
        return Product.ItemType.SEMINAR
    if '必須テスト対策' in category_name:
        return Product.ItemType.REQUIRED_TEST_PREP
    if 'テスト対策' in category_name:
        return Product.ItemType.TEST_PREP
    if '必須模試' in category_name:
        return Product.ItemType.REQUIRED_MOCK_EXAM
    if '模試' in category_name:
        return Product.ItemType.MOCK_EXAM
    if '入試対策' in category_name:
        return Product.ItemType.EXAM_PREP

    # 検定
    if '検定料1' in category_name:
        return Product.ItemType.CERTIFICATION_FEE_1
    if '検定料2' in category_name:
        return Product.ItemType.CERTIFICATION_FEE_2
    if '検定料' in category_name:
        return Product.ItemType.CERTIFICATION_FEE_1

    # 備品
    if 'バッグ' in category_name:
        return Product.ItemType.BAG
    if 'そろばん本体' in category_name:
        return Product.ItemType.ABACUS

    # 学童
    if 'おやつ' in category_name:
        return Product.ItemType.SNACK
    if 'お弁当' in category_name:
        return Product.ItemType.LUNCH

    # その他
    if '管理費' in category_name:
        return Product.ItemType.MANAGEMENT

    return Product.ItemType.OTHER


def is_success_brand(brand_code, brand_name):
    """サクセス系ブランドかどうか判定"""
    if brand_code in SUCCESS_BRANDS:
        return True
    if brand_name and 'サクセス' in brand_name:
        return True
    return False


def import_contracts(csv_path):
    """契約データをインポート"""

    # テナント取得
    an_tenant = Tenant.objects.filter(tenant_code='100000').first()
    teraco_tenant = Tenant.objects.filter(tenant_code='101615').first()

    if not an_tenant:
        print("エラー: アンイングリッシュグループテナントが見つかりません")
        sys.exit(1)
    if not teraco_tenant:
        print("エラー: 株式会社TE・RA・COテナントが見つかりません")
        sys.exit(1)

    print(f"アンイングリッシュグループ: {an_tenant.id}")
    print(f"株式会社TE・RA・CO: {teraco_tenant.id}")

    # ブランドマップ（両テナント）
    brand_map = {}
    for b in Brand.objects.all():
        key = (b.tenant_id, b.brand_code)
        brand_map[key] = b
        # コードのみでも検索可能に
        if b.brand_code not in brand_map:
            brand_map[b.brand_code] = b
    print(f"ブランドマップ: {len(brand_map)} 件")

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            try:
                # 契約ID（請求ID）をproduct_codeとして使用
                billing_id = row.get('請求ID', '').strip()
                if not billing_id:
                    skipped += 1
                    continue

                # ブランド情報
                brand_code = row.get('契約ブランド記号', '').strip()
                brand_name = row.get('契約ブランド名', '').strip()

                # テナント決定（サクセス系かどうか）
                if is_success_brand(brand_code, brand_name):
                    tenant_id = teraco_tenant.id
                else:
                    tenant_id = an_tenant.id

                # ブランド取得
                brand = brand_map.get((tenant_id, brand_code)) or brand_map.get(brand_code)

                # 請求カテゴリ名と商品種別
                category_name = row.get('請求カテゴリ名', '').strip()
                category_code = row.get('請求カテゴリ区分', '').strip()
                item_type = get_item_type(category_name, category_code)

                # 契約名・明細表記
                contract_name = row.get('契約名', '').strip()
                detail_name = row.get('明細表記', '').strip()
                brand_category = row.get('ブランド別請求カテゴリ', '').strip()

                # 商品名を決定
                product_name = brand_category or detail_name or contract_name

                # 価格情報
                base_price = parse_decimal(row.get('単価', '0')) or Decimal('0')
                discount_max = parse_decimal(row.get('割引MAX(%)', '0')) or Decimal('0')
                mile = parse_decimal(row.get('マイル', '0')) or Decimal('0')

                # 税区分
                tax_type_val = row.get('税区分', '1').strip()
                if tax_type_val == '1':
                    tax_type = Product.TaxType.TAX_1
                elif tax_type_val == '2':
                    tax_type = Product.TaxType.TAX_2
                else:
                    tax_type = Product.TaxType.TAX_3

                # 2ヶ月目以降の月別料金（1月〜12月）
                billing_jan = parse_decimal(row.get('1月', ''))
                billing_feb = parse_decimal(row.get('2月', ''))
                billing_mar = parse_decimal(row.get('3月', ''))
                billing_apr = parse_decimal(row.get('4月', ''))
                billing_may = parse_decimal(row.get('5月', ''))
                billing_jun = parse_decimal(row.get('6月', ''))
                billing_jul = parse_decimal(row.get('7月', ''))
                billing_aug = parse_decimal(row.get('8月', ''))
                billing_sep = parse_decimal(row.get('9月', ''))
                billing_oct = parse_decimal(row.get('10月', ''))
                billing_nov = parse_decimal(row.get('11月', ''))
                billing_dec = parse_decimal(row.get('12月', ''))

                # 入会月別料金（1月入会者〜12月入会者）
                enroll_jan = parse_decimal(row.get('1月入会者', ''))
                enroll_feb = parse_decimal(row.get('2月入会者', ''))
                enroll_mar = parse_decimal(row.get('3月入会者', ''))
                enroll_apr = parse_decimal(row.get('4月入会者', ''))
                enroll_may = parse_decimal(row.get('5月入会者', ''))
                enroll_jun = parse_decimal(row.get('6月入会者', ''))
                enroll_jul = parse_decimal(row.get('7月入会者', ''))
                enroll_aug = parse_decimal(row.get('8月入会者', ''))
                enroll_sep = parse_decimal(row.get('9月入会者', ''))
                enroll_oct = parse_decimal(row.get('10月入会者', ''))
                enroll_nov = parse_decimal(row.get('11月入会者', ''))
                enroll_dec = parse_decimal(row.get('12月入会者', ''))

                # 有効・無効
                is_active = row.get('有効・無効', '1') == '1'

                # 一回きり判定（入会金、備品など）
                # ※教材費は半期・四半期ごとに2ヶ月目以降の該当月料金で請求するためis_one_time=False
                is_one_time = item_type in [
                    Product.ItemType.ENROLLMENT,
                    Product.ItemType.BAG,
                    Product.ItemType.ABACUS,
                ]

                # 入会時授業料判定
                is_enrollment_tuition = item_type == Product.ItemType.ENROLLMENT_TUITION

                # 既存チェック
                existing = Product.objects.filter(
                    tenant_id=tenant_id,
                    product_code=billing_id
                ).first()

                data = {
                    'tenant_id': tenant_id,
                    'product_code': billing_id,
                    'product_name': product_name,
                    'product_name_short': contract_name[:50] if contract_name else '',
                    'item_type': item_type,
                    'brand': brand,
                    'base_price': base_price,
                    'tax_type': tax_type,
                    'mile': mile,
                    'discount_max': discount_max,
                    'is_one_time': is_one_time,
                    'is_enrollment_tuition': is_enrollment_tuition,
                    'per_ticket_price': base_price if is_enrollment_tuition else None,
                    # 2ヶ月目以降料金
                    'billing_price_jan': billing_jan,
                    'billing_price_feb': billing_feb,
                    'billing_price_mar': billing_mar,
                    'billing_price_apr': billing_apr,
                    'billing_price_may': billing_may,
                    'billing_price_jun': billing_jun,
                    'billing_price_jul': billing_jul,
                    'billing_price_aug': billing_aug,
                    'billing_price_sep': billing_sep,
                    'billing_price_oct': billing_oct,
                    'billing_price_nov': billing_nov,
                    'billing_price_dec': billing_dec,
                    # 入会月別料金
                    'enrollment_price_jan': enroll_jan,
                    'enrollment_price_feb': enroll_feb,
                    'enrollment_price_mar': enroll_mar,
                    'enrollment_price_apr': enroll_apr,
                    'enrollment_price_may': enroll_may,
                    'enrollment_price_jun': enroll_jun,
                    'enrollment_price_jul': enroll_jul,
                    'enrollment_price_aug': enroll_aug,
                    'enrollment_price_sep': enroll_sep,
                    'enrollment_price_oct': enroll_oct,
                    'enrollment_price_nov': enroll_nov,
                    'enrollment_price_dec': enroll_dec,
                    'is_active': is_active,
                    'description': f"契約ID: {row.get('契約ID', '')}, カテゴリ: {category_name}",
                }

                if existing:
                    for key, value in data.items():
                        if key != 'brand' or value is not None:
                            setattr(existing, key, value)
                    existing.save()
                    updated += 1
                else:
                    Product.objects.create(**data)
                    imported += 1

                if (imported + updated) % 1000 == 0:
                    print(f"  処理中... {imported + updated} 件")

            except Exception as e:
                errors.append(f"行 {row_num}: {billing_id} - {str(e)}")
                continue

    return imported, updated, skipped, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_contracts.py <csv_path>")
        sys.exit(1)

    csv_path = sys.argv[1]

    if not os.path.exists(csv_path):
        print(f"エラー: ファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print(f"インポート開始: {csv_path}")
    print("-" * 50)

    imported, updated, skipped, errors = import_contracts(csv_path)

    print("-" * 50)
    print(f"完了!")
    print(f"  新規作成: {imported} 件")
    print(f"  更新: {updated} 件")
    print(f"  スキップ: {skipped} 件")

    if errors:
        print(f"  エラー: {len(errors)} 件")
        for error in errors[:20]:
            print(f"    - {error}")
        if len(errors) > 20:
            print(f"    ... 他 {len(errors) - 20} 件")

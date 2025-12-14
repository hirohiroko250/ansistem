"""
追加請求インポートスクリプト

T5_追加請求CSVからStudentItemを作成する。
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

import pandas as pd
from datetime import datetime
from decimal import Decimal
from django.db import transaction

from apps.contracts.models import Contract, StudentItem, Product
from apps.students.models import Student, Guardian
from apps.schools.models import School, Brand
from apps.tenants.models import Tenant

CSV_PATH = '/tmp/additional_billing.csv'


def get_tenant():
    tenant = Tenant.objects.first()
    if not tenant:
        print("テナントが見つかりません")
        sys.exit(1)
    return tenant


def parse_date(date_str):
    if pd.isna(date_str) or not date_str:
        return None
    try:
        if isinstance(date_str, str):
            return datetime.strptime(date_str.strip(), '%Y/%m/%d').date()
        return date_str
    except:
        return None


def get_billing_month(start_date):
    """開始日から請求月を取得"""
    if start_date:
        return start_date.strftime('%Y-%m')
    return datetime.now().strftime('%Y-%m')


def find_or_create_product(tenant, category_name, item_type_code, price):
    """商品を検索または作成"""
    # カテゴリー名から商品コードを生成
    product_code = f"IMP_{item_type_code}_{category_name[:10]}" if category_name else f"IMP_{item_type_code}"

    product = Product.objects.filter(
        tenant_id=tenant.id,
        product_code=product_code
    ).first()

    if not product:
        # 商品種別マッピング
        item_type_map = {
            '入会金': Product.ItemType.ENROLLMENT,
            '入会時教材費': Product.ItemType.ENROLLMENT_TEXTBOOK,
            '入会時授業料': Product.ItemType.ENROLLMENT_TUITION,
            '入会時月会費': Product.ItemType.ENROLLMENT_MONTHLY_FEE,
            '入会時設備費': Product.ItemType.ENROLLMENT_FACILITY,
            'バッグ': Product.ItemType.BAG,
            'そろばん本体代': Product.ItemType.ABACUS,
            '授業料': Product.ItemType.TUITION,
            '月会費': Product.ItemType.MONTHLY_FEE,
            '教材費': Product.ItemType.TEXTBOOK,
            '設備費': Product.ItemType.FACILITY,
        }

        item_type = Product.ItemType.OTHER
        if category_name:
            for key, val in item_type_map.items():
                if key in str(category_name):
                    item_type = val
                    break

        product = Product.objects.create(
            tenant_id=tenant.id,
            product_code=product_code,
            product_name=category_name or f'追加請求_{item_type_code}',
            item_type=item_type,
            base_price=Decimal(str(price)) if price else Decimal('0'),
            is_one_time=True,
        )

    return product


def import_data(dry_run=True):
    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    print(f"\nCSVファイルを読み込み中: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    print(f"総レコード数: {len(df)}")

    # マッピング作成
    print("既存データをマッピング中...")

    student_map = {}
    for s in Student.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        student_map[str(s.old_id)] = s
    print(f"  生徒: {len(student_map)}")

    contract_map = {}
    for c in Contract.objects.filter(tenant_id=tenant.id):
        if hasattr(c, 'old_id') and c.old_id:
            contract_map[str(c.old_id)] = c
    print(f"  契約: {len(contract_map)}")

    # 既存のStudentItemをold_idでマッピング
    existing_items = set()
    for item in StudentItem.objects.filter(tenant_id=tenant.id):
        if hasattr(item, 'old_id') and item.old_id:
            existing_items.add(str(item.old_id))
    print(f"  既存請求項目: {len(existing_items)}")

    brand_map = {}
    for b in Brand.objects.all():
        brand_map[b.brand_name] = b

    default_school = School.objects.filter(is_active=True).first()

    created_items = 0
    skipped_no_student = 0
    skipped_existing = 0
    skipped_invalid = 0
    errors = []

    with transaction.atomic():
        for idx, row in df.iterrows():
            billing_id = str(row['請求ID']).strip() if not pd.isna(row['請求ID']) else None

            if not billing_id:
                skipped_invalid += 1
                continue

            if billing_id in existing_items:
                skipped_existing += 1
                continue

            # 有無チェック（0は無効）
            if pd.isna(row['有無']) or int(row['有無']) == 0:
                skipped_invalid += 1
                continue

            # 生徒を検索
            student_old_id = str(int(row['生徒ID'])) if not pd.isna(row['生徒ID']) else None
            student = student_map.get(student_old_id) if student_old_id else None

            if not student:
                skipped_no_student += 1
                continue

            # 契約を検索
            contract_old_id = str(row['対象　契約ID']).strip() if not pd.isna(row['対象　契約ID']) else None
            contract = contract_map.get(contract_old_id) if contract_old_id else None

            # ブランドを検索
            brand_name = str(row['対象　同ブランド']).strip() if not pd.isna(row['対象　同ブランド']) else None
            brand = brand_map.get(brand_name) if brand_name else None

            # 日付
            start_date = parse_date(row.get('開始日'))
            billing_month = get_billing_month(start_date)

            # 金額
            try:
                price = Decimal(str(row['金額'])) if not pd.isna(row['金額']) else Decimal('0')
            except:
                price = Decimal('0')

            # 商品を取得または作成
            category_name = str(row['対象カテゴリー']) if not pd.isna(row['対象カテゴリー']) else ''
            category_code = str(int(row['請求カテゴリー区分'])) if not pd.isna(row['請求カテゴリー区分']) else '0'

            try:
                product = find_or_create_product(tenant, category_name, category_code, price)
            except Exception as e:
                errors.append(f"商品作成エラー ({billing_id}): {str(e)}")
                continue

            # 校舎
            school = student.primary_school or default_school

            # 備考
            notes_parts = []
            display_name = str(row['顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）']) if not pd.isna(row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）')) else ''
            if display_name:
                notes_parts.append(display_name)
            notes = '\n'.join(notes_parts)

            try:
                quantity = int(row['複数個']) if not pd.isna(row['複数個']) and row['複数個'] else 1
                if quantity < 1:
                    quantity = 1

                item = StudentItem(
                    tenant_id=tenant.id,
                    old_id=billing_id,
                    student=student,
                    contract=contract,
                    product=product,
                    brand=brand,
                    school=school,
                    start_date=start_date,
                    billing_month=billing_month,
                    quantity=quantity,
                    unit_price=price,
                    discount_amount=Decimal('0'),
                    final_price=price * quantity,
                    notes=notes,
                )

                if not dry_run:
                    item.save()

                existing_items.add(billing_id)
                created_items += 1

            except Exception as e:
                errors.append(f"作成エラー ({billing_id}): {str(e)}")
                import traceback
                traceback.print_exc()

        if dry_run:
            print("\n=== ドライラン結果 ===")
            print(f"作成予定: {created_items}")
            print(f"スキップ（生徒なし）: {skipped_no_student}")
            print(f"スキップ（既存）: {skipped_existing}")
            print(f"スキップ（無効）: {skipped_invalid}")
            if errors:
                print(f"\nエラー: {len(errors)}")
                for err in errors[:5]:
                    print(f"  - {err}")
            transaction.set_rollback(True)
        else:
            print("\n=== インポート結果 ===")
            print(f"作成: {created_items}")
            print(f"スキップ（生徒なし）: {skipped_no_student}")
            print(f"スキップ（既存）: {skipped_existing}")
            print(f"スキップ（無効）: {skipped_invalid}")
            if errors:
                print(f"\nエラー: {len(errors)}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()

    if args.execute:
        print("実際のインポートを実行...")
        import_data(dry_run=False)
    else:
        print("ドライランモード（--execute で実行）")
        import_data(dry_run=True)

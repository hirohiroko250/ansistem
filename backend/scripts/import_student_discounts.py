"""
生徒割引インポートスクリプト

T6_割引情報CSVからStudentDiscountを作成する。
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

from apps.contracts.models import Contract, StudentItem, StudentDiscount
from apps.students.models import Student, Guardian
from apps.schools.models import Brand
from apps.tenants.models import Tenant

CSV_PATH = '/tmp/student_discounts.csv'


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


def get_discount_unit(unit_str):
    """割引単位を変換"""
    if pd.isna(unit_str) or not unit_str:
        return StudentDiscount.DiscountUnit.YEN
    unit = str(unit_str).strip()
    if unit == '%' or unit == 'percent':
        return StudentDiscount.DiscountUnit.PERCENT
    return StudentDiscount.DiscountUnit.YEN


def get_end_condition(condition_str, recurring_flag):
    """終了条件を変換"""
    if pd.isna(condition_str) or not condition_str:
        # recurringフラグで判定
        if recurring_flag and int(recurring_flag) == 2:
            return StudentDiscount.EndCondition.MONTHLY
        return StudentDiscount.EndCondition.ONCE

    condition = str(condition_str).strip()
    if '毎月' in condition:
        return StudentDiscount.EndCondition.MONTHLY
    elif '終了日' in condition:
        return StudentDiscount.EndCondition.UNTIL_END_DATE
    return StudentDiscount.EndCondition.ONCE


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

    guardian_map = {}
    for g in Guardian.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        guardian_map[str(g.old_id)] = g
    print(f"  保護者: {len(guardian_map)}")

    contract_map = {}
    for c in Contract.objects.filter(tenant_id=tenant.id):
        if hasattr(c, 'old_id') and c.old_id:
            contract_map[str(c.old_id)] = c
    print(f"  契約: {len(contract_map)}")

    student_item_map = {}
    for item in StudentItem.objects.filter(tenant_id=tenant.id):
        if hasattr(item, 'old_id') and item.old_id:
            student_item_map[str(item.old_id)] = item
    print(f"  請求項目: {len(student_item_map)}")

    # 既存のStudentDiscountをold_idでマッピング
    existing_discounts = set()
    for d in StudentDiscount.objects.filter(tenant_id=tenant.id):
        if hasattr(d, 'old_id') and d.old_id:
            existing_discounts.add(str(d.old_id))
    print(f"  既存割引: {len(existing_discounts)}")

    brand_map = {}
    for b in Brand.objects.all():
        brand_map[b.brand_name] = b
    print(f"  ブランド: {len(brand_map)}")

    created_discounts = 0
    skipped_no_target = 0
    skipped_existing = 0
    skipped_invalid = 0
    errors = []

    with transaction.atomic():
        for idx, row in df.iterrows():
            discount_id = str(row['割引ID']).strip() if not pd.isna(row['割引ID']) else None

            if not discount_id:
                skipped_invalid += 1
                continue

            if discount_id in existing_discounts:
                skipped_existing += 1
                continue

            # 有無チェック（0は無効）
            if pd.isna(row['有無']) or int(row['有無']) == 0:
                skipped_invalid += 1
                continue

            # 生徒を検索
            student = None
            if not pd.isna(row['生徒ID']) and row['生徒ID']:
                student_old_id = str(int(row['生徒ID']))
                student = student_map.get(student_old_id)

            # 保護者を検索
            guardian = None
            if not pd.isna(row['保護者ID']) and row['保護者ID']:
                guardian_old_id = str(int(row['保護者ID']))
                guardian = guardian_map.get(guardian_old_id)

            # 対象が見つからない場合はスキップ
            if not student and not guardian:
                skipped_no_target += 1
                continue

            # 契約を検索
            contract = None
            if not pd.isna(row['対象　契約ID']) and row['対象　契約ID']:
                contract_old_id = str(row['対象　契約ID']).strip()
                contract = contract_map.get(contract_old_id)

            # 請求項目を検索
            student_item = None
            if not pd.isna(row['対象　請求ID']) and row['対象　請求ID']:
                item_old_id = str(row['対象　請求ID']).strip()
                student_item = student_item_map.get(item_old_id)

            # ブランドを検索
            brand = None
            if not pd.isna(row['対象　同ブランド']) and row['対象　同ブランド']:
                brand_name = str(row['対象　同ブランド']).strip()
                brand = brand_map.get(brand_name)

            # 日付
            start_date = parse_date(row.get('開始日'))
            end_date = parse_date(row.get('終了日'))

            # 金額
            try:
                amount = Decimal(str(row['金額'])) if not pd.isna(row['金額']) else Decimal('0')
            except:
                amount = Decimal('0')

            # 割引単位
            discount_unit = get_discount_unit(row.get('割引単位'))

            # 繰り返し
            recurring_flag = row.get('繰り返し')
            is_recurring = False
            if not pd.isna(recurring_flag) and int(recurring_flag) == 2:
                is_recurring = True

            # 自動割引
            is_auto = False
            if not pd.isna(row.get('自動割引')) and int(row['自動割引']) == 1:
                is_auto = True

            # 終了条件
            end_condition = get_end_condition(row.get('終了条件'), recurring_flag)

            # 割引名
            discount_name = str(row['顧客表記用割引名（契約、請求IDの割引は、そのすぐ下に表記）']) if not pd.isna(row.get('顧客表記用割引名（契約、請求IDの割引は、そのすぐ下に表記）')) else '割引'

            # 備考
            notes_parts = []
            if not pd.isna(row.get('社長のIF文用備考')) and row['社長のIF文用備考']:
                notes_parts.append(str(row['社長のIF文用備考']))
            if not pd.isna(row.get('返金時の注意')) and row['返金時の注意']:
                notes_parts.append(f"返金時注意: {row['返金時の注意']}")
            notes = '\n'.join(notes_parts)

            try:
                discount = StudentDiscount(
                    tenant_id=tenant.id,
                    old_id=discount_id,
                    student=student,
                    guardian=guardian,
                    contract=contract,
                    student_item=student_item,
                    brand=brand,
                    discount_name=discount_name[:200],
                    amount=amount,
                    discount_unit=discount_unit,
                    start_date=start_date,
                    end_date=end_date,
                    is_recurring=is_recurring,
                    is_auto=is_auto,
                    end_condition=end_condition,
                    is_active=True,
                    notes=notes,
                )

                if not dry_run:
                    discount.save()

                existing_discounts.add(discount_id)
                created_discounts += 1

            except Exception as e:
                errors.append(f"作成エラー ({discount_id}): {str(e)}")
                import traceback
                traceback.print_exc()

        if dry_run:
            print("\n=== ドライラン結果 ===")
            print(f"作成予定: {created_discounts}")
            print(f"スキップ（対象なし）: {skipped_no_target}")
            print(f"スキップ（既存）: {skipped_existing}")
            print(f"スキップ（無効）: {skipped_invalid}")
            if errors:
                print(f"\nエラー: {len(errors)}")
                for err in errors[:5]:
                    print(f"  - {err}")
            transaction.set_rollback(True)
        else:
            print("\n=== インポート結果 ===")
            print(f"作成: {created_discounts}")
            print(f"スキップ（対象なし）: {skipped_no_target}")
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

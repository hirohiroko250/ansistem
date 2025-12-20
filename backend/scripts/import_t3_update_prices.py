"""
T3（契約情報）CSVからStudentItemの価格を更新するスクリプト

T4 CSVから受講ID→契約IDのマッピングを取得し、
T3 CSVから契約ID→価格のマッピングを取得して、
StudentItemの金額を更新する
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import pandas as pd
from decimal import Decimal
from django.db import transaction

from apps.contracts.models import StudentItem
from apps.tenants.models import Tenant


def get_tenant():
    tenant = Tenant.objects.first()
    if not tenant:
        print("テナントが見つかりません")
        sys.exit(1)
    return tenant


def import_t3_prices(t3_csv_path, t4_csv_path, dry_run=True):
    """T3/T4 CSVから価格を更新"""
    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")
    print(f"T3 CSVファイル: {t3_csv_path}")
    print(f"T4 CSVファイル: {t4_csv_path}")
    print(f"モード: {'ドライラン' if dry_run else '実行'}")

    # T3 CSVを読み込み - 契約ID→価格マップ
    print("\nT3を読み込み中...")
    df_t3 = pd.read_csv(t3_csv_path, encoding='utf-8-sig', low_memory=False)
    print(f"T3レコード数: {len(df_t3)}")

    # 契約ID別に授業料の合計価格を取得
    # 請求カテゴリ区分: 1=授業料, 2=月会費, 3=設備費 など
    contract_monthly_price = {}  # 契約ID -> 月別の合計金額

    for idx, row in df_t3.iterrows():
        contract_id = str(row.get('契約ID', '')).strip()
        if not contract_id:
            continue

        # 有効なものだけ
        if row.get('有効・無効') != 1:
            continue

        # 月別価格を取得
        for month_num in range(1, 13):
            col_name = f'{month_num}月'
            if col_name in row:
                price = row.get(col_name, 0)
                if pd.isna(price):
                    price = 0
                price = int(price)

                if price > 0:
                    if contract_id not in contract_monthly_price:
                        contract_monthly_price[contract_id] = {}
                    if month_num not in contract_monthly_price[contract_id]:
                        contract_monthly_price[contract_id][month_num] = 0
                    contract_monthly_price[contract_id][month_num] += price

    print(f"契約月別価格マップ: {len(contract_monthly_price)}件")

    # T4 CSVを読み込み - 受講ID→契約IDマップ
    print("\nT4を読み込み中...")
    df_t4 = pd.read_csv(t4_csv_path, encoding='utf-8-sig', low_memory=False)
    print(f"T4レコード数: {len(df_t4)}")

    enrollment_to_contract = {}  # 受講ID -> 契約ID

    for idx, row in df_t4.iterrows():
        enrollment_id = str(row.get('受講ID', '')).strip()
        contract_id = str(row.get('契約ID', '')).strip()
        if enrollment_id and contract_id:
            enrollment_to_contract[enrollment_id] = contract_id

    print(f"受講ID→契約IDマップ: {len(enrollment_to_contract)}件")

    # StudentItemを更新
    print("\nStudentItemを更新中...")

    # T4形式のStudentItem（金額0）
    t4_items = StudentItem.objects.filter(
        tenant_id=tenant.id,
        old_id__startswith='UC',
        final_price=0
    )

    print(f"対象StudentItem（金額0、UC形式）: {t4_items.count()}件")

    stats = {
        'updated': 0,
        'skipped_no_contract': 0,
        'skipped_no_price': 0,
    }

    with transaction.atomic():
        for si in t4_items:
            enrollment_id = si.old_id

            # 受講ID → 契約ID
            contract_id = enrollment_to_contract.get(enrollment_id)
            if not contract_id:
                stats['skipped_no_contract'] += 1
                continue

            # 契約ID → 月別価格
            monthly_prices = contract_monthly_price.get(contract_id)
            if not monthly_prices:
                stats['skipped_no_price'] += 1
                continue

            # 請求月から該当月の価格を取得
            billing_month = si.billing_month
            if billing_month:
                try:
                    if '-' in billing_month:
                        month_num = int(billing_month.split('-')[1])
                    else:
                        month_num = int(billing_month[4:6])

                    price = monthly_prices.get(month_num)
                    if price and price > 0:
                        si.unit_price = Decimal(str(price))
                        si.final_price = Decimal(str(price))
                        if not dry_run:
                            si.save(update_fields=['unit_price', 'final_price'])
                        stats['updated'] += 1
                    else:
                        # 該当月の価格がない場合、最初に見つかった価格を使用
                        first_price = list(monthly_prices.values())[0] if monthly_prices else 0
                        if first_price > 0:
                            si.unit_price = Decimal(str(first_price))
                            si.final_price = Decimal(str(first_price))
                            if not dry_run:
                                si.save(update_fields=['unit_price', 'final_price'])
                            stats['updated'] += 1
                        else:
                            stats['skipped_no_price'] += 1
                except Exception as e:
                    stats['skipped_no_price'] += 1
            else:
                stats['skipped_no_price'] += 1

        if dry_run:
            print("\n=== ドライラン結果 ===")
            transaction.set_rollback(True)
        else:
            print("\n=== 実行結果 ===")

    print(f"更新: {stats['updated']}件")
    print(f"スキップ（契約IDなし）: {stats['skipped_no_contract']}件")
    print(f"スキップ（価格なし）: {stats['skipped_no_price']}件")

    # 最終状態
    if not dry_run:
        total = StudentItem.objects.filter(tenant_id=tenant.id).count()
        with_price = StudentItem.objects.filter(tenant_id=tenant.id).exclude(final_price=0).count()
        print(f"\n=== 最終状態 ===")
        print(f"総数: {total:,}件")
        print(f"金額あり: {with_price:,}件 ({with_price*100/total:.1f}%)")

    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='T3/T4 CSVから価格を更新')
    parser.add_argument('--t3', default='/tmp/T3_contracts.csv', help='T3 CSVファイルパス')
    parser.add_argument('--t4', default='/tmp/T4_contracts.csv', help='T4 CSVファイルパス')
    parser.add_argument('--execute', action='store_true', help='実際に更新を実行')
    args = parser.parse_args()

    if args.execute:
        print("実際の更新を実行します...")
        import_t3_prices(args.t3, args.t4, dry_run=False)
    else:
        print("ドライランモード（--execute で実行）")
        import_t3_prices(args.t3, args.t4, dry_run=True)

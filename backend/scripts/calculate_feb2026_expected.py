#!/usr/bin/env python3
"""
2026年2月請求 期待値計算スクリプト
旧OZAデータ（T4, T5, T6）から請求金額を計算し、CSVに出力

使い方:
  python scripts/calculate_feb2026_expected.py
"""
import csv
import sqlite3
from decimal import Decimal
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# パス設定
DATA_DIR = Path("/Users/hirosesuzu/Library/CloudStorage/GoogleDrive-katsu44sky@gmail.com/マイドライブ/OZAシステム/月謝DATA/2月DATA")
DB_PATH = Path("/Users/hirosesuzu/Desktop/アンシステム/backend/db.sqlite3")
OUTPUT_DIR = Path("/Users/hirosesuzu/Desktop/アンシステム/backend/scripts/output")

# 2026年2月
FEB_DATE = datetime(2026, 2, 1).date()


def load_product_prices():
    """商品マスタから価格を取得

    契約コードごとに、item_type別の価格を取得
    （商品コードのsuffix規則が契約タイプにより異なるため）
    """
    print("商品マスタを読み込み中...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 全商品を取得
    cursor.execute("""
        SELECT product_code, item_type, base_price
        FROM t03_products
        WHERE product_code IS NOT NULL AND base_price > 0
    """)

    # 契約コード別・item_type別に整理
    # contract_products[contract_id][item_type] = price (最初に見つかったものを使用)
    contract_products = defaultdict(dict)

    for row in cursor.fetchall():
        code, item_type, price = row
        if not code or not item_type:
            continue

        # 契約コードを抽出（最後の_より前）
        parts = code.rsplit('_', 1)
        if len(parts) == 2:
            contract_id = parts[0]
            suffix = parts[1]

            # 入会時・日割り系はスキップ（50番台）
            if suffix.isdigit() and int(suffix) >= 50:
                continue

            # 月額請求対象のitem_typeのみ
            if item_type in ('tuition', 'monthly_fee', 'facility'):
                if item_type not in contract_products[contract_id]:
                    contract_products[contract_id][item_type] = Decimal(str(price))

    conn.close()
    print(f"  契約コード数: {len(contract_products)}")
    return contract_products


def load_t4_contracts():
    """T4契約情報を読み込み"""
    print("T4契約情報を読み込み中...")

    csv_path = DATA_DIR / "T4_ユーザー契約情報_202601141851_UTF8.csv"

    contracts = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 終了日チェック
            end_date_str = row.get('終了日', '').strip()
            is_active = True
            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, '%Y/%m/%d').date()
                    if end_date < FEB_DATE:
                        is_active = False
                except:
                    pass

            if is_active:
                contracts.append({
                    'course_id': row.get('受講ID', '').strip(),
                    'guardian_id': row.get('保護者ID', '').strip(),
                    'guardian_name': row.get('保護者名1', '').strip(),
                    'student_id': row.get('生徒ID', '').strip(),
                    'student_name': row.get('生徒名1', '').strip(),
                    'contract_id': row.get('契約ID', '').strip(),
                    'contract_name': row.get('契約名', '').strip(),
                    'brand_name': row.get('Class用ブランド名', '').strip(),
                })

    print(f"  有効契約数: {len(contracts)}")
    return contracts


def load_t5_charges():
    """T5追加請求を読み込み（2026/02分のみ）"""
    print("T5追加請求を読み込み中...")

    csv_path = DATA_DIR / "T5_追加請求_202601141850_UTF8.csv"

    charges = defaultdict(list)  # guardian_id -> list of charges
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('有無', '').strip() != '1':
                continue

            start_date_str = row.get('開始日', '').strip()
            if not start_date_str or not start_date_str.startswith('2026/02'):
                continue

            guardian_id = row.get('保護者ID', '').strip()
            amount = Decimal(row.get('金額', '0').strip() or '0')
            name = row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）', '')

            charges[guardian_id].append({
                'amount': amount,
                'name': name,
            })

    total_count = sum(len(v) for v in charges.values())
    print(f"  2026/02追加請求: {total_count}件")
    return charges


def load_t6_discounts():
    """T6割引を読み込み（2026/02有効分）"""
    print("T6割引を読み込み中...")

    csv_path = DATA_DIR / "T6_割引情報_202601141850_UTF8.csv"

    discounts = defaultdict(list)  # guardian_id -> list of discounts
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('有無', '').strip() != '1':
                continue

            start_str = row.get('開始日', '').strip()
            end_str = row.get('終了日', '').strip()

            start_date = None
            end_date = None
            try:
                if start_str:
                    start_date = datetime.strptime(start_str, '%Y/%m/%d').date()
                if end_str:
                    end_date = datetime.strptime(end_str, '%Y/%m/%d').date()
            except:
                continue

            # 2026/02が範囲内か
            if start_date and start_date > FEB_DATE:
                continue
            if end_date and end_date < FEB_DATE:
                continue

            guardian_id = row.get('保護者ID', '').strip()
            amount = Decimal(row.get('金額', '0').strip() or '0')
            name = row.get('顧客表記用割引名（契約、請求IDの割引は、そのすぐ下に表記）', '')

            discounts[guardian_id].append({
                'amount': amount,
                'name': name,
            })

    total_count = sum(len(v) for v in discounts.values())
    print(f"  2026/02有効割引: {total_count}件")
    return discounts


def load_t20_balances():
    """T20過不足金を読み込み"""
    print("T20過不足金を読み込み中...")

    csv_path = DATA_DIR / "T20_過不足金一覧_202601141851_UTF8.csv"

    balances = {}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('請求日', '').strip() != '2026/02/01':
                continue

            guardian_id = row.get('保護者ID', '').strip()
            balance = Decimal(row.get('過不足金', '0').strip() or '0')
            name = f"{row.get('姓', '')} {row.get('名', '')}".strip()

            balances[guardian_id] = {
                'balance': balance,
                'name': name,
            }

    print(f"  2026/02保護者数: {len(balances)}")
    return balances


def calculate_monthly_fee(contracts, products):
    """契約から月額を計算

    各契約について、item_type別に価格を取得:
    - tuition: 授業料
    - monthly_fee: 月会費
    - facility: 設備費

    設備費は生徒ごとに重複排除（最高額を採用）
    """
    guardian_fees = defaultdict(lambda: {
        'contracts': [],
        'tuition': Decimal('0'),
        'monthly_fee': Decimal('0'),
        'facility': Decimal('0'),
        'total': Decimal('0'),
        'guardian_name': '',
    })

    # 生徒ごとの設備費を追跡（重複排除用）
    student_facilities = defaultdict(lambda: defaultdict(Decimal))  # guardian_id -> student_id -> facility_price

    for contract in contracts:
        guardian_id = contract['guardian_id']
        student_id = contract['student_id']
        contract_id = contract['contract_id']

        guardian_fees[guardian_id]['guardian_name'] = contract['guardian_name']

        # 契約コードからitem_type別の価格を取得
        contract_prices = products.get(contract_id, {})

        tuition = contract_prices.get('tuition', Decimal('0'))
        monthly = contract_prices.get('monthly_fee', Decimal('0'))
        facility = contract_prices.get('facility', Decimal('0'))

        guardian_fees[guardian_id]['tuition'] += tuition
        guardian_fees[guardian_id]['monthly_fee'] += monthly

        # 設備費は生徒ごとに最高額を追跡
        if facility > student_facilities[guardian_id][student_id]:
            student_facilities[guardian_id][student_id] = facility

        guardian_fees[guardian_id]['contracts'].append({
            'contract_id': contract_id,
            'student_id': student_id,
            'tuition': tuition,
            'monthly_fee': monthly,
            'facility': facility,
        })

    # 設備費の重複排除を適用
    for guardian_id in guardian_fees:
        # 各生徒の最高設備費を合計
        total_facility = sum(student_facilities[guardian_id].values())
        guardian_fees[guardian_id]['facility'] = total_facility
        guardian_fees[guardian_id]['total'] = (
            guardian_fees[guardian_id]['tuition'] +
            guardian_fees[guardian_id]['monthly_fee'] +
            total_facility
        )

    return guardian_fees


def main():
    print("=" * 60)
    print("2026年2月請求 期待値計算")
    print("=" * 60 + "\n")

    # データ読み込み
    products = load_product_prices()
    contracts = load_t4_contracts()
    charges = load_t5_charges()
    discounts = load_t6_discounts()
    balances = load_t20_balances()

    print("\n計算中...")

    # 月額計算
    guardian_fees = calculate_monthly_fee(contracts, products)

    # 結果を集計
    results = []

    # T20に載っている保護者をベースにする
    for guardian_id, balance_info in balances.items():
        fee_info = guardian_fees.get(guardian_id, {
            'tuition': Decimal('0'),
            'monthly_fee': Decimal('0'),
            'facility': Decimal('0'),
            'total': Decimal('0'),
            'guardian_name': balance_info['name'],
            'contracts': [],
        })

        # 追加請求
        charge_list = charges.get(guardian_id, [])
        charge_total = sum(c['amount'] for c in charge_list)

        # 割引
        discount_list = discounts.get(guardian_id, [])
        discount_total = sum(d['amount'] for d in discount_list)  # すでにマイナス値

        # 期待請求額
        expected_billing = fee_info['total'] + charge_total + discount_total

        results.append({
            'guardian_id': guardian_id,
            'guardian_name': fee_info['guardian_name'] or balance_info['name'],
            'contract_count': len(fee_info.get('contracts', [])),
            'tuition': fee_info['tuition'],
            'monthly_fee': fee_info['monthly_fee'],
            'facility': fee_info['facility'],
            'monthly_total': fee_info['total'],
            'charges': charge_total,
            'discounts': discount_total,
            'expected_billing': expected_billing,
            't20_balance': balance_info['balance'],
        })

    # CSV出力
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "feb2026_expected_billing.csv"

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'guardian_id', 'guardian_name', 'contract_count',
            'tuition', 'monthly_fee', 'facility', 'monthly_total',
            'charges', 'discounts', 'expected_billing', 't20_balance'
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n出力ファイル: {output_path}")

    # サマリー
    print("\n" + "=" * 60)
    print("サマリー")
    print("=" * 60)

    total_tuition = sum(r['tuition'] for r in results)
    total_monthly = sum(r['monthly_fee'] for r in results)
    total_facility = sum(r['facility'] for r in results)
    total_monthly_all = sum(r['monthly_total'] for r in results)
    total_charges = sum(r['charges'] for r in results)
    total_discounts = sum(r['discounts'] for r in results)
    total_expected = sum(r['expected_billing'] for r in results)

    print(f"保護者数: {len(results)}")
    print(f"")
    print(f"授業料合計: {total_tuition:,.0f}円")
    print(f"月会費合計: {total_monthly:,.0f}円")
    print(f"設備費合計: {total_facility:,.0f}円")
    print(f"月額合計: {total_monthly_all:,.0f}円")
    print(f"")
    print(f"追加請求合計: {total_charges:,.0f}円")
    print(f"割引合計: {total_discounts:,.0f}円")
    print(f"")
    print(f"期待請求額合計: {total_expected:,.0f}円")

    # 月額が0の保護者を警告
    zero_monthly = [r for r in results if r['monthly_total'] == 0]
    if zero_monthly:
        print(f"\n⚠️ 月額0の保護者: {len(zero_monthly)}件")
        print("  （商品マスタにマッチしなかった可能性）")

    # サンプル表示
    print("\n" + "-" * 60)
    print("サンプル（先頭5件）")
    print("-" * 60)
    for r in results[:5]:
        print(f"{r['guardian_id']}: {r['guardian_name']}")
        print(f"  月額: {r['monthly_total']:,.0f}円 + 追加: {r['charges']:,.0f}円 + 割引: {r['discounts']:,.0f}円 = {r['expected_billing']:,.0f}円")
        print(f"  T20残高: {r['t20_balance']:,.0f}円")


if __name__ == '__main__':
    main()

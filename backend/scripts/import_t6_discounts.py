"""
T6（割引情報）CSVからStudentItemの割引を更新するスクリプト

生徒IDと請求月で紐付けて、discount_amountとfinal_priceを更新
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import pandas as pd
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.db.models import Sum

from apps.contracts.models import StudentItem
from apps.students.models import Student
from apps.tenants.models import Tenant


def get_tenant():
    tenant = Tenant.objects.first()
    if not tenant:
        print("テナントが見つかりません")
        sys.exit(1)
    return tenant


def parse_date(date_str):
    """日付を解析"""
    if pd.isna(date_str) or not date_str:
        return None
    try:
        if isinstance(date_str, str):
            return datetime.strptime(date_str.strip(), '%Y/%m/%d').date()
        return date_str
    except:
        return None


def import_t6_discounts(csv_path, dry_run=True):
    """T6 CSVから割引を適用"""
    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")
    print(f"CSVファイル: {csv_path}")
    print(f"モード: {'ドライラン' if dry_run else '実行'}")

    # CSVを読み込み
    df = pd.read_csv(csv_path, encoding='utf-8-sig', low_memory=False)
    print(f"総レコード数: {len(df)}")

    # 生徒マップ
    student_map = {}
    for s in Student.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        student_map[str(s.old_id)] = s
    print(f"生徒マップ: {len(student_map)}件")

    # 生徒・月別の割引を集計
    # student_id -> billing_month -> total_discount
    student_month_discounts = {}

    for idx, row in df.iterrows():
        # 有効チェック
        if row.get('有無') != 1:
            continue

        # 生徒ID
        student_old_id = str(int(row['生徒ID'])) if not pd.isna(row['生徒ID']) else None
        if not student_old_id:
            # 保護者IDのみの場合はスキップ（保護者全体への割引は別処理が必要）
            continue

        student = student_map.get(student_old_id)
        if not student:
            continue

        # 金額（負の値）
        amount = row.get('金額', 0)
        if pd.isna(amount):
            amount = 0
        amount = int(amount)

        # 割引単位: 1=円（固定）, 2=円（税込）, 3=円（その他）
        # 全て円として扱う（パーセント割引は別途計算が必要）
        discount_unit = row.get('割引単位', 1)

        # 開始日から請求月を取得
        start_date = parse_date(row.get('開始日'))
        end_date = parse_date(row.get('終了日'))

        if not start_date:
            continue

        # 繰り返し: 1=1回だけ, 2=毎月
        repeat = row.get('繰り返し', 1)

        # 請求月を計算
        billing_months = []
        if repeat == 2 and end_date:
            # 毎月の場合、開始日から終了日までの各月
            current = start_date
            while current <= end_date:
                billing_months.append(current.strftime('%Y-%m'))
                # 次の月へ
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
        else:
            # 1回だけの場合
            billing_months.append(start_date.strftime('%Y-%m'))

        # 割引を集計
        student_id = str(student.id)
        for billing_month in billing_months:
            if student_id not in student_month_discounts:
                student_month_discounts[student_id] = {}
            if billing_month not in student_month_discounts[student_id]:
                student_month_discounts[student_id][billing_month] = 0

            # amountは負の値なので絶対値を加算
            student_month_discounts[student_id][billing_month] += abs(amount)

    print(f"割引対象: {len(student_month_discounts)}生徒")

    # 割引のある月を数える
    total_discount_months = sum(len(months) for months in student_month_discounts.values())
    print(f"割引月数: {total_discount_months}件")

    # StudentItemを更新
    print("\nStudentItemを更新中...")

    stats = {
        'updated': 0,
        'skipped': 0,
    }

    with transaction.atomic():
        for student_id, month_discounts in student_month_discounts.items():
            for billing_month, discount_amount in month_discounts.items():
                # この生徒・月のStudentItemを取得
                items = StudentItem.objects.filter(
                    tenant_id=tenant.id,
                    student_id=student_id,
                    billing_month=billing_month
                )

                if not items.exists():
                    # ハイフンなしの形式も試す
                    billing_month_alt = billing_month.replace('-', '')
                    items = StudentItem.objects.filter(
                        tenant_id=tenant.id,
                        student_id=student_id,
                        billing_month=billing_month_alt
                    )

                if not items.exists():
                    stats['skipped'] += 1
                    continue

                # 割引を按分して適用
                # 単純に最初のアイテムに全額適用
                item = items.first()
                current_discount = item.discount_amount or Decimal('0')
                new_discount = current_discount + Decimal(str(discount_amount))

                item.discount_amount = new_discount
                item.final_price = item.unit_price - new_discount
                if item.final_price < 0:
                    item.final_price = Decimal('0')

                if not dry_run:
                    item.save(update_fields=['discount_amount', 'final_price'])

                stats['updated'] += 1

        if dry_run:
            print("\n=== ドライラン結果 ===")
            transaction.set_rollback(True)
        else:
            print("\n=== 実行結果 ===")

    print(f"更新: {stats['updated']}件")
    print(f"スキップ: {stats['skipped']}件")

    # 最終状態
    if not dry_run:
        total = StudentItem.objects.filter(tenant_id=tenant.id).count()
        with_discount = StudentItem.objects.filter(tenant_id=tenant.id).exclude(discount_amount=0).count()
        total_discount = StudentItem.objects.filter(tenant_id=tenant.id).aggregate(
            total=Sum('discount_amount')
        )['total'] or 0
        print(f"\n=== 最終状態 ===")
        print(f"割引適用: {with_discount:,}件")
        print(f"割引総額: {total_discount:,.0f}円")

    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='T6 CSVから割引を適用')
    parser.add_argument('csv_path', nargs='?',
                        default='/tmp/T6_discounts.csv',
                        help='CSVファイルパス')
    parser.add_argument('--execute', action='store_true', help='実際に更新を実行')
    args = parser.parse_args()

    if args.execute:
        print("実際の更新を実行します...")
        import_t6_discounts(args.csv_path, dry_run=False)
    else:
        print("ドライランモード（--execute で実行）")
        import_t6_discounts(args.csv_path, dry_run=True)

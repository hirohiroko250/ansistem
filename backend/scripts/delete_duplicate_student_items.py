"""
重複StudentItemを削除するスクリプト

T4データが2回インポートされたことによる重複を削除:
- old_idが「UC」で始まる（T4データ）
- billing_monthがYYYYMM形式（ハイフンなし）
- contract_idがNone（契約に紐づいていない）

これらは正しいデータ（YYYY-MM形式、契約あり）の重複なので削除する。
T5データ（AB/NB/TB）は追加請求なので削除しない。
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.db import transaction
from apps.contracts.models import StudentItem


def delete_duplicate_items(dry_run=True):
    """重複StudentItemを削除"""

    print("=== 重複StudentItem削除スクリプト ===")
    print(f"モード: {'ドライラン' if dry_run else '実行'}")

    # 削除対象: UC + YYYYMM形式 + 契約なし
    duplicates = StudentItem.objects.filter(
        old_id__startswith='UC',
        contract__isnull=True
    ).exclude(billing_month__contains='-')

    total_count = duplicates.count()
    print(f"\n削除対象: {total_count:,}件")

    if total_count == 0:
        print("削除対象がありません。")
        return

    # サンプル表示
    print("\n--- 削除対象のサンプル（10件） ---")
    for item in duplicates[:10]:
        print(f"  old_id: {item.old_id}")
        print(f"  billing_month: {item.billing_month}")
        print(f"  notes: {(item.notes or '-')[:50]}")
        print(f"  unit_price: ¥{item.unit_price:,}" if item.unit_price else "  unit_price: -")
        print()

    # 確認
    if not dry_run:
        print(f"\n{total_count:,}件を削除します...")

        with transaction.atomic():
            deleted_count, _ = duplicates.delete()
            print(f"削除完了: {deleted_count:,}件")
    else:
        print("\n--- ドライラン終了 ---")
        print("実際に削除するには --execute オプションを付けて実行してください。")

    # 削除後の状態確認
    if not dry_run:
        remaining = StudentItem.objects.count()
        print(f"\n=== 削除後の状態 ===")
        print(f"StudentItem総数: {remaining:,}件")

        # 内訳
        uc_yyyy_mm = StudentItem.objects.filter(
            old_id__startswith='UC',
            billing_month__contains='-'
        ).count()
        t5_items = StudentItem.objects.filter(
            old_id__startswith='AB'
        ).count() + StudentItem.objects.filter(
            old_id__startswith='NB'
        ).count() + StudentItem.objects.filter(
            old_id__startswith='TB'
        ).count()

        print(f"  T4 (UC, YYYY-MM形式): {uc_yyyy_mm:,}件")
        print(f"  T5 (AB/NB/TB): {t5_items:,}件")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='重複StudentItemを削除')
    parser.add_argument('--execute', action='store_true', help='実際に削除を実行')
    args = parser.parse_args()

    if args.execute:
        print("実際の削除を実行します...")
        delete_duplicate_items(dry_run=False)
    else:
        print("ドライランモード（--execute で実行）")
        delete_duplicate_items(dry_run=True)

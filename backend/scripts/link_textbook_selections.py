"""
Link Textbook Selections Script

StudentItemにある教材費情報からContractのselected_textbooksを設定する。

Usage:
    docker-compose exec -T backend python scripts/link_textbook_selections.py
"""
import os
import sys
import django

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection
from apps.contracts.models import StudentItem, Contract


def link_textbook_selections(dry_run=True):
    """
    StudentItemの教材費情報からContractのselected_textbooksを設定する。

    Args:
        dry_run: Trueの場合は変更を保存しない
    """
    # 教材費のStudentItemを取得（直接SQL）
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, student_id, brand_id, product_id, notes
            FROM t04_student_items
            WHERE notes LIKE '%%教材%%'
            AND student_id IS NOT NULL
            AND brand_id IS NOT NULL
            AND product_id IS NOT NULL
        """)
        textbook_items = cursor.fetchall()

    print(f"教材費StudentItem数: {len(textbook_items)}")

    # 統計
    total_processed = 0
    total_linked = 0
    no_contract_found = 0
    already_linked = 0

    # 処理済みの契約+商品ペアを追跡
    processed_pairs = set()

    for item in textbook_items:
        item_id, student_id, brand_id, product_id, notes = item

        # 重複チェック
        pair_key = (str(student_id), str(brand_id), str(product_id))
        if pair_key in processed_pairs:
            continue
        processed_pairs.add(pair_key)

        total_processed += 1

        # 該当するContractを検索（直接SQL）
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, contract_no
                FROM t03_contracts
                WHERE student_id = %s
                AND brand_id = %s
                AND status = 'active'
            """, [str(student_id), str(brand_id)])
            contracts = cursor.fetchall()

        if not contracts:
            no_contract_found += 1
            continue

        for contract_id, contract_no in contracts:
            # 既にリンクされているか確認
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM t03_contracts_selected_textbooks WHERE contract_id = %s AND product_id = %s",
                    [str(contract_id), str(product_id)]
                )
                if cursor.fetchone():
                    already_linked += 1
                    continue

            # リンクを追加
            if not dry_run:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO t03_contracts_selected_textbooks (contract_id, product_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [str(contract_id), str(product_id)]
                    )

            total_linked += 1

            if total_linked <= 20:  # 最初の20件のみ詳細表示
                notes_str = notes[:40] if notes else "Unknown"
                print(f"  契約 {contract_no} ← 教材費 [{notes_str}]")

    print(f"\n結果サマリ:")
    print(f"  処理した教材費アイテム: {total_processed}")
    print(f"  リンクした数: {total_linked}")
    print(f"  契約が見つからなかった: {no_contract_found}")
    print(f"  既にリンク済み: {already_linked}")

    if dry_run:
        print("\n※ ドライラン実行 - 実際の変更は保存されていません")
        print("※ 実際に保存するには dry_run=False で実行してください")
    else:
        print("\n✓ 変更を保存しました")


if __name__ == '__main__':
    # コマンドライン引数で dry_run を制御
    dry_run = '--commit' not in sys.argv

    print("=" * 60)
    print("教材費選択リンクスクリプト")
    print("=" * 60)

    if dry_run:
        print("モード: ドライラン (変更は保存されません)")
    else:
        print("モード: コミット (変更を保存します)")

    print()
    link_textbook_selections(dry_run=dry_run)

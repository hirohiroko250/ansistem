"""
生徒・保護者情報インポートスクリプト

Excelファイルから生徒・保護者情報を更新する。
--fill-missing オプションで、空のフィールドのみ埋める（既存データは上書きしない）

Usage:
    docker-compose exec -T backend python scripts/import_student_guardian.py
    docker-compose exec -T backend python scripts/import_student_guardian.py --fill-missing
    docker-compose exec -T backend python scripts/import_student_guardian.py --fill-missing --commit
"""
import os
import sys
import django

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

import pandas as pd
from django.db import connection


def normalize_phone(phone):
    """電話番号を正規化"""
    if pd.isna(phone) or not phone:
        return None
    return str(phone).strip()


def is_empty(value):
    """値が空かどうか判定"""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False


def import_student_guardian(file_path, dry_run=True, fill_missing_only=False):
    """生徒・保護者情報をインポート

    Args:
        file_path: Excelファイルのパス
        dry_run: Trueの場合は変更を保存しない
        fill_missing_only: Trueの場合は空のフィールドのみ更新
    """

    print(f"ファイル読み込み: {file_path}")
    df = pd.read_excel(file_path)
    print(f"総レコード数: {len(df)}")

    if fill_missing_only:
        print("モード: 足りない情報のみ埋める（既存データは上書きしない）")
    else:
        print("モード: 全フィールドを上書き")

    # 統計
    guardian_updated = 0
    guardian_not_found = 0
    guardian_skipped = 0
    student_updated = 0
    student_not_found = 0
    student_skipped = 0
    errors = []

    for idx, row in df.iterrows():
        guardian_id = row.get('保護者ID')
        student_id = row.get('個人ID')

        if pd.isna(guardian_id):
            continue

        guardian_id = int(guardian_id)

        # 保護者を検索（全フィールド取得）
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, last_name, first_name, phone, email,
                          postal_code, prefecture, city, address1, address2
                   FROM t01_guardians WHERE guardian_no = %s""",
                [str(guardian_id)]
            )
            guardian = cursor.fetchone()

        if not guardian:
            guardian_not_found += 1
            if guardian_not_found <= 5:
                print(f"  保護者が見つかりません: guardian_no={guardian_id}")
            continue

        g_id, g_last_name, g_first_name, g_phone, g_email, g_postal, g_prefecture, g_city, g_address1, g_address2 = guardian

        # 更新データを準備
        new_last_name = str(row.get('苗字', '')).strip() if not pd.isna(row.get('苗字')) else None
        new_first_name = str(row.get('お名前', '')).strip() if not pd.isna(row.get('お名前')) else None
        new_phone = normalize_phone(row.get('電話1番号'))
        new_email = str(row.get('メールアドレス', '')).strip() if not pd.isna(row.get('メールアドレス')) else None
        new_postal = str(row.get('郵便番号', '')).strip() if not pd.isna(row.get('郵便番号')) else None
        new_prefecture = str(row.get('都道府県', '')).strip() if not pd.isna(row.get('都道府県')) else None
        new_city = str(row.get('市区町村', '')).strip() if not pd.isna(row.get('市区町村')) else None
        new_address1 = str(row.get('番地', '')).strip() if not pd.isna(row.get('番地')) else None
        new_address2 = str(row.get('建物・部屋番号', '')).strip() if not pd.isna(row.get('建物・部屋番号')) else None

        # 保護者を更新
        updates = []
        params = []

        if fill_missing_only:
            # 足りない情報のみ埋める
            if new_phone and is_empty(g_phone):
                updates.append("phone = %s")
                params.append(new_phone)
            if new_email and is_empty(g_email):
                updates.append("email = %s")
                params.append(new_email)
            if new_postal and is_empty(g_postal):
                updates.append("postal_code = %s")
                params.append(new_postal)
            if new_prefecture and is_empty(g_prefecture):
                updates.append("prefecture = %s")
                params.append(new_prefecture)
            if new_city and is_empty(g_city):
                updates.append("city = %s")
                params.append(new_city)
            if new_address1 and is_empty(g_address1):
                updates.append("address1 = %s")
                params.append(new_address1)
            if new_address2 and is_empty(g_address2):
                updates.append("address2 = %s")
                params.append(new_address2)
        else:
            # 全て上書き（従来の動作）
            if new_phone and new_phone != g_phone:
                updates.append("phone = %s")
                params.append(new_phone)
            if new_email and new_email != g_email:
                updates.append("email = %s")
                params.append(new_email)
            if new_postal:
                updates.append("postal_code = %s")
                params.append(new_postal)
            if new_prefecture:
                updates.append("prefecture = %s")
                params.append(new_prefecture)
            if new_city:
                updates.append("city = %s")
                params.append(new_city)
            if new_address1:
                updates.append("address1 = %s")
                params.append(new_address1)
            if new_address2:
                updates.append("address2 = %s")
                params.append(new_address2)

        if updates and not dry_run:
            params.append(str(g_id))
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE t01_guardians SET {', '.join(updates)} WHERE id = %s",
                    params
                )
            guardian_updated += 1
        elif updates:
            guardian_updated += 1
        else:
            guardian_skipped += 1

        # 生徒も更新（student_noで検索）
        if not pd.isna(student_id):
            student_id = int(student_id)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, last_name, first_name FROM t02_students WHERE student_no = %s",
                    [str(student_id)]
                )
                student = cursor.fetchone()

            if student:
                s_id, s_last_name, s_first_name = student

                s_updates = []
                s_params = []

                if fill_missing_only:
                    # 足りない情報のみ埋める
                    if new_last_name and is_empty(s_last_name):
                        s_updates.append("last_name = %s")
                        s_params.append(new_last_name)
                    if new_first_name and is_empty(s_first_name):
                        s_updates.append("first_name = %s")
                        s_params.append(new_first_name)
                else:
                    # 全て上書き（従来の動作）
                    if new_last_name and new_last_name != s_last_name:
                        s_updates.append("last_name = %s")
                        s_params.append(new_last_name)
                    if new_first_name and new_first_name != s_first_name:
                        s_updates.append("first_name = %s")
                        s_params.append(new_first_name)

                if s_updates and not dry_run:
                    s_params.append(str(s_id))
                    with connection.cursor() as cursor:
                        cursor.execute(
                            f"UPDATE t02_students SET {', '.join(s_updates)} WHERE id = %s",
                            s_params
                        )
                    student_updated += 1
                elif s_updates:
                    student_updated += 1
                else:
                    student_skipped += 1
            else:
                student_not_found += 1

        # 進捗表示
        if (idx + 1) % 2000 == 0:
            print(f"  処理中: {idx + 1}/{len(df)}")

    print()
    print("=== 結果 ===")
    print(f"保護者更新: {guardian_updated}件")
    print(f"保護者スキップ（既存データあり）: {guardian_skipped}件")
    print(f"保護者見つからず: {guardian_not_found}件")
    print(f"生徒更新: {student_updated}件")
    print(f"生徒スキップ（既存データあり）: {student_skipped}件")
    print(f"生徒見つからず: {student_not_found}件")

    if dry_run:
        print()
        print("※ ドライラン - 実際の変更は保存されていません")
        print("※ 実行するには --commit オプションを付けてください")
    else:
        print()
        print("✓ 変更を保存しました")


if __name__ == '__main__':
    file_path = '/app/生徒保護者情報.xlsx'
    dry_run = '--commit' not in sys.argv
    fill_missing_only = '--fill-missing' in sys.argv

    print("=" * 60)
    print("生徒・保護者情報インポート")
    print("=" * 60)

    if dry_run:
        print("モード: ドライラン")
    else:
        print("モード: コミット")

    if fill_missing_only:
        print("更新方式: 足りない情報のみ埋める")
    else:
        print("更新方式: 全て上書き")
    print()

    import_student_guardian(file_path, dry_run=dry_run, fill_missing_only=fill_missing_only)

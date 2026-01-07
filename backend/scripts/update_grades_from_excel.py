#!/usr/bin/env python
"""
コース/パックの学年定義をExcelから更新するスクリプト

使用方法（サーバー上で実行）:
1. このファイルとgrade_mapping.jsonをサーバーの /home/user/backend/scripts/ にコピー
2. cd /home/user/backend && source /home/user/venv/bin/activate
3. python manage.py shell < scripts/update_grades_from_excel.py
   または
   python scripts/update_grades_from_excel.py
"""
import os
import sys
import json

# Django設定を読み込む
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.schools.models import Grade
from apps.contracts.models import Course, Pack

# スクリプトのディレクトリを取得
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAPPING_FILE = os.path.join(SCRIPT_DIR, 'grade_mapping.json')


def load_mapping():
    """JSONファイルからマッピングを読み込む"""
    if not os.path.exists(MAPPING_FILE):
        print(f"エラー: マッピングファイルが見つかりません: {MAPPING_FILE}")
        return {}

    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_current_state():
    """現在の状態を確認"""
    print("=" * 60)
    print("現在の状態確認")
    print("=" * 60)

    print("\n=== 学年マスタ ===")
    grades = Grade.objects.all().order_by('sort_order')
    for g in grades:
        print(f"  {g.grade_code} | {g.grade_name}")
    print(f"\n学年マスタ総数: {grades.count()}件")

    print("\n=== 学年が未設定のアクティブコース ===")
    courses = Course.objects.filter(is_active=True, grade__isnull=True)
    print(f"件数: {courses.count()}")
    for c in courses[:5]:
        print(f"  {c.course_code} | {c.course_name}")
    if courses.count() > 5:
        print(f"  ... 他 {courses.count() - 5}件")

    print("\n=== 学年が未設定のアクティブパック ===")
    packs = Pack.objects.filter(is_active=True, grade__isnull=True)
    print(f"件数: {packs.count()}")
    for p in packs[:5]:
        print(f"  {p.pack_code} | {p.pack_name}")
    if packs.count() > 5:
        print(f"  ... 他 {packs.count() - 5}件")

    return courses.count(), packs.count()


def get_or_create_grade(grade_name):
    """学年マスタに存在しない場合は作成"""
    # 学年名から学年コードと並び順を生成
    grade_info = {
        # 単一学年
        '年少': ('PRESCHOOL_3', 1),
        '年中': ('PRESCHOOL_4', 2),
        '年長': ('PRESCHOOL_5', 3),
        '小1': ('ELEMENTARY_1', 4),
        '小2': ('ELEMENTARY_2', 5),
        '小3': ('ELEMENTARY_3', 6),
        '小4': ('ELEMENTARY_4', 7),
        '小5': ('ELEMENTARY_5', 8),
        '小6': ('ELEMENTARY_6', 9),
        '中1': ('JUNIOR_1', 10),
        '中2': ('JUNIOR_2', 11),
        '中3': ('JUNIOR_3', 12),
        '高1': ('HIGH_1', 13),
        '高2': ('HIGH_2', 14),
        '高3': ('HIGH_3', 15),
        # 範囲指定
        '年少~年長': ('PRESCHOOL_ALL', 100),
        '年中~年長': ('PRESCHOOL_4_5', 101),
        '年長~小3': ('K5_E3', 102),
        '年長~小4': ('K5_E4', 103),
        '年長~中3': ('K5_J3', 104),
        '小1~小3': ('E1_E3', 105),
        '小1~小4': ('E1_E4', 106),
        '小1~小6': ('E1_E6', 107),
        '小3~中1': ('E3_J1', 108),
        '小3~高1': ('E3_H1', 109),
        '小3~高3': ('E3_H3', 110),
        '小3~小6': ('E3_E6', 111),
        '小4~小6': ('E4_E6', 112),
        '小4~高3': ('E4_H3', 113),
        '小6~高3': ('E6_H3', 114),
        '中1~中3': ('J1_J3', 115),
        # 以上指定
        '年少以上': ('PRESCHOOL_3_PLUS', 200),
        '年中以上': ('PRESCHOOL_4_PLUS', 201),
        '年長以上': ('PRESCHOOL_5_PLUS', 202),
        '小1以上': ('E1_PLUS', 203),
        '小4以上': ('E4_PLUS', 204),
        '小４以上': ('E4_PLUS', 204),  # 全角数字対応
        '中学生以上': ('JUNIOR_PLUS', 205),
        '高校生': ('HIGH_ALL', 206),
        '大学以上': ('UNIV_PLUS', 207),
        '社会人': ('ADULT', 208),
        # その他
        '小１～小４': ('E1_E4', 106),  # 全角対応
        '小1~': ('E1_PLUS', 203),  # 曖昧な指定
        '3歳~小3': ('AGE3_E3', 300),
        '1歳~1歳半': ('AGE1_1H', 301),
        '1歳~小2': ('AGE1_E2', 302),
        '1歳半~2歳': ('AGE1H_2', 303),
        '2歳~3歳': ('AGE2_3', 304),
        '年中~中3': ('K4_J3', 305),
        '年中~小3': ('K4_E3', 306),
        '年少~中3': ('K3_J3', 307),
    }

    if grade_name in grade_info:
        grade_code, sort_order = grade_info[grade_name]
    else:
        # 未知の学年名の場合
        grade_code = grade_name.replace('~', '_').replace('以上', '_PLUS').replace(' ', '')
        sort_order = 999
        print(f"  警告: 未知の学年名 '{grade_name}' -> コード '{grade_code}'")

    grade, created = Grade.objects.get_or_create(
        grade_name=grade_name,
        defaults={
            'grade_code': grade_code,
            'sort_order': sort_order
        }
    )
    if created:
        print(f"  学年を作成: {grade_name} ({grade_code})")
    return grade


def update_course_pack_grades(mapping_data, dry_run=False):
    """コース/パックの学年を更新"""
    print("\n" + "=" * 60)
    print(f"学年の更新 {'(DRY RUN)' if dry_run else ''}")
    print("=" * 60)

    updated_courses = 0
    updated_packs = 0
    not_found = []

    for contract_id, grade_name in mapping_data.items():
        if not grade_name or not contract_id:
            continue

        # 学年を取得または作成
        if not dry_run:
            grade = get_or_create_grade(grade_name)
        else:
            grade = None

        # コースを更新（contract_idがcourse_codeと一致）
        courses = Course.objects.filter(course_code=contract_id, is_active=True, grade__isnull=True)
        if courses.exists():
            if not dry_run:
                courses.update(grade=grade)
            updated_courses += courses.count()

        # パックを更新（contract_idがpack_codeと一致）
        packs = Pack.objects.filter(pack_code=contract_id, is_active=True, grade__isnull=True)
        if packs.exists():
            if not dry_run:
                packs.update(grade=grade)
            updated_packs += packs.count()

    print(f"\n更新結果:")
    print(f"  コース: {updated_courses}件{'更新予定' if dry_run else '更新'}")
    print(f"  パック: {updated_packs}件{'更新予定' if dry_run else '更新'}")

    return updated_courses, updated_packs


def main():
    """メイン処理"""
    print("\n" + "=" * 60)
    print("コース/パック学年定義更新スクリプト")
    print("=" * 60)

    # マッピングを読み込む
    mapping = load_mapping()
    if not mapping:
        print("マッピングデータがありません。終了します。")
        return

    print(f"\nマッピングデータ: {len(mapping)}件読み込み")

    # 現在の状態を確認
    courses_without_grade, packs_without_grade = check_current_state()

    if courses_without_grade == 0 and packs_without_grade == 0:
        print("\n学年が未設定のコース/パックはありません。")
        return

    # DRY RUN
    print("\n--- DRY RUN（テスト実行）---")
    update_course_pack_grades(mapping, dry_run=True)

    # 確認
    print("\n" + "-" * 60)
    response = input("実行しますか？ (yes/no): ").strip().lower()
    if response != 'yes':
        print("キャンセルしました。")
        return

    # 実行
    print("\n--- 実行 ---")
    update_course_pack_grades(mapping, dry_run=False)

    # 結果確認
    print("\n--- 更新後の状態 ---")
    check_current_state()

    print("\n完了しました！")


if __name__ == '__main__':
    main()

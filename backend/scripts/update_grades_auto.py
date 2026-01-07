#!/usr/bin/env python
"""
コース/パックの学年定義を自動更新するスクリプト（対話なし版）

使用方法（サーバー上で実行）:
  cd /home/user/backend && source /home/user/venv/bin/activate
  python scripts/update_grades_auto.py
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

# 学年マッピング定義
GRADE_INFO = {
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
    '小４以上': ('E4_PLUS', 204),
    '中学生以上': ('JUNIOR_PLUS', 205),
    '高校生': ('HIGH_ALL', 206),
    '大学以上': ('UNIV_PLUS', 207),
    '社会人': ('ADULT', 208),
    # その他
    '小１～小４': ('E1_E4', 106),
    '小1~': ('E1_PLUS', 203),
    '3歳~小3': ('AGE3_E3', 300),
    '1歳~1歳半': ('AGE1_1H', 301),
    '1歳~小2': ('AGE1_E2', 302),
    '1歳半~2歳': ('AGE1H_2', 303),
    '2歳~3歳': ('AGE2_3', 304),
    '年中~中3': ('K4_J3', 305),
    '年中~小3': ('K4_E3', 306),
    '年少~中3': ('K3_J3', 307),
}


def load_mapping():
    """JSONファイルからマッピングを読み込む"""
    if not os.path.exists(MAPPING_FILE):
        print(f"エラー: マッピングファイルが見つかりません: {MAPPING_FILE}")
        return {}

    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_or_create_grade(grade_name):
    """学年マスタに存在しない場合は作成"""
    if grade_name in GRADE_INFO:
        grade_code, sort_order = GRADE_INFO[grade_name]
    else:
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


def main():
    """メイン処理"""
    print("=" * 60)
    print("コース/パック学年定義更新（自動実行）")
    print("=" * 60)

    # マッピングを読み込む
    mapping = load_mapping()
    if not mapping:
        print("マッピングデータがありません。終了します。")
        return

    print(f"\nマッピングデータ: {len(mapping)}件読み込み")

    # 更新前の状態
    courses_no_grade = Course.objects.filter(is_active=True, grade__isnull=True).count()
    packs_no_grade = Pack.objects.filter(is_active=True, grade__isnull=True).count()
    print(f"\n更新前:")
    print(f"  学年未設定コース: {courses_no_grade}件")
    print(f"  学年未設定パック: {packs_no_grade}件")

    # 更新実行
    updated_courses = 0
    updated_packs = 0
    created_grades = set()

    for contract_id, grade_name in mapping.items():
        if not grade_name or not contract_id:
            continue

        # コースを検索
        courses = Course.objects.filter(course_code=contract_id, is_active=True, grade__isnull=True)
        # パックを検索
        packs = Pack.objects.filter(pack_code=contract_id, is_active=True, grade__isnull=True)

        if courses.exists() or packs.exists():
            grade = get_or_create_grade(grade_name)
            created_grades.add(grade_name)

            if courses.exists():
                courses.update(grade=grade)
                updated_courses += courses.count()

            if packs.exists():
                packs.update(grade=grade)
                updated_packs += packs.count()

    # 結果表示
    print(f"\n更新結果:")
    print(f"  コース: {updated_courses}件更新")
    print(f"  パック: {updated_packs}件更新")
    print(f"  使用した学年: {len(created_grades)}種類")

    # 更新後の状態
    courses_no_grade_after = Course.objects.filter(is_active=True, grade__isnull=True).count()
    packs_no_grade_after = Pack.objects.filter(is_active=True, grade__isnull=True).count()
    print(f"\n更新後:")
    print(f"  学年未設定コース: {courses_no_grade_after}件")
    print(f"  学年未設定パック: {packs_no_grade_after}件")

    print("\n完了しました！")


if __name__ == '__main__':
    main()

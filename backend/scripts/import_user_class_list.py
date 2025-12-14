"""
UserClassListからStudentItemに曜日・時間情報をインポートするスクリプト

Usage:
    python manage.py shell < scripts/import_user_class_list.py
    または
    python manage.py runscript import_user_class_list
"""
import pandas as pd
from datetime import datetime, time
from apps.students.models import Student
from apps.contracts.models import StudentItem
from apps.schools.models import Brand, School

# Excelファイルパス
FILE_PATH = '/Users/hirosesuzu/Library/CloudStorage/GoogleDrive-katsu44sky@gmail.com/マイドライブ/OZAシステム/UserClassList - 2025-12-11T131958.831.xlsx'

# 曜日マッピング（Excel -> DB）
DOW_MAP = {
    '月': 1,
    '火': 2,
    '水': 3,
    '木': 4,
    '金': 5,
    '土': 6,
    '日': 7,
}


def parse_time(time_str):
    """時間文字列をtimeオブジェクトに変換"""
    if pd.isna(time_str):
        return None
    if isinstance(time_str, time):
        return time_str
    if isinstance(time_str, datetime):
        return time_str.time()
    try:
        return datetime.strptime(str(time_str), '%H:%M:%S').time()
    except ValueError:
        try:
            return datetime.strptime(str(time_str), '%H:%M').time()
        except ValueError:
            return None


def run():
    print(f"Loading Excel file: {FILE_PATH}")
    df = pd.read_excel(FILE_PATH)
    print(f"Total rows: {len(df)}")

    # ブランド名 -> Brand IDのマッピングを作成
    brands = {b.brand_name: b for b in Brand.objects.all()}
    print(f"Brands in DB: {len(brands)}")

    # 校舎名 -> School IDのマッピングを作成
    schools = {s.school_name: s for s in School.objects.all()}
    print(f"Schools in DB: {len(schools)}")

    # 生徒名 -> Student のマッピングを作成
    # 姓+名で検索
    students = {}
    for s in Student.objects.all():
        full_name = f"{s.last_name}{s.first_name}".replace('　', '').replace(' ', '')
        students[full_name] = s
    print(f"Students in DB: {len(students)}")

    updated_count = 0
    not_found_count = 0
    skipped_count = 0

    for idx, row in df.iterrows():
        # 退会日がある場合はスキップ
        if pd.notna(row.get('退会日')):
            skipped_count += 1
            continue

        # 休会中の場合はスキップ（オプション）
        # if row.get('休会中') == 'Y':
        #     skipped_count += 1
        #     continue

        # 生徒を検索
        student_name1 = str(row.get('生徒名1', '')).replace('　', '').replace(' ', '')
        student_name2 = str(row.get('生徒名2', '')).replace('　', '').replace(' ', '')
        full_name = f"{student_name1}{student_name2}"

        student = students.get(full_name)
        if not student:
            not_found_count += 1
            if idx < 20:  # 最初の20件のみ表示
                print(f"  Student not found: {full_name}")
            continue

        # ブランドを検索
        brand_name = row.get('ブランド名')
        brand = brands.get(brand_name)
        if not brand:
            # 部分一致で検索
            for bn, b in brands.items():
                if brand_name and brand_name in bn:
                    brand = b
                    break

        # 校舎を検索
        school_name = row.get('校舎名')
        school = schools.get(school_name)
        if not school and school_name:
            # 部分一致で検索（Excelの「本山校Motoyama」-> 「本山」で検索）
            import re
            # 日本語部分を抽出
            jp_match = re.match(r'^([^\x00-\x7F]+)', school_name)
            if jp_match:
                school_name_jp = jp_match.group(1)
                for sn, s in schools.items():
                    if school_name_jp in sn:
                        school = s
                        break

        # 曜日を変換
        dow_str = row.get('曜日')
        day_of_week = DOW_MAP.get(dow_str)

        # 開始時間を変換
        start_time = parse_time(row.get('開始時間'))

        if not day_of_week or not start_time:
            skipped_count += 1
            continue

        # StudentItemを更新または作成
        # まず該当のbrand+school+day_of_week+start_timeで既存を探す
        items = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True
        )

        # 同じbrand+school+曜日+時間の既存レコードがあるか確認
        existing_item = None
        if brand and school:
            existing_item = items.filter(
                brand=brand,
                school=school,
                day_of_week=day_of_week,
                start_time=start_time
            ).first()

        if existing_item:
            # 既に同じ内容で存在する
            skipped_count += 1
            continue

        # 曜日・時間が未設定のものを優先的に更新
        item = items.filter(day_of_week__isnull=True).first()

        if item:
            # 既存のStudentItemを更新
            item.day_of_week = day_of_week
            item.start_time = start_time
            if brand:
                item.brand = brand
            if school:
                item.school = school
            item.save(update_fields=['day_of_week', 'start_time', 'brand', 'school'])
            updated_count += 1
            if updated_count <= 20:
                print(f"  Updated: {full_name} - {brand_name} - {dow_str} {start_time}")
        else:
            # 既存のStudentItemがない場合は、ProductなしでStudentEnrollmentとして作成
            # または既存のStudentItem（day_of_weekがあっても）を更新
            any_item = items.first()
            if any_item:
                # 既存アイテムを更新（曜日・時間が違っても上書き）
                any_item.day_of_week = day_of_week
                any_item.start_time = start_time
                if brand:
                    any_item.brand = brand
                if school:
                    any_item.school = school
                any_item.save(update_fields=['day_of_week', 'start_time', 'brand', 'school'])
                updated_count += 1
                if updated_count <= 20:
                    print(f"  Updated (existing): {full_name} - {brand_name} - {dow_str} {start_time}")
            else:
                not_found_count += 1
                if not_found_count <= 20:
                    print(f"  No StudentItem: {full_name} - {brand_name}")

    print(f"\n=== Summary ===")
    print(f"Updated: {updated_count}")
    print(f"Not found: {not_found_count}")
    print(f"Skipped: {skipped_count}")


if __name__ == '__main__':
    run()

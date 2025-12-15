"""
UserClassListからStudentSchoolの曜日・時間帯をインポート

Usage (ローカル):
    cd backend && python scripts/import_student_school_schedule.py
"""
import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

import pandas as pd
from datetime import time
from apps.students.models import Student, StudentSchool
from apps.schools.models import School, Brand, ClassSchedule

# 曜日マッピング
DAY_MAP = {
    '月': 1, '火': 2, '水': 3, '木': 4, '金': 5, '土': 6, '日': 7
}

def extract_japanese_name(name):
    """校舎名から日本語部分を抽出（例: 尾張旭校Owariasahi → 尾張旭校）"""
    import re
    if not name or pd.isna(name):
        return ''
    # アルファベット以前の部分を取得
    match = re.match(r'^([^A-Za-z]+)', str(name))
    return match.group(1) if match else str(name)

def import_schedule():
    # Excelファイル読み込み
    excel_path = '/Volumes/share/_★20170701作業用/79 勝野紘尚/UserClassList - 2025-12-11T131958.831.xlsx'

    if not os.path.exists(excel_path):
        print(f"ファイルが見つかりません: {excel_path}")
        return

    print(f"読み込み中: {excel_path}")
    df = pd.read_excel(excel_path)
    print(f"総行数: {len(df)}")

    # 事前にキャッシュ（名前でマッチング）
    schools_cache = {s.school_name: s for s in School.objects.all()}
    brands_cache = {b.brand_name: b for b in Brand.objects.all()}
    students_cache = {str(s.old_id): s for s in Student.objects.exclude(old_id='').exclude(old_id__isnull=True)}

    print(f"キャッシュ: Schools={len(schools_cache)}, Brands={len(brands_cache)}, Students={len(students_cache)}")

    updated = 0
    created = 0
    skipped = 0
    errors = []

    # グループ化して処理（同一生徒×校舎×ブランドで1レコード）
    grouped = df.groupby(['生徒ID', '校舎名', 'ブランド名'])

    for (student_old_id, school_name_raw, brand_name), group in grouped:
        try:
            # 生徒取得
            student_old_id_str = str(int(student_old_id)) if pd.notna(student_old_id) else None
            if not student_old_id_str or student_old_id_str not in students_cache:
                skipped += 1
                continue
            student = students_cache[student_old_id_str]

            # 校舎取得（日本語名を抽出して検索）
            school_name = extract_japanese_name(school_name_raw)
            if school_name not in schools_cache:
                skipped += 1
                continue
            school = schools_cache[school_name]

            # ブランド取得
            if brand_name not in brands_cache:
                skipped += 1
                continue
            brand = brands_cache[brand_name]

            # 最初の行からスケジュール情報取得
            row = group.iloc[0]
            day_of_week_text = row['曜日']
            start_time_val = row['開始時間']

            day_of_week = DAY_MAP.get(day_of_week_text)
            if not day_of_week:
                skipped += 1
                continue

            # 開始時間の変換
            if pd.isna(start_time_val):
                start_time = None
            elif isinstance(start_time_val, time):
                start_time = start_time_val
            elif isinstance(start_time_val, str):
                parts = start_time_val.split(':')
                if len(parts) >= 2:
                    start_time = time(int(parts[0]), int(parts[1]))
                else:
                    start_time = None
            else:
                start_time = None

            # StudentSchoolレコード取得または作成
            student_school, is_created = StudentSchool.objects.get_or_create(
                student=student,
                school=school,
                brand=brand,
                deleted_at__isnull=True,
                defaults={
                    'tenant_id': student.tenant_id,
                    'start_date': row['ユーザークラス開始日'] if pd.notna(row['ユーザークラス開始日']) else '2025-01-01',
                    'day_of_week': day_of_week,
                    'start_time': start_time,
                }
            )

            if is_created:
                created += 1
            else:
                # 更新
                needs_update = False
                if student_school.day_of_week != day_of_week:
                    student_school.day_of_week = day_of_week
                    needs_update = True
                if start_time and student_school.start_time != start_time:
                    student_school.start_time = start_time
                    needs_update = True

                # ClassScheduleから終了時間を取得
                if start_time and not student_school.end_time:
                    class_schedule = ClassSchedule.objects.filter(
                        school=school,
                        brand=brand,
                        day_of_week=day_of_week,
                        start_time=start_time,
                        deleted_at__isnull=True
                    ).first()
                    if class_schedule and class_schedule.end_time:
                        student_school.end_time = class_schedule.end_time
                        student_school.class_schedule = class_schedule
                        needs_update = True

                if needs_update:
                    student_school.save()
                    updated += 1

        except Exception as e:
            errors.append(f"Error: {student_old_id}, {school_name_raw}, {brand_name}: {str(e)}")

    print(f"\n=== 結果 ===")
    print(f"作成: {created}")
    print(f"更新: {updated}")
    print(f"スキップ: {skipped}")
    print(f"エラー: {len(errors)}")

    if errors[:10]:
        print("\n最初の10エラー:")
        for e in errors[:10]:
            print(f"  {e}")

if __name__ == '__main__':
    import_schedule()
else:
    # Django shell用
    import_schedule()

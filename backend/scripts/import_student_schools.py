"""
生徒所属（StudentSchool）インポートスクリプト
UserClassList ExcelファイルからStudentSchoolテーブルにデータをインポート

実行方法:
  python manage.py shell < scripts/import_student_schools.py
"""
import pandas as pd
from datetime import datetime
from django.db import transaction
from apps.students.models import Student, StudentSchool
from apps.schools.models import School, Brand


def parse_date(value):
    """日付をパース"""
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value.split()[0], '%Y-%m-%d').date()
        except:
            return None
    return None


def import_student_schools(excel_path, dry_run=True):
    """生徒所属データをインポート"""
    print(f"Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path)
    print(f"Total rows: {len(df)}")

    # 必要なカラムを確認
    required_cols = ['生徒ID', 'ブランドID', '校舎ID', 'ユーザークラス開始日']
    for col in required_cols:
        if col not in df.columns:
            print(f"ERROR: Missing required column: {col}")
            return

    # キャッシュ用の辞書
    student_cache = {}
    school_cache = {}
    brand_cache = {}

    # 既存データをキャッシュ（old_idでマッチング）
    print("Loading existing data...")
    for s in Student.objects.all():
        if s.old_id:
            student_cache[str(s.old_id)] = s
    print(f"  Students (with old_id): {len(student_cache)}")

    for s in School.objects.all():
        school_cache[s.school_code] = s
    print(f"  Schools: {len(school_cache)}")

    for b in Brand.objects.all():
        brand_cache[b.brand_code] = b
        # ブランド名でもマッチングできるようにする
        brand_cache[b.brand_name] = b

    # 【星煌学院】【キタン塾】プレフィックス付きブランドをベースブランドにマッピング
    prefix_mapping = {
        '【星煌学院】アンイングリッシュクラブ': 'アンイングリッシュクラブ',
        '【星煌学院】アンそろばんクラブ': 'アンそろばんクラブ',
        '【星煌学院】アンプログラミングクラブ': 'アンプログラミングクラブ',
        '【星煌学院】アン美文字クラブ': 'アン美文字クラブ',
        '【星煌学院】アンさんこくキッズ': 'アンさんこくキッズ',
        '【キタン塾】アンイングリッシュクラブ': 'アンイングリッシュクラブ',
    }
    for prefixed, base in prefix_mapping.items():
        if base in brand_cache:
            brand_cache[prefixed] = brand_cache[base]

    print(f"  Brands: {len(brand_cache)}")

    # 重複チェック用
    existing_enrollments = set()
    for ss in StudentSchool.objects.all():
        key = (str(ss.student_id), str(ss.school_id), str(ss.brand_id))
        existing_enrollments.add(key)
    print(f"  Existing StudentSchool records: {len(existing_enrollments)}")

    # 統計
    stats = {
        'total': 0,
        'created': 0,
        'skipped_duplicate': 0,
        'skipped_no_student': 0,
        'skipped_no_school': 0,
        'skipped_no_brand': 0,
        'errors': []
    }

    # 作成するレコードを収集
    records_to_create = []

    # 生徒ごとにグループ化して、最初のレコードをis_primary=Trueにする
    student_primary_set = set()

    print("Processing rows...")
    for idx, row in df.iterrows():
        stats['total'] += 1

        old_id = str(row['生徒ID']).strip()
        brand_name = str(row['ブランド名']).strip()
        excel_school_code = str(row['校舎ID']).strip()
        # Excel校舎コード S0XXX を DB形式 S10XXX に変換
        school_code = 'S1' + excel_school_code[1:] if excel_school_code.startswith('S0') else excel_school_code
        start_date = parse_date(row['ユーザークラス開始日'])
        end_date = parse_date(row.get('ユーザークラス終了日'))

        # 生徒を検索（old_idでマッチング）
        student = student_cache.get(old_id)
        if not student:
            stats['skipped_no_student'] += 1
            if len(stats['errors']) < 20:
                stats['errors'].append(f"Row {idx+2}: Student not found (old_id={old_id})")
            continue

        # 校舎を検索
        school = school_cache.get(school_code)
        if not school:
            stats['skipped_no_school'] += 1
            if len(stats['errors']) < 20:
                stats['errors'].append(f"Row {idx+2}: School not found: {school_code}")
            continue

        # ブランドを検索（ブランド名でマッチング）
        brand = brand_cache.get(brand_name)
        if not brand:
            stats['skipped_no_brand'] += 1
            if len(stats['errors']) < 20:
                stats['errors'].append(f"Row {idx+2}: Brand not found: {brand_name}")
            continue

        # 重複チェック
        key = (str(student.id), str(school.id), str(brand.id))
        if key in existing_enrollments:
            stats['skipped_duplicate'] += 1
            continue

        # すでに処理済みのキーをチェック（同じExcel内の重複）
        if key in student_primary_set:
            # 同じ生徒+校舎+ブランドの組み合わせは1つだけ
            continue

        existing_enrollments.add(key)
        student_primary_set.add(key)

        # 開始日がない場合はスキップ
        if not start_date:
            if len(stats['errors']) < 20:
                stats['errors'].append(f"Row {idx+2}: No start_date for student (old_id={old_id})")
            continue

        # この生徒の最初の所属をis_primary=Trueにする
        is_primary = old_id not in [r['old_id'] for r in records_to_create]

        records_to_create.append({
            'student': student,
            'school': school,
            'brand': brand,
            'start_date': start_date,
            'end_date': end_date,
            'is_primary': is_primary,
            'old_id': old_id,
            'tenant_id': student.tenant_id,
        })
        stats['created'] += 1

    print("\n--- Summary ---")
    print(f"Total rows processed: {stats['total']}")
    print(f"Records to create: {stats['created']}")
    print(f"Skipped (duplicate): {stats['skipped_duplicate']}")
    print(f"Skipped (no student): {stats['skipped_no_student']}")
    print(f"Skipped (no school): {stats['skipped_no_school']}")
    print(f"Skipped (no brand): {stats['skipped_no_brand']}")

    if stats['errors']:
        print(f"\nFirst {len(stats['errors'])} errors:")
        for err in stats['errors'][:20]:
            print(f"  {err}")

    if dry_run:
        print("\n[DRY RUN] No changes made to database.")
        return stats

    # 実際にデータを作成
    print(f"\nCreating {len(records_to_create)} StudentSchool records...")
    with transaction.atomic():
        created_count = 0
        for rec in records_to_create:
            StudentSchool.objects.create(
                student=rec['student'],
                school=rec['school'],
                brand=rec['brand'],
                start_date=rec['start_date'],
                end_date=rec['end_date'],
                is_primary=rec['is_primary'],
                tenant_id=rec['tenant_id'],
            )
            created_count += 1
            if created_count % 500 == 0:
                print(f"  Created {created_count} records...")

        print(f"Created {created_count} StudentSchool records.")

    return stats


# 実行
EXCEL_PATH = "/Users/hirosesuzu/Library/CloudStorage/GoogleDrive-katsu44sky@gmail.com/マイドライブ/OZAシステム/UserClassList - 2025-12-11T131958.831.xlsx"
DRY_RUN = True  # True: 確認のみ, False: 実際にインポート

import_student_schools(EXCEL_PATH, dry_run=DRY_RUN)

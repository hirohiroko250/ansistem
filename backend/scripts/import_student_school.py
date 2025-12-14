#!/usr/bin/env python
"""
UserClassList ExcelからStudentSchoolテーブルへのインポートスクリプト

使用方法:
    python manage.py shell < scripts/import_student_school.py

または本番環境:
    docker exec -i oza_backend python manage.py shell < scripts/import_student_school.py
"""
import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

import pandas as pd
from datetime import datetime
from apps.students.models import Student, StudentSchool
from apps.schools.models import School, Brand
from apps.tenants.models import Tenant

# Excelファイルパス（本番環境では/tmpにコピーする）
EXCEL_PATH = '/tmp/UserClassList.xlsx'

def parse_date(value):
    """日付を解析"""
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

def get_enrollment_status(is_suspended, end_date):
    """在籍状況を判定"""
    if is_suspended == '○':
        return 'transferred'  # 休会中
    if end_date and end_date < datetime.now().date():
        return 'ended'  # 終了
    return 'active'  # 在籍中

def main():
    print("=== StudentSchool インポート開始 ===")

    # Excelファイル読み込み
    if not os.path.exists(EXCEL_PATH):
        print(f"エラー: ファイルが見つかりません: {EXCEL_PATH}")
        print("ファイルを /tmp/UserClassList.xlsx にコピーしてください")
        return

    df = pd.read_excel(EXCEL_PATH)
    print(f"読み込み行数: {len(df)}")

    # テナント取得（最初のテナントを使用）
    tenant = Tenant.objects.first()
    if not tenant:
        print("エラー: テナントが見つかりません")
        return
    print(f"テナント: {tenant.name} ({tenant.id})")

    # 校舎とブランドのキャッシュを作成
    schools = {s.school_code: s for s in School.objects.filter(tenant=tenant)}
    brands = {b.brand_code: b for b in Brand.objects.filter(tenant=tenant)}
    students = {str(s.student_no): s for s in Student.objects.filter(tenant=tenant)}

    print(f"校舎数: {len(schools)}, ブランド数: {len(brands)}, 生徒数: {len(students)}")

    # 統計
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    # 重複チェック用
    processed = set()

    for idx, row in df.iterrows():
        try:
            student_no = str(row.get('生徒ID', '')).strip()
            school_code = str(row.get('校舎ID', '')).strip()
            brand_code = str(row.get('ブランドID', '')).strip()

            if not student_no or not school_code or not brand_code:
                skipped_count += 1
                continue

            # 重複スキップ（同じ生徒・校舎・ブランドの組み合わせ）
            key = (student_no, school_code, brand_code)
            if key in processed:
                skipped_count += 1
                continue
            processed.add(key)

            # 関連オブジェクト取得
            student = students.get(student_no)
            school = schools.get(school_code)
            brand = brands.get(brand_code)

            if not student:
                if idx < 10:
                    print(f"  警告: 生徒が見つかりません: {student_no}")
                skipped_count += 1
                continue

            if not school:
                if idx < 10:
                    print(f"  警告: 校舎が見つかりません: {school_code}")
                skipped_count += 1
                continue

            if not brand:
                if idx < 10:
                    print(f"  警告: ブランドが見つかりません: {brand_code}")
                skipped_count += 1
                continue

            # 日付処理
            start_date = parse_date(row.get('ユーザークラス開始日'))
            end_date = parse_date(row.get('ユーザークラス終了日'))

            if not start_date:
                start_date = parse_date(row.get('開始日'))

            if not start_date:
                skipped_count += 1
                continue

            # 在籍状況
            is_suspended = row.get('休会中', '')
            enrollment_status = get_enrollment_status(is_suspended, end_date)

            # 既存レコード検索または作成
            student_school, created = StudentSchool.objects.update_or_create(
                tenant=tenant,
                student=student,
                school=school,
                brand=brand,
                defaults={
                    'enrollment_status': enrollment_status,
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_primary': True,  # 最初の登録を主所属とする
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

            if (created_count + updated_count) % 500 == 0:
                print(f"  処理中... 作成: {created_count}, 更新: {updated_count}")

        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"  エラー (行 {idx}): {e}")

    print("\n=== インポート完了 ===")
    print(f"作成: {created_count}")
    print(f"更新: {updated_count}")
    print(f"スキップ: {skipped_count}")
    print(f"エラー: {error_count}")

if __name__ == '__main__':
    main()

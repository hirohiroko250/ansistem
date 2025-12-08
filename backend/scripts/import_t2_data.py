#!/usr/bin/env python
"""
T2（個人・生徒情報）CSVインポートスクリプト

保護者と生徒の両方を処理し、StudentGuardian関連も作成
"""
import os
import sys
import csv
import uuid
from datetime import datetime
from pathlib import Path

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import transaction
from apps.students.models import Student, Guardian, StudentGuardian
from apps.schools.models import Grade, School

# テナントID（デフォルト）
DEFAULT_TENANT_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')

# 学年マッピング
GRADE_MAPPING = {
    '小1': 'elementary', '小2': 'elementary', '小3': 'elementary',
    '小4': 'elementary', '小5': 'elementary', '小6': 'elementary',
    '中1': 'junior_high', '中2': 'junior_high', '中3': 'junior_high',
    '高1': 'high_school', '高2': 'high_school', '高3': 'high_school',
    '年少': 'other', '年中': 'other', '年長': 'other',
    '社会人': 'other', '': 'other'
}

# 性別マッピング
GENDER_MAPPING = {
    '男': 'male',
    '女': 'female',
    '': 'other'
}

# ステータスマッピング
STATUS_MAPPING = {
    '受講中': 'active',
    '無': 'prospective',
    '保護者': 'active',  # 保護者用（使わない）
    '休会': 'resting',
    '退会': 'withdrawn',
}

# 続柄マッピング
RELATIONSHIP_MAPPING = {
    '父': 'father',
    '母': 'mother',
    '祖父': 'grandfather',
    '祖母': 'grandmother',
    '兄弟姉妹': 'sibling',
    '子': 'other',  # 生徒側から見た場合
    '保護者': 'other',
    '': 'other'
}


def parse_date(date_str):
    """日付文字列をパース"""
    if not date_str:
        return None
    try:
        # YYYY/MM/DD 形式
        return datetime.strptime(date_str, '%Y/%m/%d').date()
    except ValueError:
        try:
            # YYYY-MM-DD HH:MM:SS 形式
            return datetime.strptime(date_str.split()[0], '%Y-%m-%d').date()
        except ValueError:
            return None


def get_or_create_grade(grade_name, tenant_id):
    """学年を取得または作成"""
    if not grade_name or grade_name == '社会人':
        return None

    category = GRADE_MAPPING.get(grade_name, 'other')

    grade, created = Grade.objects.get_or_create(
        tenant_id=tenant_id,
        grade_name=grade_name,
        defaults={
            'grade_code': grade_name.replace(' ', '_'),
            'category': category,
            'sort_order': 0,
            'is_active': True
        }
    )
    if created:
        print(f"  Created grade: {grade_name}")
    return grade


def get_school_by_name(school_name, tenant_id):
    """校舎名から校舎を取得"""
    if not school_name or school_name == '-':
        return None

    school = School.objects.filter(
        tenant_id=tenant_id,
        school_name__icontains=school_name
    ).first()
    return school


def import_t2_csv(csv_path, tenant_id=DEFAULT_TENANT_ID):
    """T2 CSVをインポート"""

    print(f"Importing T2 data from: {csv_path}")
    print(f"Tenant ID: {tenant_id}")

    # 統計
    stats = {
        'total_rows': 0,
        'students_created': 0,
        'students_updated': 0,
        'guardians_created': 0,
        'guardians_updated': 0,
        'relations_created': 0,
        'skipped': 0,
        'errors': []
    }

    # 保護者と生徒の一時保存
    guardian_map = {}  # guardian_id -> Guardian instance
    student_guardian_pairs = []  # (student_id, guardian_id, relationship)

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total rows to process: {len(rows)}")

    with transaction.atomic():
        # 第1パス: 保護者の作成
        print("\n=== Phase 1: Creating Guardians ===")
        for row in rows:
            stats['total_rows'] += 1

            guardian_id = row.get('保護者ID', '')
            person_id = row.get('個人ID', '')
            relationship = row.get('保護者との続柄', '')

            # 保護者の場合（保護者IDと個人IDが同じ、または続柄が「保護者」）
            is_guardian = (guardian_id == person_id) or relationship == '保護者'

            if is_guardian and guardian_id not in guardian_map:
                try:
                    last_name = row.get('苗字', '')
                    first_name = row.get('お名前', '')

                    if not last_name or not first_name:
                        continue

                    guardian, created = Guardian.objects.update_or_create(
                        tenant_id=tenant_id,
                        guardian_no=guardian_id,
                        defaults={
                            'last_name': last_name,
                            'first_name': first_name,
                            'last_name_kana': row.get('苗字(ヨミ)', ''),
                            'first_name_kana': row.get('お名前(ヨミ)', ''),
                            'email': row.get('メールアドレス', ''),
                            'phone': row.get('電話1番号', ''),
                            'phone_mobile': row.get('電話2番号', ''),
                            'postal_code': row.get('郵便番号', '').replace('-', ''),
                            'prefecture': row.get('都道府県', ''),
                            'city': row.get('市区町村', ''),
                            'address1': row.get('番地', ''),
                            'address2': row.get('建物・部屋番号', ''),
                            'workplace': row.get('勤務先1', ''),
                        }
                    )

                    guardian_map[guardian_id] = guardian

                    if created:
                        stats['guardians_created'] += 1
                    else:
                        stats['guardians_updated'] += 1

                except Exception as e:
                    stats['errors'].append({
                        'row': stats['total_rows'],
                        'type': 'guardian',
                        'id': guardian_id,
                        'error': str(e)
                    })

        print(f"Guardians created: {stats['guardians_created']}")
        print(f"Guardians updated: {stats['guardians_updated']}")

        # 第2パス: 生徒の作成
        print("\n=== Phase 2: Creating Students ===")
        stats['total_rows'] = 0

        for row in rows:
            stats['total_rows'] += 1

            guardian_id = row.get('保護者ID', '')
            person_id = row.get('個人ID', '')
            relationship = row.get('保護者との続柄', '')

            # 生徒の場合（保護者IDと個人IDが違う、かつ続柄が「子」など）
            is_student = (guardian_id != person_id) and relationship != '保護者'

            if is_student:
                try:
                    last_name = row.get('苗字', '')
                    first_name = row.get('お名前', '')

                    if not last_name or not first_name:
                        stats['skipped'] += 1
                        continue

                    # 学年を取得または作成
                    grade_name = row.get('現在の学年', '')
                    grade = get_or_create_grade(grade_name, tenant_id)

                    # 校舎を取得
                    school_name = row.get('近くの校舎', '')
                    school = get_school_by_name(school_name, tenant_id)

                    # ステータス決定
                    status_raw = row.get('状態', '')
                    status = STATUS_MAPPING.get(status_raw, 'prospective')

                    # 性別
                    gender_raw = row.get('性別', '')
                    gender = GENDER_MAPPING.get(gender_raw, 'other')

                    # 生年月日
                    birth_date = parse_date(row.get('生年月日', ''))

                    student, created = Student.objects.update_or_create(
                        tenant_id=tenant_id,
                        student_no=person_id,
                        defaults={
                            'last_name': last_name,
                            'first_name': first_name,
                            'last_name_kana': row.get('苗字(ヨミ)', ''),
                            'first_name_kana': row.get('お名前(ヨミ)', ''),
                            'display_name': row.get('ニックネーム', ''),
                            'email': row.get('メールアドレス', ''),
                            'phone': row.get('電話1番号', ''),
                            'birth_date': birth_date,
                            'gender': gender,
                            'school_name': row.get('現在の学校名', ''),
                            'grade': grade,
                            'primary_school': school,
                            'status': status,
                        }
                    )

                    if created:
                        stats['students_created'] += 1
                    else:
                        stats['students_updated'] += 1

                    # 保護者との関連を記録
                    if guardian_id and guardian_id in guardian_map:
                        student_guardian_pairs.append((student, guardian_map[guardian_id], relationship))

                except Exception as e:
                    stats['errors'].append({
                        'row': stats['total_rows'],
                        'type': 'student',
                        'id': person_id,
                        'error': str(e)
                    })

        print(f"Students created: {stats['students_created']}")
        print(f"Students updated: {stats['students_updated']}")

        # 第3パス: 生徒-保護者関連の作成
        print("\n=== Phase 3: Creating Student-Guardian Relations ===")

        for student, guardian, relationship_raw in student_guardian_pairs:
            try:
                # 続柄を電話の関係から推測
                rel = RELATIONSHIP_MAPPING.get(relationship_raw, 'other')

                relation, created = StudentGuardian.objects.update_or_create(
                    tenant_id=tenant_id,
                    student=student,
                    guardian=guardian,
                    defaults={
                        'relationship': rel,
                        'is_primary': True,
                        'is_emergency_contact': True,
                        'is_billing_target': True,
                        'contact_priority': 1
                    }
                )

                if created:
                    stats['relations_created'] += 1

            except Exception as e:
                stats['errors'].append({
                    'type': 'relation',
                    'student': str(student),
                    'guardian': str(guardian),
                    'error': str(e)
                })

        print(f"Relations created: {stats['relations_created']}")

    # 結果表示
    print("\n" + "=" * 50)
    print("Import Complete!")
    print("=" * 50)
    print(f"Total rows processed: {len(rows)}")
    print(f"Guardians created: {stats['guardians_created']}")
    print(f"Guardians updated: {stats['guardians_updated']}")
    print(f"Students created: {stats['students_created']}")
    print(f"Students updated: {stats['students_updated']}")
    print(f"Relations created: {stats['relations_created']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {len(stats['errors'])}")

    if stats['errors']:
        print("\nFirst 10 errors:")
        for err in stats['errors'][:10]:
            print(f"  - {err}")

    return stats


if __name__ == '__main__':
    csv_path = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/T2_個人・生徒情報_202511282014_UTF8.csv'

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]

    import_t2_csv(csv_path)

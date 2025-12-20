"""
T4 CSVから生徒と保護者の紐付けを修正するスクリプト

生徒ID → 保護者ID のマッピングを使って、Student.guardian を更新
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import pandas as pd
from django.db import transaction

from apps.students.models import Student, Guardian
from apps.tenants.models import Tenant


def get_tenant():
    tenant = Tenant.objects.first()
    if not tenant:
        print("テナントが見つかりません")
        sys.exit(1)
    return tenant


def fix_guardian_links(csv_path, dry_run=True):
    """T4 CSVから保護者紐付けを修正"""
    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")
    print(f"CSVファイル: {csv_path}")
    print(f"モード: {'ドライラン' if dry_run else '実行'}")

    # CSVを読み込み
    df = pd.read_csv(csv_path, encoding='utf-8-sig', low_memory=False)
    print(f"総レコード数: {len(df)}")

    # 生徒マップ (old_id -> Student)
    student_map = {}
    for s in Student.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        student_map[str(s.old_id)] = s
    print(f"生徒マップ: {len(student_map)}件")

    # 保護者マップ (old_id -> Guardian)
    guardian_map = {}
    for g in Guardian.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        guardian_map[str(g.old_id)] = g
    print(f"保護者マップ: {len(guardian_map)}件")

    # 保護者なしの生徒を確認
    students_without_guardian = Student.objects.filter(
        tenant_id=tenant.id,
        guardian__isnull=True
    ).count()
    print(f"保護者なしの生徒: {students_without_guardian}件")

    # 生徒→保護者のマッピングを作成
    student_guardian_map = {}  # student_old_id -> guardian_old_id

    for idx, row in df.iterrows():
        student_old_id = str(int(row['生徒ID'])) if not pd.isna(row.get('生徒ID')) else None
        guardian_old_id = str(int(row['保護者ID'])) if not pd.isna(row.get('保護者ID')) else None

        if student_old_id and guardian_old_id:
            # 最初に見つかったマッピングを使用
            if student_old_id not in student_guardian_map:
                student_guardian_map[student_old_id] = guardian_old_id

    print(f"生徒→保護者マッピング: {len(student_guardian_map)}件")

    stats = {
        'updated': 0,
        'already_linked': 0,
        'guardian_not_found': 0,
        'student_not_found': 0,
    }

    with transaction.atomic():
        for student_old_id, guardian_old_id in student_guardian_map.items():
            student = student_map.get(student_old_id)
            if not student:
                stats['student_not_found'] += 1
                continue

            # 既に保護者が設定されている場合はスキップ
            if student.guardian_id:
                stats['already_linked'] += 1
                continue

            guardian = guardian_map.get(guardian_old_id)
            if not guardian:
                stats['guardian_not_found'] += 1
                continue

            # 保護者を設定
            student.guardian = guardian
            if not dry_run:
                student.save(update_fields=['guardian'])
            stats['updated'] += 1

        if dry_run:
            print("\n=== ドライラン結果 ===")
            transaction.set_rollback(True)
        else:
            print("\n=== 実行結果 ===")

    print(f"更新: {stats['updated']}件")
    print(f"既にリンク済み: {stats['already_linked']}件")
    print(f"保護者が見つからない: {stats['guardian_not_found']}件")
    print(f"生徒が見つからない: {stats['student_not_found']}件")

    # 最終状態
    if not dry_run:
        students_without_guardian = Student.objects.filter(
            tenant_id=tenant.id,
            guardian__isnull=True
        ).count()
        total_students = Student.objects.filter(tenant_id=tenant.id).count()
        print(f"\n=== 最終状態 ===")
        print(f"保護者なしの生徒: {students_without_guardian}件 / {total_students}件")

    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='T4 CSVから保護者紐付けを修正')
    parser.add_argument('csv_path', nargs='?',
                        default='/tmp/T4_contracts.csv',
                        help='T4 CSVファイルパス')
    parser.add_argument('--execute', action='store_true', help='実際に更新を実行')
    args = parser.parse_args()

    if args.execute:
        print("実際の更新を実行します...")
        fix_guardian_links(args.csv_path, dry_run=False)
    else:
        print("ドライランモード（--execute で実行）")
        fix_guardian_links(args.csv_path, dry_run=True)

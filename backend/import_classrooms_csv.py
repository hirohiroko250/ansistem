#!/usr/bin/env python
"""
教室CSVからデータをインポート
T11_教室マスタ
"""
import os
import sys
sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import csv
from apps.schools.models import Classroom, School
from apps.tenants.models import Tenant


CSV_PATH = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/T11 教室 2025年12月03.csv'


def get_tenant():
    return Tenant.objects.get(tenant_code='OZA')


def import_classrooms():
    print("=" * 60)
    print("教室CSVインポート (T11)")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    # 現在の教室数
    current_count = Classroom.objects.filter(tenant_id=tenant.id).count()
    print(f"現在の教室数: {current_count}")

    # 校舎コードマッピングを取得
    schools = {s.school_code: s for s in School.objects.filter(tenant_id=tenant.id)}
    print(f"校舎数: {len(schools)}")

    created = 0
    updated = 0
    errors = 0
    skipped = 0

    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                classroom_code = row.get('教室コード', '').strip()
                if not classroom_code:
                    continue

                # 校舎を取得（校舎IDで検索）
                school_code = row.get('校舎ID', '').strip()
                if school_code not in schools:
                    print(f"警告: 校舎 '{school_code}' が見つかりません (教室: {classroom_code})")
                    skipped += 1
                    continue

                school = schools[school_code]

                # 定員
                try:
                    capacity = int(row.get('Room定員', '0').strip() or '0')
                except:
                    capacity = 0

                # 並び順
                try:
                    sort_order = int(row.get('並び順', '0').strip() or '0')
                except:
                    sort_order = 0

                # 有効フラグ
                is_active_val = row.get('有効', '1').strip()
                is_active = is_active_val == '1'

                # フロア（CSVには空だが、説明から抽出可能）
                floor = row.get('フロア', '').strip()
                description = row.get('説明', '').strip()

                # 説明からフロア情報を抽出（1F, 2F, 3F など）
                if not floor and description:
                    import re
                    floor_match = re.match(r'^(\d+F)', description)
                    if floor_match:
                        floor = floor_match.group(1)

                classroom, is_created = Classroom.objects.update_or_create(
                    school=school,
                    classroom_code=classroom_code,
                    defaults={
                        'tenant_id': tenant.id,
                        'classroom_name': row.get('教室名', '').strip(),
                        'capacity': capacity,
                        'floor': floor,
                        'room_type': '',  # CSVには種別情報なし
                        'equipment': [],  # 設備はJSONフィールド
                        'sort_order': sort_order,
                        'is_active': is_active,
                    }
                )

                # 説明があればroom_typeに設定
                if description and not classroom.room_type:
                    classroom.room_type = description[:50]  # 最大50文字
                    classroom.save()

                if is_created:
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                errors += 1
                print(f"エラー ({row.get('教室コード', 'unknown')}): {e}")

    print(f"\n=== 結果 ===")
    print(f"作成: {created}")
    print(f"更新: {updated}")
    print(f"スキップ: {skipped}")
    print(f"エラー: {errors}")

    # 確認
    final_count = Classroom.objects.filter(tenant_id=tenant.id).count()
    print(f"\n=== 確認 ===")
    print(f"教室総数: {final_count}")

    # 校舎別集計
    print(f"\n=== 校舎別教室数（上位10校舎）===")
    from django.db.models import Count
    school_counts = Classroom.objects.filter(
        tenant_id=tenant.id
    ).values(
        'school__school_name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    for sc in school_counts:
        print(f"  {sc['school__school_name']}: {sc['count']}室")

    # サンプル表示
    print(f"\n=== サンプル（最初の15件）===")
    for classroom in Classroom.objects.filter(tenant_id=tenant.id).order_by('sort_order')[:15]:
        print(f"  [{classroom.classroom_code}] {classroom.classroom_name} ({classroom.school.school_name}) 定員:{classroom.capacity}")


if __name__ == '__main__':
    import_classrooms()

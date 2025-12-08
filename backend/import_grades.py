#!/usr/bin/env python
"""
対象学年マスタをインポート
HTMLから抽出したデータを登録
"""
import os
import sys
sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.schools.models import Grade
from apps.tenants.models import Tenant


# HTMLから抽出した対象学年データ
GRADE_DATA = [
    (1, "1-2歳", 2),
    (2, "1歳半から", 2),
    (3, "2-3歳", 1),
    (4, "ALL", 23),
    (5, "高１", 1),
    (6, "高2", 1),
    (7, "高3", 1),
    (8, "高校生", 3),
    (9, "小１", 1),
    (10, "小１以上", 17),
    (11, "小１-小３", 3),
    (12, "小２", 1),
    (13, "小３", 1),
    (14, "小３-小６", 4),
    (15, "小３-中１", 6),
    (16, "小４", 1),
    (17, "小４～小６", 3),
    (18, "小5", 1),
    (19, "小6", 1),
    (20, "小６-高３", 12),
    (21, "小学生", 6),
    (22, "中１", 1),
    (23, "中１～中３", 3),
    (24, "中１・中２", 2),
    (25, "中2", 1),
    (26, "中3", 1),
    (27, "中学生", 3),
    (28, "年少", 1),
    (29, "年中", 1),
    (30, "年中・年長", 2),
    (31, "年中以上", 19),
    (32, "年中-小３", 5),
    (33, "年長", 1),
    (34, "幼児", 3),
    (35, "幼児～小４", 7),
    (36, "幼児以上", 20),
    (37, "0歳～小１", 7),
    (38, "小1-小4", 4),
    (39, "小4～高3", 14),
    (40, "幼児～小３", 6),
    (41, "小1～小5", 5),
    (42, "年長～小6", 7),
    (43, "小3-中3", 7),
    (44, "年長～中3", 10),
    (45, "年長以上", 18),
    (46, "中１＋小６", 2),
    (47, "中学生＋小６", 4),
    (48, "中3・高１", 2),
    # (49, "", 0),  # 空のためスキップ
    (50, "小4～中3", 6),
    (51, "中学生以上", 10),
    (52, "0-1歳", 1),
    (53, "高校生＋中3", 4),
    (54, "年長～小2", 3),
    (55, "社会人", 1),
    (56, "大学生以上", 5),
    (57, "2-3歳児～小3", 7),
    (58, "小3-小4", 2),
    (59, "小4-小5", 2),
    (60, "小5-小6", 2),
    (61, "小5～中3", 5),
    (62, "小1～中3", 9),
    (63, "年長～小5", 6),
    (64, "小3-小5", 3),
    (65, "年少以上", 12),
    (66, "年長～小３", 4),
    (67, "年長～中学生", 10),
    # (68, "", 6),  # 空のためスキップ
    (69, "Yellow年長含む", 5),
    # (70, "中2", 0),  # 重複のためスキップ
    (71, "小１～中学生", 0),
    (72, "小3-高1", 8),
    # (73, "", 0),  # 空のためスキップ
    (74, "中2＋中3", 2),
    # (75, "小１～小３", 0),  # 重複のためスキップ
    (76, "2-3歳児～幼児", 4),
    # (77, "高校生", 0),  # 重複のためスキップ
    (78, "小1～", 12),
    (79, "小1～小6", 6),
    (80, "年少～小2", 5),
    (81, "年少～小３", 6),
    (82, "年少～小6", 9),
    (83, "年少～年長", 3),
    (84, "年長～", 4),
    (85, "年少～高校生", 16),
    (86, "小５-高３", 8),
    (87, "小3-高2", 9),
    (88, "高3", 1),
    (89, "中1～高3", 6),
]


def get_category(grade_name):
    """学年名からカテゴリを推定"""
    if any(k in grade_name for k in ['0歳', '1歳', '2歳', '3歳', '幼児', '年少', '年中', '年長']):
        return 'preschool'
    elif any(k in grade_name for k in ['小１', '小２', '小３', '小４', '小5', '小6', '小学']):
        if any(k in grade_name for k in ['中', '高']):
            return 'mixed'
        return 'elementary'
    elif any(k in grade_name for k in ['中１', '中2', '中3', '中学']):
        if any(k in grade_name for k in ['高']):
            return 'mixed'
        return 'junior_high'
    elif any(k in grade_name for k in ['高１', '高2', '高3', '高校']):
        return 'high_school'
    elif any(k in grade_name for k in ['大学', '社会人']):
        return 'adult'
    elif grade_name == 'ALL':
        return 'all'
    else:
        return 'other'


def get_tenant():
    return Tenant.objects.get(tenant_code='OZA')


def import_grades():
    print("=" * 60)
    print("対象学年マスタインポート")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    # 現在の学年数
    current_count = Grade.objects.filter(tenant_id=tenant.id).count()
    print(f"現在の学年数: {current_count}")

    created = 0
    updated = 0
    errors = 0

    for sort_order, grade_name, usage_count in GRADE_DATA:
        if not grade_name.strip():
            continue

        try:
            grade_code = f"G{sort_order:03d}"
            category = get_category(grade_name)

            grade, is_created = Grade.objects.update_or_create(
                tenant_id=tenant.id,
                grade_code=grade_code,
                defaults={
                    'grade_name': grade_name,
                    'grade_name_short': grade_name[:10] if len(grade_name) > 10 else grade_name,
                    'category': category,
                    'sort_order': sort_order,
                    'is_active': True,
                }
            )

            if is_created:
                created += 1
            else:
                updated += 1

        except Exception as e:
            errors += 1
            print(f"エラー ({grade_name}): {e}")

    print(f"\n=== 結果 ===")
    print(f"作成: {created}")
    print(f"更新: {updated}")
    print(f"エラー: {errors}")

    # 確認
    final_count = Grade.objects.filter(tenant_id=tenant.id).count()
    print(f"\n=== 確認 ===")
    print(f"学年総数: {final_count}")

    # カテゴリ別集計
    print(f"\n=== カテゴリ別集計 ===")
    from django.db.models import Count
    categories = Grade.objects.filter(tenant_id=tenant.id).values('category').annotate(count=Count('id'))
    for cat in categories:
        print(f"  {cat['category']}: {cat['count']}件")

    # サンプル表示
    print(f"\n=== サンプル（最初の15件）===")
    for grade in Grade.objects.filter(tenant_id=tenant.id).order_by('sort_order')[:15]:
        print(f"  [{grade.grade_code}] {grade.grade_name} ({grade.category})")


if __name__ == '__main__':
    import_grades()

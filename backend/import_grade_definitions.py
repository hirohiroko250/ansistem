#!/usr/bin/env python
"""
対象学年定義システムのインポート
1. 単一学年マスタ（SchoolYear）: 23件
2. 対象学年定義（Grade）とその組み合わせ（GradeSchoolYear）
"""
import os
import sys
sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.schools.models import Grade, SchoolYear, GradeSchoolYear
from apps.tenants.models import Tenant


# 単一学年マスタ（23件）
# HTMLから抽出: 0-1歳児, 1-2歳児, 2-3歳児, 年少, 年中, 年長, 小１-小６, 中１-中３, 高１-高３, 大１-大４, 社会人
SCHOOL_YEAR_DATA = [
    # (sort_order, year_code, year_name, category)
    (1, 'Y01', '0-1歳児', 'infant'),
    (2, 'Y02', '1-2歳児', 'infant'),
    (3, 'Y03', '2-3歳児', 'infant'),
    (4, 'Y04', '年少', 'preschool'),
    (5, 'Y05', '年中', 'preschool'),
    (6, 'Y06', '年長', 'preschool'),
    (7, 'Y07', '小１', 'elementary'),
    (8, 'Y08', '小２', 'elementary'),
    (9, 'Y09', '小３', 'elementary'),
    (10, 'Y10', '小４', 'elementary'),
    (11, 'Y11', '小５', 'elementary'),
    (12, 'Y12', '小６', 'elementary'),
    (13, 'Y13', '中１', 'junior_high'),
    (14, 'Y14', '中２', 'junior_high'),
    (15, 'Y15', '中３', 'junior_high'),
    (16, 'Y16', '高１', 'high_school'),
    (17, 'Y17', '高２', 'high_school'),
    (18, 'Y18', '高３', 'high_school'),
    (19, 'Y19', '大１', 'university'),
    (20, 'Y20', '大２', 'university'),
    (21, 'Y21', '大３', 'university'),
    (22, 'Y22', '大４', 'university'),
    (23, 'Y23', '社会人', 'adult'),
]


# 対象学年定義データ（HTMLから抽出）
# (grade_id, grade_name, 含まれる単一学年のリスト)
# 含まれる学年は年齢順で判定
GRADE_DEFINITION_DATA = [
    (1, "1-2歳", ['1-2歳児']),
    (2, "1歳半から", ['1-2歳児', '2-3歳児']),  # 1歳半からなので1-2歳児と2-3歳児
    (3, "2-3歳", ['2-3歳児']),
    (4, "ALL", ['0-1歳児', '1-2歳児', '2-3歳児', '年少', '年中', '年長', '小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３', '大１', '大２', '大３', '大４', '社会人']),
    (5, "高１", ['高１']),
    (6, "高2", ['高２']),
    (7, "高3", ['高３']),
    (8, "高校生", ['高１', '高２', '高３']),
    (9, "小１", ['小１']),
    (10, "小１以上", ['小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３', '大１', '大２', '大３', '大４', '社会人']),
    (11, "小１-小３", ['小１', '小２', '小３']),
    (12, "小２", ['小２']),
    (13, "小３", ['小３']),
    (14, "小３-小６", ['小３', '小４', '小５', '小６']),
    (15, "小３-中１", ['小３', '小４', '小５', '小６', '中１']),
    (16, "小４", ['小４']),
    (17, "小４～小６", ['小４', '小５', '小６']),
    (18, "小5", ['小５']),
    (19, "小6", ['小６']),
    (20, "小６-高３", ['小６', '中１', '中２', '中３', '高１', '高２', '高３']),
    (21, "小学生", ['小１', '小２', '小３', '小４', '小５', '小６']),
    (22, "中１", ['中１']),
    (23, "中１～中３", ['中１', '中２', '中３']),
    (24, "中１・中２", ['中１', '中２']),
    (25, "中2", ['中２']),
    (26, "中3", ['中３']),
    (27, "中学生", ['中１', '中２', '中３']),
    (28, "年少", ['年少']),
    (29, "年中", ['年中']),
    (30, "年中・年長", ['年中', '年長']),
    (31, "年中以上", ['年中', '年長', '小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３', '大１', '大２', '大３', '大４', '社会人']),
    (32, "年中-小３", ['年中', '年長', '小１', '小２', '小３']),
    (33, "年長", ['年長']),
    (34, "幼児", ['年少', '年中', '年長']),
    (35, "幼児～小４", ['年少', '年中', '年長', '小１', '小２', '小３', '小４']),
    (36, "幼児以上", ['年少', '年中', '年長', '小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３', '大１', '大２', '大３', '大４', '社会人']),
    (37, "0歳～小１", ['0-1歳児', '1-2歳児', '2-3歳児', '年少', '年中', '年長', '小１']),
    (38, "小1-小4", ['小１', '小２', '小３', '小４']),
    (39, "小4～高3", ['小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３']),
    (40, "幼児～小３", ['年少', '年中', '年長', '小１', '小２', '小３']),
    (41, "小1～小5", ['小１', '小２', '小３', '小４', '小５']),
    (42, "年長～小6", ['年長', '小１', '小２', '小３', '小４', '小５', '小６']),
    (43, "小3-中3", ['小３', '小４', '小５', '小６', '中１', '中２', '中３']),
    (44, "年長～中3", ['年長', '小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３']),
    (45, "年長以上", ['年長', '小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３', '大１', '大２', '大３', '大４', '社会人']),
    (46, "中１＋小６", ['小６', '中１']),
    (47, "中学生＋小６", ['小６', '中１', '中２', '中３']),
    (48, "中3・高１", ['中３', '高１']),
    (50, "小4～中3", ['小４', '小５', '小６', '中１', '中２', '中３']),
    (51, "中学生以上", ['中１', '中２', '中３', '高１', '高２', '高３', '大１', '大２', '大３', '大４', '社会人']),
    (52, "0-1歳", ['0-1歳児']),
    (53, "高校生＋中3", ['中３', '高１', '高２', '高３']),
    (54, "年長～小2", ['年長', '小１', '小２']),
    (55, "社会人", ['社会人']),
    (56, "大学生以上", ['大１', '大２', '大３', '大４', '社会人']),
    (57, "2-3歳児～小3", ['2-3歳児', '年少', '年中', '年長', '小１', '小２', '小３']),
    (58, "小3-小4", ['小３', '小４']),
    (59, "小4-小5", ['小４', '小５']),
    (60, "小5-小6", ['小５', '小６']),
    (61, "小5～中3", ['小５', '小６', '中１', '中２', '中３']),
    (62, "小1～中3", ['小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３']),
    (63, "年長～小5", ['年長', '小１', '小２', '小３', '小４', '小５']),
    (64, "小3-小5", ['小３', '小４', '小５']),
    (65, "年少以上", ['年少', '年中', '年長', '小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３', '大１', '大２', '大３', '大４', '社会人']),
    (66, "年長～小３", ['年長', '小１', '小２', '小３']),
    (67, "年長～中学生", ['年長', '小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３']),
    (69, "Yellow年長含む", ['年長']),  # 特殊定義、年長のみ
    (71, "小１～中学生", ['小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３']),
    (72, "小3-高1", ['小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１']),
    (74, "中2＋中3", ['中２', '中３']),
    (76, "2-3歳児～幼児", ['2-3歳児', '年少', '年中', '年長']),
    (78, "小1～", ['小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３', '大１', '大２', '大３', '大４', '社会人']),
    (79, "小1～小6", ['小１', '小２', '小３', '小４', '小５', '小６']),
    (80, "年少～小2", ['年少', '年中', '年長', '小１', '小２']),
    (81, "年少～小３", ['年少', '年中', '年長', '小１', '小２', '小３']),
    (82, "年少～小6", ['年少', '年中', '年長', '小１', '小２', '小３', '小４', '小５', '小６']),
    (83, "年少～年長", ['年少', '年中', '年長']),
    (84, "年長～", ['年長', '小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３', '大１', '大２', '大３', '大４', '社会人']),
    (85, "年少～高校生", ['年少', '年中', '年長', '小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３']),
    (86, "小５-高３", ['小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３']),
    (87, "小3-高2", ['小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２']),
    (88, "高3", ['高３']),
    (89, "中1～高3", ['中１', '中２', '中３', '高１', '高２', '高３']),
]


def get_tenant():
    return Tenant.objects.get(tenant_code='OZA')


def import_school_years():
    """単一学年マスタ（23件）をインポート"""
    print("=" * 60)
    print("単一学年マスタインポート")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    created = 0
    updated = 0

    for sort_order, year_code, year_name, category in SCHOOL_YEAR_DATA:
        school_year, is_created = SchoolYear.objects.update_or_create(
            tenant_id=tenant.id,
            year_code=year_code,
            defaults={
                'year_name': year_name,
                'category': category,
                'sort_order': sort_order,
                'is_active': True,
            }
        )

        if is_created:
            created += 1
        else:
            updated += 1

    print(f"\n=== 結果 ===")
    print(f"作成: {created}")
    print(f"更新: {updated}")

    # 確認
    count = SchoolYear.objects.filter(tenant_id=tenant.id).count()
    print(f"単一学年総数: {count}")

    # サンプル表示
    print(f"\n=== 全件表示 ===")
    for sy in SchoolYear.objects.filter(tenant_id=tenant.id).order_by('sort_order'):
        print(f"  [{sy.year_code}] {sy.year_name} ({sy.category})")

    return True


def import_grade_definitions():
    """対象学年定義をインポート"""
    print("\n" + "=" * 60)
    print("対象学年定義インポート")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    # 単一学年の名前→IDマッピングを取得
    school_years = {sy.year_name: sy for sy in SchoolYear.objects.filter(tenant_id=tenant.id)}
    print(f"単一学年マスタ: {len(school_years)}件")

    # 既存のGradeを削除（再構築）
    existing_count = Grade.objects.filter(tenant_id=tenant.id).count()
    if existing_count > 0:
        print(f"既存の対象学年定義を削除: {existing_count}件")
        GradeSchoolYear.objects.filter(grade__tenant_id=tenant.id).delete()
        Grade.objects.filter(tenant_id=tenant.id).delete()

    created_grades = 0
    created_relations = 0
    errors = []

    for grade_id, grade_name, year_names in GRADE_DEFINITION_DATA:
        try:
            grade_code = f"G{grade_id:03d}"

            # カテゴリを推定
            if any(k in grade_name for k in ['0歳', '1歳', '2歳', '3歳']):
                category = 'infant'
            elif any(k in grade_name for k in ['幼児', '年少', '年中', '年長']) and '小' not in grade_name and '中' not in grade_name:
                category = 'preschool'
            elif any(k in grade_name for k in ['小']) and '中' not in grade_name and '高' not in grade_name:
                category = 'elementary'
            elif any(k in grade_name for k in ['中']) and '高' not in grade_name and '小' not in grade_name:
                category = 'junior_high'
            elif any(k in grade_name for k in ['高']) and '中' not in grade_name and '小' not in grade_name:
                category = 'high_school'
            elif any(k in grade_name for k in ['大学', '社会人']):
                category = 'adult'
            elif grade_name == 'ALL' or '以上' in grade_name:
                category = 'all'
            else:
                category = 'mixed'

            # Grade作成
            grade = Grade.objects.create(
                tenant_id=tenant.id,
                grade_code=grade_code,
                grade_name=grade_name,
                grade_name_short=grade_name[:10] if len(grade_name) > 10 else grade_name,
                category=category,
                sort_order=grade_id,
                is_active=True,
            )
            created_grades += 1

            # GradeSchoolYear関連作成
            for year_name in year_names:
                if year_name in school_years:
                    GradeSchoolYear.objects.create(
                        tenant_id=tenant.id,
                        grade=grade,
                        school_year=school_years[year_name],
                    )
                    created_relations += 1
                else:
                    errors.append(f"単一学年 '{year_name}' が見つかりません (定義: {grade_name})")

        except Exception as e:
            errors.append(f"エラー ({grade_name}): {e}")

    print(f"\n=== 結果 ===")
    print(f"対象学年定義作成: {created_grades}")
    print(f"関連レコード作成: {created_relations}")

    if errors:
        print(f"\n=== エラー ({len(errors)}件) ===")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... 他 {len(errors) - 10}件")

    # 確認
    grade_count = Grade.objects.filter(tenant_id=tenant.id).count()
    relation_count = GradeSchoolYear.objects.filter(grade__tenant_id=tenant.id).count()
    print(f"\n=== 確認 ===")
    print(f"対象学年定義総数: {grade_count}")
    print(f"関連レコード総数: {relation_count}")

    # サンプル表示
    print(f"\n=== サンプル（最初の10件）===")
    for grade in Grade.objects.filter(tenant_id=tenant.id).order_by('sort_order')[:10]:
        years = list(grade.school_years.values_list('year_name', flat=True))
        print(f"  [{grade.grade_code}] {grade.grade_name}")
        print(f"       → {', '.join(years)}")


if __name__ == '__main__':
    import_school_years()
    import_grade_definitions()

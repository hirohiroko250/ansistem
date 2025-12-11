"""
T17学年定義インポートスクリプト
Excel: T17_学年定義_修正版.xlsx

使い方:
docker exec -it ansystem_backend python manage.py shell < scripts/import_t17_grades.py
"""
import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.schools.models import Grade, SchoolYear, GradeSchoolYear
from apps.tenants.models import Tenant
import uuid

# テナント取得
tenant = Tenant.objects.first()
if not tenant:
    print("ERROR: テナントが見つかりません")
    sys.exit(1)

print(f"テナント: {tenant.tenant_name} ({tenant.id})")

# 単一学年データ（26種類）
SCHOOL_YEARS = [
    # (year_code, year_name, category, sort_order)
    ('SY01', '１歳', 'infant', 1),
    ('SY02', '１歳半', 'infant', 2),
    ('SY03', '２歳', 'infant', 3),
    ('SY04', '２歳半', 'infant', 4),
    ('SY05', '３歳', 'preschool', 5),
    ('SY06', '年少', 'preschool', 6),
    ('SY07', '年中', 'preschool', 7),
    ('SY08', '年長', 'preschool', 8),
    ('SY09', '小１', 'elementary', 9),
    ('SY10', '小２', 'elementary', 10),
    ('SY11', '小３', 'elementary', 11),
    ('SY12', '小４', 'elementary', 12),
    ('SY13', '小５', 'elementary', 13),
    ('SY14', '小６', 'elementary', 14),
    ('SY15', '中１', 'junior_high', 15),
    ('SY16', '中２', 'junior_high', 16),
    ('SY17', '中３', 'junior_high', 17),
    ('SY18', '高１', 'high_school', 18),
    ('SY19', '高２', 'high_school', 19),
    ('SY20', '高３', 'high_school', 20),
    ('SY21', '大専１', 'university', 21),
    ('SY22', '大専２', 'university', 22),
    ('SY23', '大専３', 'university', 23),
    ('SY24', '大専４', 'university', 24),
    ('SY25', '社会人', 'adult', 25),
    ('SY26', 'プラチナ世代', 'adult', 26),
]

# 対象学年定義データ（73種類）と対応する単一学年
GRADES = [
    # (grade_code, grade_name, grade_name_short, [school_year_names], sort_order)
    ('GR001', '中3', '中3', ['中３'], 1),
    ('GR002', '小2', '小2', ['小２'], 2),
    ('GR003', '1歳～小2', '1歳～小2', ['１歳', '１歳半', '２歳', '２歳半', '３歳', '年少', '年中', '年長', '小１', '小２'], 3),
    ('GR004', '小3～小6', '小3～小6', ['小３', '小４', '小５', '小６'], 4),
    ('GR005', '1歳半', '1歳半', ['１歳半'], 5),
    ('GR006', '年少', '年少', ['年少'], 6),
    ('GR007', '年中', '年中', ['年中'], 7),
    ('GR008', '年長', '年長', ['年長'], 8),
    ('GR009', '小1', '小1', ['小１'], 9),
    ('GR010', '小3', '小3', ['小３'], 10),
    ('GR011', '小4', '小4', ['小４'], 11),
    ('GR012', '小5', '小5', ['小５'], 12),
    ('GR013', '小6', '小6', ['小６'], 13),
    ('GR014', '中1', '中1', ['中１'], 14),
    ('GR015', '中2', '中2', ['中２'], 15),
    ('GR016', '高1', '高1', ['高１'], 16),
    ('GR017', '高2', '高2', ['高２'], 17),
    ('GR018', '高3', '高3', ['高３'], 18),
    ('GR019', '大学生', '大学生', ['大専１', '大専２', '大専３', '大専４'], 19),
    ('GR020', '社会人', '社会人', ['社会人'], 20),
    ('GR021', 'プラチナ世代', 'プラチナ', ['プラチナ世代'], 21),
    ('GR022', '1歳', '1歳', ['１歳'], 22),
    ('GR023', '2歳', '2歳', ['２歳'], 23),
    ('GR024', '2歳半', '2歳半', ['２歳半'], 24),
    ('GR025', '3歳', '3歳', ['３歳'], 25),
    ('GR026', '年少～年長', '年少～年長', ['年少', '年中', '年長'], 26),
    ('GR027', '小1～小2', '小1～小2', ['小１', '小２'], 27),
    ('GR028', '小1～小3', '小1～小3', ['小１', '小２', '小３'], 28),
    ('GR029', '小1～小4', '小1～小4', ['小１', '小２', '小３', '小４'], 29),
    ('GR030', '小1～小6', '小1～小6', ['小１', '小２', '小３', '小４', '小５', '小６'], 30),
    ('GR031', '小2～小3', '小2～小3', ['小２', '小３'], 31),
    ('GR032', '小2～小4', '小2～小4', ['小２', '小３', '小４'], 32),
    ('GR033', '小2～小6', '小2～小6', ['小２', '小３', '小４', '小５', '小６'], 33),
    ('GR034', '小3～小4', '小3～小4', ['小３', '小４'], 34),
    ('GR035', '小3～小5', '小3～小5', ['小３', '小４', '小５'], 35),
    ('GR036', '小4～小5', '小4～小5', ['小４', '小５'], 36),
    ('GR037', '小4～小6', '小4～小6', ['小４', '小５', '小６'], 37),
    ('GR038', '小5～小6', '小5～小6', ['小５', '小６'], 38),
    ('GR039', '小5～中1', '小5～中1', ['小５', '小６', '中１'], 39),
    ('GR040', '小5～中2', '小5～中2', ['小５', '小６', '中１', '中２'], 40),
    ('GR041', '小5～中3', '小5～中3', ['小５', '小６', '中１', '中２', '中３'], 41),
    ('GR042', '小6～中1', '小6～中1', ['小６', '中１'], 42),
    ('GR043', '小6～中2', '小6～中2', ['小６', '中１', '中２'], 43),
    ('GR044', '小6～中3', '小6～中3', ['小６', '中１', '中２', '中３'], 44),
    ('GR045', '中1～中2', '中1～中2', ['中１', '中２'], 45),
    ('GR046', '中1～中3', '中1～中3', ['中１', '中２', '中３'], 46),
    ('GR047', '中2～中3', '中2～中3', ['中２', '中３'], 47),
    ('GR048', '中1～高1', '中1～高1', ['中１', '中２', '中３', '高１'], 48),
    ('GR049', '中1～高2', '中1～高2', ['中１', '中２', '中３', '高１', '高２'], 49),
    ('GR050', '中1～高3', '中1～高3', ['中１', '中２', '中３', '高１', '高２', '高３'], 50),
    ('GR051', '高1～高2', '高1～高2', ['高１', '高２'], 51),
    ('GR052', '高1～高3', '高1～高3', ['高１', '高２', '高３'], 52),
    ('GR053', '高2～高3', '高2～高3', ['高２', '高３'], 53),
    ('GR054', '高校生～社会人', '高～社会人', ['高１', '高２', '高３', '大専１', '大専２', '大専３', '大専４', '社会人'], 54),
    ('GR055', '大学生～社会人', '大～社会人', ['大専１', '大専２', '大専３', '大専４', '社会人'], 55),
    ('GR056', '年長～小1', '年長～小1', ['年長', '小１'], 56),
    ('GR057', '年長～小2', '年長～小2', ['年長', '小１', '小２'], 57),
    ('GR058', '年長～小3', '年長～小3', ['年長', '小１', '小２', '小３'], 58),
    ('GR059', '年中～年長', '年中～年長', ['年中', '年長'], 59),
    ('GR060', '年中～小1', '年中～小1', ['年中', '年長', '小１'], 60),
    ('GR061', '年中～小2', '年中～小2', ['年中', '年長', '小１', '小２'], 61),
    ('GR062', '年少～小1', '年少～小1', ['年少', '年中', '年長', '小１'], 62),
    ('GR063', '年少～小2', '年少～小2', ['年少', '年中', '年長', '小１', '小２'], 63),
    ('GR064', '3歳～年少', '3歳～年少', ['３歳', '年少'], 64),
    ('GR065', '2歳半～年少', '2歳半～年少', ['２歳半', '３歳', '年少'], 65),
    ('GR066', '2歳～年少', '2歳～年少', ['２歳', '２歳半', '３歳', '年少'], 66),
    ('GR067', '1歳半～2歳半', '1歳半～2歳半', ['１歳半', '２歳', '２歳半'], 67),
    ('GR068', '1歳～2歳', '1歳～2歳', ['１歳', '１歳半', '２歳'], 68),
    ('GR069', '1歳～3歳', '1歳～3歳', ['１歳', '１歳半', '２歳', '２歳半', '３歳'], 69),
    ('GR070', '1歳～年少', '1歳～年少', ['１歳', '１歳半', '２歳', '２歳半', '３歳', '年少'], 70),
    ('GR071', '1歳～年中', '1歳～年中', ['１歳', '１歳半', '２歳', '２歳半', '３歳', '年少', '年中'], 71),
    ('GR072', '1歳～年長', '1歳～年長', ['１歳', '１歳半', '２歳', '２歳半', '３歳', '年少', '年中', '年長'], 72),
    ('GR073', '全学年', '全学年', ['１歳', '１歳半', '２歳', '２歳半', '３歳', '年少', '年中', '年長', '小１', '小２', '小３', '小４', '小５', '小６', '中１', '中２', '中３', '高１', '高２', '高３', '大専１', '大専２', '大専３', '大専４', '社会人', 'プラチナ世代'], 73),
]

# インポート処理
print("\n=== 単一学年（SchoolYear）インポート ===")
school_year_map = {}  # year_name -> SchoolYear オブジェクト
sy_created = 0
sy_updated = 0

for year_code, year_name, category, sort_order in SCHOOL_YEARS:
    obj, created = SchoolYear.objects.update_or_create(
        tenant_id=tenant.id,
        year_code=year_code,
        defaults={
            'year_name': year_name,
            'category': category,
            'sort_order': sort_order,
            'is_active': True,
            'tenant_ref': tenant,
        }
    )
    school_year_map[year_name] = obj
    if created:
        sy_created += 1
    else:
        sy_updated += 1

print(f"作成: {sy_created}, 更新: {sy_updated}")

print("\n=== 対象学年（Grade）インポート ===")
gr_created = 0
gr_updated = 0
mapping_created = 0

for grade_code, grade_name, grade_name_short, school_year_names, sort_order in GRADES:
    grade, created = Grade.objects.update_or_create(
        tenant_id=tenant.id,
        grade_code=grade_code,
        defaults={
            'grade_name': grade_name,
            'grade_name_short': grade_name_short,
            'sort_order': sort_order,
            'is_active': True,
            'tenant_ref': tenant,
        }
    )

    if created:
        gr_created += 1
    else:
        gr_updated += 1

    # 既存のマッピングを削除
    GradeSchoolYear.objects.filter(tenant_id=tenant.id, grade=grade).delete()

    # 新しいマッピングを作成
    for sy_name in school_year_names:
        if sy_name in school_year_map:
            GradeSchoolYear.objects.create(
                tenant_id=tenant.id,
                tenant_ref=tenant,
                grade=grade,
                school_year=school_year_map[sy_name]
            )
            mapping_created += 1
        else:
            print(f"WARNING: 単一学年 '{sy_name}' が見つかりません（{grade_name}）")

print(f"作成: {gr_created}, 更新: {gr_updated}")
print(f"マッピング作成: {mapping_created}")

print("\n=== インポート完了 ===")
print(f"単一学年: {SchoolYear.objects.filter(tenant_id=tenant.id).count()}件")
print(f"対象学年: {Grade.objects.filter(tenant_id=tenant.id).count()}件")
print(f"マッピング: {GradeSchoolYear.objects.filter(tenant_id=tenant.id).count()}件")

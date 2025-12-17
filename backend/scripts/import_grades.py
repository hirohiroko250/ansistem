"""
学年定義インポートスクリプト (T17)
使用方法: docker compose run --rm backend python scripts/import_grades.py <xlsx_path>
"""
import sys
import os
import django
import openpyxl

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.schools.models import SchoolYear, Grade, GradeSchoolYear
from apps.tenants.models import Tenant


# 単一学年の定義（ヘッダーの順番に対応）
SCHOOL_YEAR_DEFINITIONS = [
    # (code, name, category, sort_order)
    ('1Y', '１歳', 'infant', 1),
    ('1Y5', '１歳半', 'infant', 2),
    ('2Y', '２歳', 'infant', 3),
    ('2Y5', '２歳半', 'infant', 4),
    ('3Y', '３歳', 'infant', 5),
    ('NS', '年少', 'preschool', 6),
    ('NC', '年中', 'preschool', 7),
    ('NL', '年長', 'preschool', 8),
    ('E1', '小１', 'elementary', 9),
    ('E2', '小２', 'elementary', 10),
    ('E3', '小３', 'elementary', 11),
    ('E4', '小４', 'elementary', 12),
    ('E5', '小５', 'elementary', 13),
    ('E6', '小６', 'elementary', 14),
    ('J1', '中１', 'junior_high', 15),
    ('J2', '中２', 'junior_high', 16),
    ('J3', '中３', 'junior_high', 17),
    ('H1', '高１', 'high', 18),
    ('H2', '高２', 'high', 19),
    ('H3', '高３', 'high', 20),
    ('U1', '大専１', 'university', 21),
    ('U2', '大専２', 'university', 22),
    ('U3', '大専３', 'university', 23),
    ('U4', '大専４', 'university', 24),
    ('AD', '社会人', 'adult', 25),
    ('PT', 'プラチナ世代', 'platinum', 26),
]

# 列インデックスから単一学年コードへのマッピング（ヘッダー行のインデックス1〜26）
COLUMN_TO_SCHOOL_YEAR = {
    1: '1Y',    # １歳
    2: '1Y5',   # １歳半
    3: '2Y',    # ２歳
    4: '2Y5',   # ２歳半
    5: '3Y',    # ３歳
    6: 'NS',    # 年少
    7: 'NC',    # 年中
    8: 'NL',    # 年長
    9: 'E1',    # 小１
    10: 'E2',   # 小２
    11: 'E3',   # 小３
    12: 'E4',   # 小４
    13: 'E5',   # 小５
    14: 'E6',   # 小６
    15: 'J1',   # 中１
    16: 'J2',   # 中２
    17: 'J3',   # 中３
    18: 'H1',   # 高１
    19: 'H2',   # 高２
    20: 'H3',   # 高３
    21: 'U1',   # 大専１
    22: 'U2',   # 大専２
    23: 'U3',   # 大専３
    24: 'U4',   # 大専４
    25: 'AD',   # 社会人
    26: 'PT',   # プラチナ世代
}


def normalize_grade_name(name):
    """学年名を正規化"""
    if not name:
        return ''
    # 全角を半角に
    name = name.strip()
    # よくある表記ゆれを統一
    replacements = {
        '〜': '～',
        '−': '～',
        '-': '～',
        '―': '～',
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name


def generate_grade_code(grade_name):
    """学年名からコードを生成"""
    # 正規化
    name = normalize_grade_name(grade_name)

    # 特定のパターン
    if name == '中3' or name == '中３':
        return 'J3'
    if name == '小2' or name == '小２':
        return 'E2'
    if name == '小3' or name == '小３':
        return 'E3'
    if name == '高１' or name == '高1':
        return 'H1'
    if name == '年少':
        return 'NS'
    if name == '年中':
        return 'NC'
    if name == '年長':
        return 'NL'

    # 範囲を含む場合
    if '～' in name:
        parts = name.split('～')
        start = parts[0].strip()
        end = parts[1].strip() if len(parts) > 1 else ''

        # 開始と終了のコードを取得
        start_code = generate_grade_code(start) if start else ''
        end_code = generate_grade_code(end) if end else ''

        if start_code and end_code:
            return f"{start_code}_{end_code}"
        elif start_code:
            return f"{start_code}_UP"  # ～以降
        elif end_code:
            return f"START_{end_code}"

    # 単純なマッピング
    simple_map = {
        '１歳': '1Y', '1歳': '1Y',
        '１歳半': '1Y5', '1歳半': '1Y5',
        '２歳': '2Y', '2歳': '2Y',
        '２歳半': '2Y5', '2歳半': '2Y5',
        '３歳': '3Y', '3歳': '3Y',
        '年少': 'NS',
        '年中': 'NC', '年中～': 'NC_UP',
        '年長': 'NL',
        '小１': 'E1', '小1': 'E1',
        '小２': 'E2', '小2': 'E2',
        '小３': 'E3', '小3': 'E3',
        '小４': 'E4', '小4': 'E4',
        '小５': 'E5', '小5': 'E5',
        '小６': 'E6', '小6': 'E6',
        '中１': 'J1', '中1': 'J1',
        '中２': 'J2', '中2': 'J2',
        '中３': 'J3', '中3': 'J3',
        '高１': 'H1', '高1': 'H1',
        '高２': 'H2', '高2': 'H2',
        '高３': 'H3', '高3': 'H3',
        '大専１': 'U1', '大専1': 'U1',
        '大専２': 'U2', '大専2': 'U2',
        '大専３': 'U3', '大専3': 'U3',
        '大専４': 'U4', '大専4': 'U4',
        '社会人': 'AD',
        'プラチナ世代': 'PT',
    }

    if name in simple_map:
        return simple_map[name]

    # 見つからない場合は名前からハッシュ
    return f"G{abs(hash(name)) % 10000:04d}"


def import_grades(xlsx_path):
    """学年定義をインポート"""

    # テナント取得
    tenant = Tenant.objects.filter(tenant_code='100000').first()
    if not tenant:
        print("エラー: アンイングリッシュグループテナントが見つかりません")
        sys.exit(1)
    tenant_id = tenant.id
    print(f"テナント: {tenant.tenant_name} ({tenant_id})")

    # 1. 単一学年（SchoolYear）を作成
    print("\n=== 単一学年の作成 ===")
    school_year_map = {}
    for code, name, category, sort_order in SCHOOL_YEAR_DEFINITIONS:
        sy, created = SchoolYear.objects.get_or_create(
            tenant_id=tenant_id,
            year_code=code,
            defaults={
                'year_name': name,
                'category': category,
                'sort_order': sort_order,
                'is_active': True,
            }
        )
        school_year_map[code] = sy
        school_year_map[name] = sy
        if created:
            print(f"  作成: {code} - {name}")
        else:
            print(f"  既存: {code} - {name}")

    # 2. Excelから対象学年定義をインポート
    print("\n=== 対象学年定義の作成 ===")
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb['T17_学年定義_修正版']

    imported_grades = 0
    imported_relations = 0
    errors = []

    for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
        try:
            # 授業対象（学年名）
            grade_name = str(row[0].value).strip() if row[0].value else ''
            if not grade_name:
                continue

            # 正規化
            grade_name = normalize_grade_name(grade_name)

            # コード生成
            grade_code = generate_grade_code(grade_name)

            # 対象学年定義を作成
            grade, created = Grade.objects.get_or_create(
                tenant_id=tenant_id,
                grade_code=grade_code,
                defaults={
                    'grade_name': grade_name,
                    'grade_name_short': grade_name[:20] if len(grade_name) > 20 else grade_name,
                    'sort_order': row_num,
                    'is_active': True,
                }
            )

            if created:
                imported_grades += 1

            # 関連する単一学年を検出（列1〜26をチェック）
            for col_idx in range(1, 27):
                if col_idx >= len(row):
                    break
                cell_value = row[col_idx].value
                if cell_value and str(cell_value).strip():
                    # この列に値がある = この単一学年が含まれる
                    sy_code = COLUMN_TO_SCHOOL_YEAR.get(col_idx)
                    if sy_code and sy_code in school_year_map:
                        school_year = school_year_map[sy_code]
                        # 関連を作成
                        rel, rel_created = GradeSchoolYear.objects.get_or_create(
                            tenant_id=tenant_id,
                            grade=grade,
                            school_year=school_year,
                        )
                        if rel_created:
                            imported_relations += 1

            if imported_grades % 50 == 0 and imported_grades > 0:
                print(f"  処理中... {imported_grades} 件")

        except Exception as e:
            errors.append(f"行 {row_num}: {grade_name} - {str(e)}")
            continue

    return len(SCHOOL_YEAR_DEFINITIONS), imported_grades, imported_relations, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_grades.py <xlsx_path>")
        sys.exit(1)

    xlsx_path = sys.argv[1]

    if not os.path.exists(xlsx_path):
        print(f"エラー: ファイルが見つかりません: {xlsx_path}")
        sys.exit(1)

    print(f"インポート開始: {xlsx_path}")
    print("-" * 50)

    sy_count, grade_count, rel_count, errors = import_grades(xlsx_path)

    print("-" * 50)
    print(f"完了!")
    print(f"  単一学年: {sy_count} 件")
    print(f"  対象学年定義: {grade_count} 件")
    print(f"  学年関連: {rel_count} 件")

    if errors:
        print(f"  エラー: {len(errors)} 件")
        for error in errors[:10]:
            print(f"    - {error}")
        if len(errors) > 10:
            print(f"    ... 他 {len(errors) - 10} 件")

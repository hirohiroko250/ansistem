"""
生徒所属データインポートスクリプト (UserClassList)
使用方法: docker compose run --rm backend python scripts/import_student_schools.py <xlsx_path>
"""
import sys
import os
import django
import openpyxl
from datetime import datetime, time

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.students.models import Student, StudentSchool
from apps.schools.models import School, Brand, ClassSchedule
from apps.tenants.models import Tenant


# サクセス系ブランド
SUCCESS_BRANDS = {
    'AES', 'AGS', 'BMS', 'FES', 'GOK', 'MPS', 'MWS', 'PRS',
    'SCC', 'SEL', 'SFE', 'SFJ', 'SHI', 'SHS', 'SJJ', 'SJU',
    'SKC', 'SKK', 'SOS', 'SUC', 'SHO', 'SEK',
}


def parse_date(value):
    """日付パース"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()
    except:
        try:
            return datetime.strptime(str(value)[:10], '%Y/%m/%d').date()
        except:
            return None


def parse_time(value):
    """時間パース"""
    if not value:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    try:
        parts = str(value).split(':')
        return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except:
        return None


def day_to_int(day_str):
    """曜日文字列を整数に変換"""
    mapping = {
        '月': 1, '火': 2, '水': 3, '木': 4, '金': 5, '土': 6, '日': 7
    }
    return mapping.get(day_str, None)


def is_success_brand(brand_code):
    """サクセス系ブランドかどうか"""
    if not brand_code:
        return False
    return brand_code in SUCCESS_BRANDS


def import_student_schools(xlsx_path):
    """生徒所属をインポート"""

    # テナント取得
    an_tenant = Tenant.objects.filter(tenant_code='100000').first()
    teraco_tenant = Tenant.objects.filter(tenant_code='101615').first()

    if not an_tenant or not teraco_tenant:
        print("エラー: テナントが見つかりません")
        sys.exit(1)

    print(f"アンイングリッシュグループ: {an_tenant.id}")
    print(f"株式会社TE・RA・CO: {teraco_tenant.id}")

    # 生徒マップ（student_no → Student）
    student_map = {}
    for s in Student.objects.all():
        student_map[s.student_no] = s
        if s.old_id:
            student_map[str(s.old_id)] = s
    print(f"生徒マップ: {len(student_map)} 件")

    # 校舎マップ
    school_map = {}
    for s in School.objects.all():
        school_map[s.school_code] = s
        # S0001形式でもマッピング
        if s.school_code.isdigit():
            school_map[f'S{int(s.school_code):04d}'] = s
        # S10001 -> S0001 のマッピングも追加
        if s.school_code.startswith('S1'):
            alt_code = 'S0' + s.school_code[2:]
            school_map[alt_code] = s
    print(f"校舎マップ: {len(school_map)} 件")

    # ブランドマップ
    brand_map = {}
    for b in Brand.objects.all():
        brand_map[b.brand_code] = b
        brand_map[b.brand_name] = b
    # プレフィックス付きブランドをマッピング
    prefix_mapping = {
        '【星煌学院】アンイングリッシュクラブ': 'アンイングリッシュクラブ',
        '【星煌学院】アンそろばんクラブ': 'アンそろばんクラブ',
        '【星煌学院】アンプログラミングクラブ': 'アンプログラミングクラブ',
        '【星煌学院】アン美文字クラブ': 'アン美文字クラブ',
        '【星煌学院】アンさんこくキッズ': 'アンさんこくキッズ',
        '【キタン塾】アンイングリッシュクラブ': 'アンイングリッシュクラブ',
    }
    for prefixed, base in prefix_mapping.items():
        if base in brand_map:
            brand_map[prefixed] = brand_map[base]
    print(f"ブランドマップ: {len(brand_map)} 件")

    # クラススケジュールマップ
    schedule_map = {}
    for cs in ClassSchedule.objects.all():
        schedule_map[cs.schedule_code] = cs
    print(f"クラススケジュールマップ: {len(schedule_map)} 件")

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb['クラス一覧']

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    # 重複チェック用
    existing_keys = set()
    for ss in StudentSchool.objects.all():
        key = (str(ss.student_id), str(ss.school_id), str(ss.brand_id))
        existing_keys.add(key)

    # 処理済みキー（同Excel内重複防止）
    processed_keys = set()

    for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
        try:
            # 生徒ID（列13）
            student_no = str(row[13].value).strip() if row[13].value else ''
            if not student_no:
                skipped += 1
                continue

            # 生徒を検索
            student = student_map.get(student_no)
            if not student:
                skipped += 1
                continue

            # ブランド名（列25）
            brand_name = str(row[25].value).strip() if row[25].value else ''
            brand = brand_map.get(brand_name)
            if not brand:
                skipped += 1
                continue

            # テナント決定
            if is_success_brand(brand.brand_code):
                tenant_id = teraco_tenant.id
            else:
                tenant_id = an_tenant.id

            # 校舎ID（列30）
            school_id = str(row[30].value).strip() if row[30].value else ''
            school = school_map.get(school_id)
            if not school:
                # S0XXX → S10XXX 形式に変換してリトライ (S0001 -> S10001)
                if school_id.startswith('S0'):
                    school_id_alt = 'S10' + school_id[2:]
                    school = school_map.get(school_id_alt)

            if not school:
                skipped += 1
                continue

            # 重複チェック
            key = (str(student.id), str(school.id), str(brand.id))
            if key in existing_keys or key in processed_keys:
                skipped += 1
                continue
            processed_keys.add(key)

            # 曜日（列32）
            day_str = str(row[32].value).strip() if row[32].value else ''
            day_of_week = day_to_int(day_str)

            # 開始時間（列34）
            start_time = parse_time(row[34].value)

            # ユーザークラス開始日（列35）
            start_date = parse_date(row[35].value)
            if not start_date:
                # 開始日（列20）を使用
                start_date = parse_date(row[20].value)

            if not start_date:
                skipped += 1
                continue

            # 終了日は入れない
            end_date = None

            # 在籍状況は全員active
            enrollment_status = 'active'

            # 選択クラスID（列22）- ClassScheduleの検索用
            class_id = str(row[22].value).strip() if row[22].value else ''
            class_schedule = None
            if class_id:
                class_schedule = schedule_map.get(class_id)

            # 新規作成
            StudentSchool.objects.create(
                tenant_id=tenant_id,
                student=student,
                school=school,
                brand=brand,
                enrollment_status=enrollment_status,
                start_date=start_date,
                end_date=end_date,
                day_of_week=day_of_week,
                start_time=start_time,
                class_schedule=class_schedule,
                is_primary=False,
            )
            imported += 1

            if imported % 500 == 0:
                print(f"  処理中... {imported} 件")

        except Exception as e:
            errors.append(f"行 {row_num}: {student_no} - {str(e)}")
            continue

    return imported, updated, skipped, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_student_schools.py <xlsx_path>")
        sys.exit(1)

    xlsx_path = sys.argv[1]

    if not os.path.exists(xlsx_path):
        print(f"エラー: ファイルが見つかりません: {xlsx_path}")
        sys.exit(1)

    print(f"インポート開始: {xlsx_path}")
    print("-" * 50)

    imported, updated, skipped, errors = import_student_schools(xlsx_path)

    print("-" * 50)
    print(f"完了!")
    print(f"  新規作成: {imported} 件")
    print(f"  更新: {updated} 件")
    print(f"  スキップ: {skipped} 件")

    if errors:
        print(f"  エラー: {len(errors)} 件")
        for error in errors[:10]:
            print(f"    - {error}")
        if len(errors) > 10:
            print(f"    ... 他 {len(errors) - 10} 件")

"""
開講時間割データインポートスクリプト (T14)
使用方法: docker compose run --rm backend python scripts/import_class_schedule.py <xlsx_path>
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

from apps.schools.models import (
    ClassSchedule, School, Brand, BrandCategory, Classroom,
    CalendarMaster
)
from apps.tenants.models import Tenant


def parse_time(value):
    """時間パース"""
    if not value:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    try:
        # "19:00:00" 形式
        parts = str(value).split(':')
        return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except:
        return None


def parse_date(value):
    """日付パース"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()
    except:
        return None


def day_of_week_to_int(day_str):
    """曜日文字列を整数に変換"""
    mapping = {
        '月': 1, '火': 2, '水': 3, '木': 4, '金': 5, '土': 6, '日': 7
    }
    return mapping.get(day_str, 1)


def import_class_schedules(xlsx_path):
    """開講時間割をインポート"""

    # テナント取得
    tenant = Tenant.objects.filter(tenant_code='100000').first()
    if not tenant:
        print("エラー: アンイングリッシュグループテナントが見つかりません")
        sys.exit(1)
    tenant_id = tenant.id
    print(f"テナント: {tenant.tenant_name} ({tenant_id})")

    # 校舎マップ
    school_map = {}
    for s in School.objects.filter(tenant_id=tenant_id):
        school_map[s.school_code] = s
    print(f"校舎マップ: {len(school_map)} 件")

    # ブランドマップ
    brand_map = {}
    for b in Brand.objects.filter(tenant_id=tenant_id):
        brand_map[b.brand_code] = b
    print(f"ブランドマップ: {len(brand_map)} 件")

    # ブランドカテゴリマップ
    category_map = {}
    for c in BrandCategory.objects.filter(tenant_id=tenant_id):
        category_map[c.category_code] = c

    # ブランド→カテゴリマップ
    brand_to_category = {}
    for b in Brand.objects.filter(tenant_id=tenant_id).select_related('category'):
        if b.category:
            brand_to_category[b.brand_code] = b.category

    # 教室マップ
    classroom_map = {}
    for c in Classroom.objects.filter(tenant_id=tenant_id):
        key = f"{c.school.school_code}_{c.classroom_name}"
        classroom_map[key] = c
    print(f"教室マップ: {len(classroom_map)} 件")

    # カレンダーマスターマップ
    calendar_master_map = {}
    for cm in CalendarMaster.objects.filter(tenant_id=tenant_id):
        calendar_master_map[cm.code] = cm

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb['T14_開講時間割_ 時間割Group版']

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    for row_num, row in enumerate(ws.iter_rows(min_row=3), start=3):
        try:
            # 社内時間割ID（ユニークキー）
            schedule_code = str(row[13].value).strip() if row[13].value else ''
            if not schedule_code:
                continue

            # 校舎
            school_code = str(row[15].value).strip() if row[15].value else ''
            school = school_map.get(school_code)
            if not school:
                skipped += 1
                continue

            # ブランド
            brand_code = str(row[18].value).strip() if row[18].value else ''
            brand = brand_map.get(brand_code)
            if not brand:
                skipped += 1
                continue

            # ブランドカテゴリ
            brand_category = brand_to_category.get(brand_code)

            # 曜日
            day_str = str(row[32].value).strip() if row[32].value else ''
            day_of_week = day_of_week_to_int(day_str)

            # 時限
            period = row[34].value
            try:
                period = int(period) if period else 1
            except:
                period = 1

            # 時間
            start_time = parse_time(row[35].value)
            duration = row[36].value
            end_time = parse_time(row[37].value)
            break_time = parse_time(row[38].value)

            try:
                duration_minutes = int(duration) if duration else 50
            except:
                duration_minutes = 50

            if not start_time:
                start_time = time(0, 0)
            if not end_time:
                end_time = time(0, 50)

            # クラス情報
            class_name = str(row[24].value).strip() if row[24].value else ''
            class_type = str(row[29].value).strip() if row[29].value else ''
            display_course_name = str(row[21].value).strip() if row[21].value else ''
            display_pair_name = str(row[22].value).strip() if row[22].value else ''
            display_description = str(row[23].value).strip() if row[23].value else ''
            ticket_name = str(row[25].value).strip() if row[25].value else ''
            ticket_id = str(row[26].value).strip() if row[26].value else ''
            transfer_group = str(row[27].value).strip() if row[27].value else ''
            schedule_group = str(row[28].value).strip() if row[28].value else ''

            # 席数
            capacity = row[39].value
            trial_capacity = row[40].value
            pause_seat_fee = row[41].value

            try:
                capacity = int(capacity) if capacity else 12
            except:
                capacity = 12

            try:
                trial_capacity = int(trial_capacity) if trial_capacity else 2
            except:
                trial_capacity = 2

            try:
                pause_seat_fee = int(pause_seat_fee) if pause_seat_fee else 0
            except:
                pause_seat_fee = 0

            # カレンダーパターン
            calendar_pattern = str(row[42].value).strip() if row[42].value else ''

            # カレンダーマスター
            calendar_master = None
            if calendar_pattern:
                if calendar_pattern not in calendar_master_map:
                    calendar_master, _ = CalendarMaster.objects.get_or_create(
                        tenant_id=tenant_id,
                        code=calendar_pattern,
                        defaults={
                            'name': calendar_pattern,
                            'brand': brand,
                            'lesson_type': CalendarMaster._detect_lesson_type(calendar_pattern),
                        }
                    )
                    calendar_master_map[calendar_pattern] = calendar_master
                else:
                    calendar_master = calendar_master_map[calendar_pattern]

            # 教室
            room_name = str(row[31].value).strip() if row[31].value else ''
            room_key = f"{school_code}_{room_name}"
            room = classroom_map.get(room_key)

            # 承認種別
            approval_str = str(row[29].value).strip() if row[29].value else ''
            approval_type = 1  # デフォルト: 自動
            if '承認' in approval_str:
                approval_type = 2

            # 日付
            display_start_date = parse_date(row[50].value)
            class_start_date = parse_date(row[51].value)
            class_end_date = parse_date(row[52].value)

            # 既存チェック
            existing = ClassSchedule.objects.filter(
                tenant_id=tenant_id,
                schedule_code=schedule_code
            ).first()

            data = {
                'tenant_id': tenant_id,
                'schedule_code': schedule_code,
                'school': school,
                'brand': brand,
                'brand_category': brand_category,
                'day_of_week': day_of_week,
                'period': period,
                'start_time': start_time,
                'duration_minutes': duration_minutes,
                'end_time': end_time,
                'break_time': break_time,
                'class_name': class_name,
                'class_type': class_type,
                'display_course_name': display_course_name,
                'display_pair_name': display_pair_name,
                'display_description': display_description,
                'ticket_name': ticket_name,
                'ticket_id': ticket_id,
                'transfer_group': transfer_group,
                'schedule_group': schedule_group,
                'capacity': capacity,
                'trial_capacity': trial_capacity,
                'pause_seat_fee': pause_seat_fee,
                'calendar_master': calendar_master,
                'calendar_pattern': calendar_pattern,
                'approval_type': approval_type,
                'room': room,
                'room_name': room_name,
                'display_start_date': display_start_date,
                'class_start_date': class_start_date,
                'class_end_date': class_end_date,
                'is_active': True,
            }

            if existing:
                for key, value in data.items():
                    if key not in ['school', 'brand']:  # ForeignKeyは更新しない
                        setattr(existing, key, value)
                existing.save()
                updated += 1
            else:
                ClassSchedule.objects.create(**data)
                imported += 1

            if (imported + updated) % 100 == 0:
                print(f"  処理中... {imported + updated} 件")

        except Exception as e:
            errors.append(f"行 {row_num}: {schedule_code} - {str(e)}")
            continue

    return imported, updated, skipped, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_class_schedule.py <xlsx_path>")
        sys.exit(1)

    xlsx_path = sys.argv[1]

    if not os.path.exists(xlsx_path):
        print(f"エラー: ファイルが見つかりません: {xlsx_path}")
        sys.exit(1)

    print(f"インポート開始: {xlsx_path}")
    print("-" * 50)

    imported, updated, skipped, errors = import_class_schedules(xlsx_path)

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

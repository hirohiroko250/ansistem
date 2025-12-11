"""
T13開講カレンダーインポートスクリプト - 星付きシート用
星付きシートからエクスポートしたCSVをインポート

使い方:
cat scripts/import_t13_star.py | docker exec -i oza_backend python manage.py shell
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import csv
from datetime import datetime
from apps.schools.models import LessonCalendar, Brand
from apps.tenants.models import Tenant

# テナント取得（ブランドが紐づいているテナントを使用）
brand_sample = Brand.objects.first()
if brand_sample:
    tenant_id = brand_sample.tenant_id
    tenant = Tenant.objects.filter(id=tenant_id).first()
else:
    tenant = Tenant.objects.first()

if not tenant:
    print("ERROR: テナントが見つかりません")
    sys.exit(1)

print(f"テナント: {tenant.tenant_name} ({tenant.id})")

def parse_display_label(display_label):
    """保護者カレンダー表示からチケット番号を抽出"""
    if not display_label or display_label in ['講', '休', '★', 0, '0', 'nan', 'NaN']:
        return None
    import re
    match = re.search(r'(\d+)', str(display_label))
    if match:
        return int(match.group(1))
    return None

def determine_is_open(row):
    """開講日かどうかを判定"""
    open_flag = row.get('開講日', '')
    display_label = str(row.get('保護者カレンダー表示', ''))

    if open_flag == 'Y':
        return True
    if display_label == '休':
        return False
    if display_label == '講' or any(c.isdigit() for c in display_label):
        return True
    if '★' in display_label:
        return True
    return False

def import_calendar_csv(file_path, lesson_type_default):
    """CSVファイルをインポート"""
    created = 0
    skipped = 0
    errors = []

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            calendar_code = row.get('カレンダーID', '')
            date_str = row.get('日付', '')

            if not calendar_code or not date_str or calendar_code in ['0', 'ID', 'カレンダーID']:
                skipped += 1
                continue

            try:
                # 日付をパース
                if isinstance(date_str, str):
                    if ' ' in date_str:
                        date_str = date_str.split()[0]
                    if '-' in date_str:
                        lesson_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    else:
                        skipped += 1
                        continue
                else:
                    skipped += 1
                    continue

                day_of_week = row.get('曜日', '')
                is_open = determine_is_open(row)

                display_label = str(row.get('保護者カレンダー表示', ''))
                if display_label in ['nan', 'NaN']:
                    display_label = ''

                lesson_type = lesson_type_default if is_open else 'closed'

                ticket_seq = parse_display_label(display_label)
                ticket_type_raw = row.get('消化・発行チケット券種', '')
                ticket_type = str(ticket_type_raw)[:10] if ticket_type_raw and str(ticket_type_raw) not in ['nan', 'NaN'] else ''

                rejection_reason = row.get('拒否理由', '')
                rejection_reason = str(rejection_reason) if rejection_reason and str(rejection_reason) not in ['nan', 'NaN'] else ''
                is_makeup_allowed = not bool(rejection_reason)

                notice_message = row.get('お知らせ', '')
                notice_message = str(notice_message) if notice_message and str(notice_message) not in ['nan', 'NaN'] else ''

                holiday_name = row.get('祝日名', '')
                holiday_name = str(holiday_name) if holiday_name and str(holiday_name) not in ['nan', 'NaN'] else ''

                ticket_issue = row.get('発券', '')
                ticket_issue_count = None
                if ticket_issue and str(ticket_issue) not in ['nan', 'NaN', '']:
                    try:
                        ticket_issue_count = int(float(ticket_issue))
                    except:
                        pass

                valid_days = row.get('有効期限', 90)
                try:
                    valid_days_int = int(float(valid_days)) if valid_days and str(valid_days) not in ['nan', 'NaN'] else 90
                except:
                    valid_days_int = 90

                LessonCalendar.objects.create(
                    tenant_id=tenant.id,
                    tenant_ref=tenant,
                    calendar_code=calendar_code,
                    brand=None,
                    school=None,
                    lesson_date=lesson_date,
                    day_of_week=day_of_week,
                    is_open=is_open,
                    lesson_type=lesson_type,
                    display_label=display_label[:20] if display_label else '',
                    ticket_type=ticket_type,
                    ticket_sequence=ticket_seq,
                    is_makeup_allowed=is_makeup_allowed,
                    rejection_reason=rejection_reason[:100] if rejection_reason else '',
                    ticket_issue_count=ticket_issue_count,
                    valid_days=valid_days_int,
                    notice_message=notice_message,
                    holiday_name=holiday_name[:50] if holiday_name else '',
                )
                created += 1

            except Exception as e:
                errors.append(f"行{row_num}: {str(e)}")
                skipped += 1

    return created, skipped, errors

# CSVファイルをインポート
import glob

csv_files = {
    '/tmp/t13_star_A.csv': 'A',
    '/tmp/t13_star_B.csv': 'B',
    '/tmp/t13_star_P.csv': 'P',
    '/tmp/t13_star_Y.csv': 'Y',
}

total_created = 0
total_skipped = 0
all_errors = []

for csv_file, lesson_type in csv_files.items():
    if os.path.exists(csv_file):
        print(f"\n=== {csv_file} をインポート中 (lesson_type={lesson_type}) ===")
        created, skipped, errors = import_calendar_csv(csv_file, lesson_type)
        total_created += created
        total_skipped += skipped
        all_errors.extend(errors)
        print(f"作成: {created}, スキップ: {skipped}")
    else:
        print(f"\n{csv_file} が見つかりません")

print("\n=== インポート完了 ===")
print(f"合計作成: {total_created}")
print(f"合計スキップ: {total_skipped}")

if all_errors[:10]:
    print("\nエラー（最初の10件）:")
    for err in all_errors[:10]:
        print(f"  {err}")

# カレンダーコードごとの件数
print("\n=== カレンダーコード別件数 ===")
from django.db.models import Count
stats = LessonCalendar.objects.filter(tenant_id=tenant.id).values('calendar_code').annotate(count=Count('id'))
for s in stats:
    print(f"  {s['calendar_code']}: {s['count']}件")

print(f"\nLessonCalendar総数: {LessonCalendar.objects.filter(tenant_id=tenant.id).count()}")

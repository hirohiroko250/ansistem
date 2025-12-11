"""
T13開講カレンダーインポートスクリプト v2
Excel: T13_開講カレンダー202411181844.xlsx

テナント単位で管理（校舎は不要）
カレンダーコードでパターンを識別:
- 1001_SKAEC_A: Aパターン（外国人講師あり）- そろばん等
- 1002_SKAEC_B: Bパターン（日本人講師のみ）- そろばん等
- 1003_AEC_P: Pパターン（ペアクラス）- 英会話等
- Int_24: インターナショナル

使い方:
cat scripts/import_t13_calendar_v2.py | docker exec -i oza_backend python manage.py shell
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

# 既存データを削除（再インポート用）
deleted_count = LessonCalendar.objects.filter(tenant_id=tenant.id).delete()[0]
print(f"既存レコード削除: {deleted_count}件")

# カレンダーコードからlesson_typeを判定
def get_lesson_type_from_code(calendar_code):
    """カレンダーコードからlesson_typeを判定"""
    if not calendar_code:
        return 'closed'

    code = str(calendar_code).upper()

    # コードの末尾または構成要素で判定
    if '_A' in code or code.endswith('A'):
        return 'A'
    elif '_B' in code or code.endswith('B'):
        return 'B'
    elif '_P' in code or code.endswith('P'):
        return 'P'
    elif 'INT' in code or code.startswith('INT'):
        return 'Y'

    return 'A'  # デフォルト

def parse_display_label(display_label):
    """保護者カレンダー表示からチケット番号を抽出"""
    if not display_label or display_label in ['講', '休', '★', 0, '0', 'nan']:
        return None

    import re
    # 例: 月1, 火2, 水A3, 月19権利 など
    match = re.search(r'(\d+)', str(display_label))
    if match:
        return int(match.group(1))
    return None

def determine_is_open(row):
    """開講日かどうかを判定"""
    open_flag = row.get('開講日', '')
    display_label = str(row.get('保護者カレンダー表示', ''))

    # 開講日フラグがYなら開講
    if open_flag == 'Y':
        return True

    # 表示が「休」なら休講
    if display_label == '休':
        return False

    # 表示が「講」や数字付きなら開講
    if display_label == '講' or any(c.isdigit() for c in display_label):
        return True

    # ★マークはインターで開講
    if '★' in display_label:
        return True

    return False

def import_calendar_csv(file_path, default_lesson_type=None):
    """CSVファイルをインポート"""
    created = 0
    skipped = 0
    errors = []

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            calendar_code = row.get('カレンダーID', '')
            date_str = row.get('日付', '')

            # 空行やヘッダー行をスキップ
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

                # 曜日
                day_of_week = row.get('曜日', '')

                # 開講情報
                is_open = determine_is_open(row)
                display_label = str(row.get('保護者カレンダー表示', ''))
                if display_label == 'nan':
                    display_label = ''

                # lesson_type判定
                if default_lesson_type:
                    lesson_type = default_lesson_type
                else:
                    lesson_type = get_lesson_type_from_code(calendar_code)

                # 休講の場合
                if not is_open:
                    lesson_type = 'closed'

                # チケット情報
                ticket_seq = parse_display_label(display_label)
                ticket_type_raw = row.get('消化・発行チケット券種', '')
                ticket_type = str(ticket_type_raw)[:10] if ticket_type_raw and str(ticket_type_raw) != 'nan' else ''

                # 振替情報
                rejection_reason = row.get('拒否理由', '')
                rejection_reason = str(rejection_reason) if rejection_reason and str(rejection_reason) != 'nan' else ''
                is_makeup_allowed = not bool(rejection_reason)

                # その他
                notice_message = row.get('お知らせ', '')
                notice_message = str(notice_message) if notice_message and str(notice_message) != 'nan' else ''

                holiday_name = row.get('祝日名', '')
                holiday_name = str(holiday_name) if holiday_name and str(holiday_name) != 'nan' else ''

                ticket_issue = row.get('権利発券数') or row.get('発券', '')
                ticket_issue_count = None
                if ticket_issue:
                    try:
                        ticket_issue_count = int(float(ticket_issue))
                    except:
                        pass

                valid_days = row.get('有効期限', 90)
                try:
                    valid_days_int = int(float(valid_days)) if valid_days and str(valid_days) != 'nan' else 90
                except:
                    valid_days_int = 90

                # レコード作成
                LessonCalendar.objects.create(
                    tenant_id=tenant.id,
                    tenant_ref=tenant,
                    calendar_code=calendar_code,
                    brand=None,  # テナント単位なのでブランド不要
                    school=None,  # テナント単位なので校舎不要
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

csv_files = glob.glob('/tmp/t13_calendar*.csv')
if not csv_files:
    print("\nCSVファイルが見つかりません。")
    print("以下の手順でCSVを準備してください:")
    print("1. ExcelファイルからCSVシートをエクスポート")
    print("2. /tmp/t13_calendar_*.csv として保存")
else:
    total_created = 0
    total_skipped = 0
    all_errors = []

    # lesson_typeのマッピング
    csv_lesson_type_map = {
        'SKAECA': 'A',
        'SKAECB': 'B',
        'PCSV': 'P',
        'Int24': 'Y',
    }

    for csv_file in sorted(csv_files):
        # ファイル名からlesson_typeを推測
        filename = os.path.basename(csv_file)
        default_type = None
        for key, lt in csv_lesson_type_map.items():
            if key in filename:
                default_type = lt
                break

        print(f"\n=== {csv_file} をインポート中 (lesson_type={default_type}) ===")
        created, skipped, errors = import_calendar_csv(csv_file, default_type)
        total_created += created
        total_skipped += skipped
        all_errors.extend(errors)
        print(f"作成: {created}, スキップ: {skipped}")

    print("\n=== インポート完了 ===")
    print(f"合計作成: {total_created}")
    print(f"合計スキップ: {total_skipped}")

    if all_errors[:10]:
        print("\nエラー（最初の10件）:")
        for err in all_errors[:10]:
            print(f"  {err}")

# カレンダーコードごとの件数を表示
print("\n=== カレンダーコード別件数 ===")
from django.db.models import Count
stats = LessonCalendar.objects.filter(tenant_id=tenant.id).values('calendar_code').annotate(count=Count('id'))
for s in stats:
    print(f"  {s['calendar_code']}: {s['count']}件")

print(f"\nLessonCalendar総数: {LessonCalendar.objects.filter(tenant_id=tenant.id).count()}")

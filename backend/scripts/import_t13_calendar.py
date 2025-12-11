"""
T13開講カレンダーインポートスクリプト
Excel: T13_開講カレンダー202411181844.xlsx

使い方:
1. ExcelをCSVに変換して/tmpにコピー
2. docker exec -i oza_backend python manage.py shell < scripts/import_t13_calendar.py

カレンダーID例:
- 1003_AEC_P: AEC(英会話)のPパターン
- 1001_SKAEC_A: SKAEC(そろばん/算数)のAパターン
- Int_24: インターナショナル2024年度

データ構造:
- カレンダーID: ブランド+パターン識別子
- 日付: 2024-04-01 ～ 2025-03-31
- 保護者カレンダー表示: 講/休/月1/火1など
- 開講日: Y=開講、X=休講
- お知らせ: 外国人講師はいません等
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import csv
from datetime import datetime
from apps.schools.models import LessonCalendar, Brand, School
from apps.tenants.models import Tenant

# テナント取得（ブランドが紐づいているテナントを使用）
# まずブランドからテナントIDを取得
from apps.schools.models import Brand
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

# ブランドマッピング（カレンダーIDからブランドを特定）
# カレンダーID例: 1003_AEC_P, 1001_SKAEC_A, Int_24
CALENDAR_BRAND_MAP = {
    'AEC': 'AEC',       # アンイングリッシュクラブ
    'SKAEC': 'SOR',     # そろばん/算数 -> SOR (アンそろばんクラブ)
    'Int': 'INT',       # インターナショナル
    'SOR': 'SOR',       # そろばん
    # 必要に応じて追加
}

# 全ブランドを取得
brands = {b.brand_code: b for b in Brand.objects.filter(tenant_id=tenant.id)}
print(f"ブランド数: {len(brands)}")
for code, brand in brands.items():
    print(f"  {code}: {brand.brand_name}")

# デフォルト校舎（全校舎共通カレンダーの場合）
default_school = School.objects.filter(tenant_id=tenant.id).first()
if not default_school:
    print("ERROR: 校舎が見つかりません")
    sys.exit(1)

print(f"デフォルト校舎: {default_school.school_name}")

def parse_calendar_id(calendar_id):
    """カレンダーIDからブランドコードとパターンを抽出"""
    if not calendar_id or calendar_id == '0':
        return None, None

    calendar_id = str(calendar_id)

    # Int_24 形式
    if calendar_id.startswith('Int'):
        return 'Int', calendar_id

    parts = calendar_id.split('_')
    if len(parts) >= 2:
        # 例: 1003_AEC_P -> brand_prefix=AEC, pattern=P
        # 例: 1001_SKAEC_A -> brand_prefix=SKAEC, pattern=A
        brand_prefix = parts[1] if len(parts) > 1 else parts[0]
        pattern = parts[-1] if len(parts) > 2 else ''
        return brand_prefix, pattern

    return None, None

def get_brand_for_calendar(calendar_id):
    """カレンダーIDからブランドオブジェクトを取得"""
    brand_prefix, pattern = parse_calendar_id(calendar_id)
    if not brand_prefix:
        return None

    # CALENDAR_BRAND_MAPを使ってブランドコードに変換
    brand_code = CALENDAR_BRAND_MAP.get(brand_prefix, brand_prefix)

    # ブランドを検索
    for code, brand in brands.items():
        if code.upper() == brand_code.upper():
            return brand
        if brand_prefix.upper() in code.upper():
            return brand

    return None

def parse_display_label(display_label):
    """保護者カレンダー表示からチケット情報を抽出"""
    if not display_label or display_label in ['講', '休', '★', 0, '0']:
        return None, None

    # 例: 月1, 火2, 水A3 など
    import re
    match = re.match(r'([月火水木金土日]+)(\d+)', str(display_label))
    if match:
        day_part = match.group(1)
        seq_part = int(match.group(2))
        return day_part, seq_part

    return None, None

def determine_lesson_type(row):
    """授業タイプを判定"""
    display_label = str(row.get('保護者カレンダー表示', ''))
    notice = str(row.get('お知らせ', ''))
    is_open = row.get('開講日') == 'Y'

    if not is_open or display_label in ['休', '0']:
        return 'closed'

    # お知らせから外国人講師の有無を判定
    if '外国人講師はいません' in notice:
        return 'B'  # 日本人講師のみ
    elif '★' in display_label:
        return 'A'  # 外国人講師あり（インターナショナル）

    # デフォルトはAパターン
    return 'A'

def import_calendar_csv(file_path):
    """CSVファイルをインポート"""
    created = 0
    updated = 0
    skipped = 0
    errors = []

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            calendar_id = row.get('カレンダーID', '')
            date_str = row.get('日付', '')

            # 空行やヘッダー行をスキップ
            if not calendar_id or not date_str or calendar_id == '0':
                skipped += 1
                continue

            try:
                # 日付をパース
                if isinstance(date_str, str) and '-' in date_str:
                    lesson_date = datetime.strptime(date_str.split()[0], '%Y-%m-%d').date()
                else:
                    skipped += 1
                    continue

                # ブランドを取得
                brand = get_brand_for_calendar(calendar_id)
                if not brand:
                    errors.append(f"行{row_num}: ブランドが見つかりません - {calendar_id}")
                    skipped += 1
                    continue

                # 曜日
                day_of_week = row.get('曜日', '')

                # 開講情報
                is_open = row.get('開講日') == 'Y'
                display_label = str(row.get('保護者カレンダー表示', ''))
                lesson_type = determine_lesson_type(row)

                # チケット情報
                _, ticket_seq = parse_display_label(display_label)
                ticket_type_raw = row.get('消化・発行チケット券種', '')
                ticket_type = str(ticket_type_raw)[:10] if ticket_type_raw else ''

                # 振替情報
                rejection_reason = str(row.get('拒否理由', '')) if row.get('拒否理由') else ''
                is_makeup_allowed = not bool(rejection_reason)

                # その他
                notice_message = str(row.get('お知らせ', '')) if row.get('お知らせ') else ''
                holiday_name = str(row.get('祝日名', '')) if row.get('祝日名') else ''
                ticket_issue = row.get('権利発券数')
                ticket_issue_count = int(ticket_issue) if ticket_issue and str(ticket_issue).isdigit() else None
                valid_days = row.get('有効期限')
                valid_days_int = int(valid_days) if valid_days and str(valid_days).isdigit() else 90

                # レコード作成/更新
                obj, was_created = LessonCalendar.objects.update_or_create(
                    tenant_id=tenant.id,
                    brand=brand,
                    school=default_school,
                    lesson_date=lesson_date,
                    defaults={
                        'calendar_code': calendar_id,
                        'day_of_week': day_of_week,
                        'is_open': is_open,
                        'lesson_type': lesson_type,
                        'display_label': display_label[:20] if display_label else '',
                        'ticket_type': ticket_type,
                        'ticket_sequence': ticket_seq,
                        'is_makeup_allowed': is_makeup_allowed,
                        'rejection_reason': rejection_reason[:100] if rejection_reason else '',
                        'ticket_issue_count': ticket_issue_count,
                        'valid_days': valid_days_int,
                        'notice_message': notice_message,
                        'holiday_name': holiday_name[:50] if holiday_name else '',
                        'tenant_ref': tenant,
                    }
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                errors.append(f"行{row_num}: {str(e)}")
                skipped += 1

    return created, updated, skipped, errors

# CSVファイルが/tmpにあるか確認してインポート
import glob

csv_files = glob.glob('/tmp/t13_calendar*.csv')
if not csv_files:
    print("\nCSVファイルが見つかりません。")
    print("以下の手順でCSVを準備してください:")
    print("1. ExcelファイルからCSVシートをエクスポート")
    print("2. /tmp/t13_calendar_*.csv として保存")
    print("例: /tmp/t13_calendar_P.csv, /tmp/t13_calendar_A.csv")
else:
    total_created = 0
    total_updated = 0
    total_skipped = 0
    all_errors = []

    for csv_file in csv_files:
        print(f"\n=== {csv_file} をインポート中 ===")
        created, updated, skipped, errors = import_calendar_csv(csv_file)
        total_created += created
        total_updated += updated
        total_skipped += skipped
        all_errors.extend(errors)
        print(f"作成: {created}, 更新: {updated}, スキップ: {skipped}")

    print("\n=== インポート完了 ===")
    print(f"合計作成: {total_created}")
    print(f"合計更新: {total_updated}")
    print(f"合計スキップ: {total_skipped}")

    if all_errors[:10]:
        print("\nエラー（最初の10件）:")
        for err in all_errors[:10]:
            print(f"  {err}")

print(f"\nLessonCalendar総数: {LessonCalendar.objects.filter(tenant_id=tenant.id).count()}")

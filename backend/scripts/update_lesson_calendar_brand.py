"""
LessonCalendarのbrandフィールドを更新するスクリプト

calendar_codeからブランドコードを抽出してbrandフィールドを設定する
例: 1011_AEC_A → AEC

使用方法:
  python manage.py shell < scripts/update_lesson_calendar_brand.py

または:
  python manage.py runscript update_lesson_calendar_brand
"""

import os
import sys
import django

# Django設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except:
    pass

from apps.schools.models import LessonCalendar, Brand


def extract_brand_code(calendar_code: str) -> str | None:
    """calendar_codeからブランドコードを抽出

    形式: {校舎番号}_{ブランドコード}_{タイプ}
    例: 1011_AEC_A → AEC
        1001_SKAEC_A → SKAEC
        Int_24 → Int
    """
    if not calendar_code:
        return None

    parts = calendar_code.split('_')
    if len(parts) >= 2:
        # 最初の部分が数字なら、2番目がブランドコード
        if parts[0].isdigit():
            return parts[1]
        else:
            # Int_24 のような形式
            return parts[0]
    return None


def update_lesson_calendar_brands():
    """LessonCalendarのbrandフィールドを更新"""

    # ブランドをコードでインデックス化
    brands = {b.brand_code: b for b in Brand.objects.all()}
    print(f"ブランド数: {len(brands)}")
    print(f"ブランドコード: {list(brands.keys())}")

    # brandがNULLのLessonCalendarを取得
    calendars_without_brand = LessonCalendar.objects.filter(brand__isnull=True)
    total = calendars_without_brand.count()
    print(f"\nbrandがNULLのカレンダー数: {total}")

    if total == 0:
        print("更新対象がありません")
        return

    # calendar_codeごとにグループ化して処理
    calendar_codes = calendars_without_brand.values_list('calendar_code', flat=True).distinct()
    print(f"ユニークなカレンダーコード数: {len(calendar_codes)}")

    updated_count = 0
    not_found_codes = set()

    for calendar_code in calendar_codes:
        brand_code = extract_brand_code(calendar_code)

        if not brand_code:
            not_found_codes.add(calendar_code)
            continue

        brand = brands.get(brand_code)
        if not brand:
            # 大文字小文字を無視して検索
            for code, b in brands.items():
                if code.upper() == brand_code.upper():
                    brand = b
                    break

        if brand:
            count = LessonCalendar.objects.filter(
                calendar_code=calendar_code,
                brand__isnull=True
            ).update(brand=brand)
            updated_count += count
            print(f"  {calendar_code} → {brand.brand_code}: {count}件更新")
        else:
            not_found_codes.add(f"{calendar_code} (brand_code={brand_code})")

    print(f"\n更新完了: {updated_count}件")

    if not_found_codes:
        print(f"\nブランドが見つからなかったカレンダーコード:")
        for code in sorted(not_found_codes):
            print(f"  - {code}")


if __name__ == '__main__':
    update_lesson_calendar_brands()

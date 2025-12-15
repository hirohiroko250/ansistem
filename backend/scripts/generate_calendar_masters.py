"""
既存のカレンダーコードからCalendarMasterを生成するスクリプト

Usage:
    python manage.py shell < scripts/generate_calendar_masters.py

または:
    python manage.py runscript generate_calendar_masters
"""
import os
import sys
import django

# Django設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.db.models import Count
from apps.schools.models import LessonCalendar, ClassSchedule, CalendarMaster, Brand
from apps.tenants.models import Tenant

def detect_brand_from_code(code, tenant_id):
    """カレンダーコードからブランドを推測"""
    if not code or '_' not in code:
        return None

    parts = code.split('_')
    if len(parts) < 2:
        return None

    # 2番目のパーツがブランドコードの可能性が高い
    potential_brand_code = parts[1]

    # ブランドを検索
    brand = Brand.objects.filter(
        tenant_id=tenant_id,
        brand_code__iexact=potential_brand_code
    ).first()

    if brand:
        return brand

    # 部分一致で検索
    brand = Brand.objects.filter(
        tenant_id=tenant_id,
        brand_code__icontains=potential_brand_code[:3]
    ).first()

    return brand


def detect_lesson_type(code):
    """コードから授業タイプを推測"""
    if not code:
        return CalendarMaster.LessonType.OTHER

    code_upper = code.upper()

    if code_upper.endswith('_A') or '_A_' in code_upper:
        return CalendarMaster.LessonType.TYPE_A
    elif code_upper.endswith('_B') or '_B_' in code_upper:
        return CalendarMaster.LessonType.TYPE_B
    elif code_upper.endswith('_P') or '_P_' in code_upper:
        return CalendarMaster.LessonType.TYPE_P
    elif 'INT' in code_upper or code_upper.endswith('_Y'):
        return CalendarMaster.LessonType.TYPE_Y

    return CalendarMaster.LessonType.OTHER


def get_tenant_with_data():
    """データがあるテナントを取得"""
    # LessonCalendarが最も多いテナントを取得
    from django.db.models import Count
    tenant_with_most_data = LessonCalendar.objects.values('tenant_id').annotate(
        count=Count('id')
    ).order_by('-count').first()

    if tenant_with_most_data:
        return Tenant.objects.filter(id=tenant_with_most_data['tenant_id']).first()

    return Tenant.objects.first()


def generate_calendar_masters(dry_run=True):
    """既存データからCalendarMasterを生成"""
    print("=" * 60)
    print("カレンダーマスター生成スクリプト")
    print("=" * 60)
    print(f"モード: {'DRY-RUN（実行しない）' if dry_run else '本番実行'}")
    print()

    # データがあるテナントを取得
    tenant = get_tenant_with_data()
    if not tenant:
        print("エラー: テナントが見つかりません")
        return

    print(f"テナント: {tenant.id}")
    print()

    # LessonCalendarから重複なしのカレンダーコードを取得
    calendar_codes = LessonCalendar.objects.filter(
        tenant_id=tenant.id
    ).values('calendar_code').annotate(
        count=Count('id')
    ).order_by('calendar_code')

    print(f"LessonCalendarから {len(calendar_codes)} 件のカレンダーコードを発見")
    print()

    created_count = 0
    skipped_count = 0

    for item in calendar_codes:
        code = item['calendar_code']
        count = item['count']

        if not code:
            print(f"  スキップ: 空のコード (レコード数: {count})")
            skipped_count += 1
            continue

        # 既存チェック
        existing = CalendarMaster.objects.filter(
            tenant_id=tenant.id,
            code=code
        ).first()

        if existing:
            print(f"  存在: {code} (レコード数: {count})")
            skipped_count += 1
            continue

        # ブランドと授業タイプを推測
        brand = detect_brand_from_code(code, tenant.id)
        lesson_type = detect_lesson_type(code)

        brand_name = brand.brand_name if brand else "なし"
        type_display = dict(CalendarMaster.LessonType.choices).get(lesson_type, lesson_type)

        print(f"  作成: {code} (レコード数: {count}) -> ブランド: {brand_name}, タイプ: {type_display}")

        if not dry_run:
            CalendarMaster.objects.create(
                tenant_id=tenant.id,
                tenant_ref=tenant,
                code=code,
                name=code,
                brand=brand,
                lesson_type=lesson_type,
                is_active=True
            )

        created_count += 1

    print()
    print("=" * 60)
    print(f"結果: 作成 {created_count} 件, スキップ {skipped_count} 件")

    if dry_run:
        print()
        print("※ DRY-RUNモードです。実際に実行するには dry_run=False で再実行してください")


def link_calendars_to_masters(dry_run=True):
    """LessonCalendarとClassScheduleをCalendarMasterに紐付け"""
    print()
    print("=" * 60)
    print("カレンダーマスター紐付け")
    print("=" * 60)

    tenant = get_tenant_with_data()
    if not tenant:
        print("エラー: テナントが見つかりません")
        return

    # LessonCalendarの紐付け
    updated_lc = 0
    for lc in LessonCalendar.objects.filter(tenant_id=tenant.id, calendar_master__isnull=True):
        if not lc.calendar_code:
            continue

        master = CalendarMaster.objects.filter(
            tenant_id=tenant.id,
            code=lc.calendar_code
        ).first()

        if master:
            print(f"  LessonCalendar {lc.id}: {lc.calendar_code} -> CalendarMaster {master.id}")
            if not dry_run:
                lc.calendar_master = master
                lc.save(update_fields=['calendar_master'])
            updated_lc += 1

    print(f"LessonCalendar: {updated_lc} 件更新")

    # ClassScheduleの紐付け
    updated_cs = 0
    for cs in ClassSchedule.objects.filter(tenant_id=tenant.id, calendar_master__isnull=True):
        if not cs.calendar_pattern:
            continue

        master = CalendarMaster.objects.filter(
            tenant_id=tenant.id,
            code=cs.calendar_pattern
        ).first()

        if master:
            print(f"  ClassSchedule {cs.id}: {cs.calendar_pattern} -> CalendarMaster {master.id}")
            if not dry_run:
                cs.calendar_master = master
                cs.save(update_fields=['calendar_master'])
            updated_cs += 1

    print(f"ClassSchedule: {updated_cs} 件更新")

    if dry_run:
        print()
        print("※ DRY-RUNモードです。実際に実行するには dry_run=False で再実行してください")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='カレンダーマスター生成')
    parser.add_argument('--execute', action='store_true', help='実際に実行する（デフォルトはdry-run）')
    args = parser.parse_args()

    dry_run = not args.execute

    generate_calendar_masters(dry_run=dry_run)
    link_calendars_to_masters(dry_run=dry_run)

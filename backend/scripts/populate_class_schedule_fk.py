#!/usr/bin/env python
"""
StudentItemのclass_schedule FKを自動設定するスクリプト

曜日 + 開始時間 + ブランド + 校舎 で ClassSchedule とマッチングして
class_schedule FK を設定する
"""
import os
import sys
import django

# Django設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.contracts.models import StudentItem
from apps.schools.models import ClassSchedule


def time_diff_minutes(t1, t2):
    """2つの時間の差を分単位で返す"""
    if not t1 or not t2:
        return float('inf')
    return abs((t1.hour * 60 + t1.minute) - (t2.hour * 60 + t2.minute))


def populate_class_schedule_fk(dry_run=True, max_diff_minutes=15):
    """
    StudentItemのclass_schedule FKを設定する

    Args:
        dry_run: Trueの場合は更新せずプレビューのみ
        max_diff_minutes: 時間差の許容範囲（分）
    """
    # class_schedule未設定で曜日+時間ありのStudentItemを取得
    items = StudentItem.objects.filter(
        deleted_at__isnull=True,
        class_schedule__isnull=True
    ).exclude(
        day_of_week__isnull=True
    ).exclude(
        start_time__isnull=True
    ).select_related('brand', 'school')

    total = items.count()
    print(f"対象StudentItem数: {total}")
    print(f"許容時間差: ±{max_diff_minutes}分")
    print(f"モード: {'ドライラン（プレビュー）' if dry_run else '本番実行'}")
    print("-" * 60)

    exact_match = 0
    fuzzy_match = 0
    no_match = 0
    updated = 0

    # バッチ処理
    batch_size = 500
    for i in range(0, total, batch_size):
        batch = items[i:i+batch_size]
        updates = []

        for item in batch:
            # 同じ曜日・ブランド・校舎のClassScheduleを検索
            css = ClassSchedule.objects.filter(
                day_of_week=item.day_of_week,
                brand_id=item.brand_id,
                school_id=item.school_id,
                is_active=True,
                deleted_at__isnull=True
            )

            best_cs = None
            min_diff = float('inf')

            for cs in css:
                diff = time_diff_minutes(item.start_time, cs.start_time)
                if diff < min_diff:
                    min_diff = diff
                    best_cs = cs

            if min_diff == 0:
                exact_match += 1
                item.class_schedule = best_cs
                updates.append(item)
            elif min_diff <= max_diff_minutes:
                fuzzy_match += 1
                item.class_schedule = best_cs
                updates.append(item)
            else:
                no_match += 1

        # 更新
        if not dry_run and updates:
            StudentItem.objects.bulk_update(updates, ['class_schedule'])
            updated += len(updates)

        # 進捗表示
        processed = min(i + batch_size, total)
        print(f"進捗: {processed}/{total} ({processed*100//total}%)")

    print("-" * 60)
    print(f"完全一致: {exact_match}件")
    print(f"ファジーマッチ（{max_diff_minutes}分以内）: {fuzzy_match}件")
    print(f"マッチなし: {no_match}件")
    print(f"合計マッチ率: {(exact_match + fuzzy_match) * 100 // total if total > 0 else 0}%")

    if dry_run:
        print(f"\n※ドライランのため、更新は行われていません")
        print(f"本番実行する場合は --execute オプションを付けてください")
    else:
        print(f"\n更新件数: {updated}件")

    return exact_match + fuzzy_match, no_match


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='StudentItemのclass_schedule FKを設定')
    parser.add_argument('--execute', action='store_true', help='本番実行（デフォルトはドライラン）')
    parser.add_argument('--max-diff', type=int, default=15, help='時間差の許容範囲（分）、デフォルト15')
    args = parser.parse_args()

    populate_class_schedule_fk(dry_run=not args.execute, max_diff_minutes=args.max_diff)

"""
ClassScheduleのdisplay_course_nameから学年(grade)を自動設定するスクリプト

使い方:
docker exec -i oza_backend python manage.py shell < /app/scripts/update_class_schedule_grades.py
"""

from apps.schools.models import ClassSchedule, Grade

# display_course_name → grade_code マッピング
GRADE_MAPPING = {
    '①幼児': 'GR026',        # 年少～年長
    '②小１以上': 'GR030',    # 小1～小6
    '③小４以上': 'G005',     # 小4~高3
    '④小５以上': 'GR041',    # 小5～中3
    '⑤小６以上': 'G006',     # 小6~高3
    '⑥中2以上': 'GR050',     # 中1～高3
}

print("=== ClassSchedule 学年更新スクリプト ===\n")

# 学年データをキャッシュ
grades = {g.grade_code: g for g in Grade.objects.filter(is_active=True)}
print(f"読み込んだ学年数: {len(grades)}")

# ClassScheduleを更新
updated_count = 0
skipped_count = 0
no_match_count = 0

schedules = ClassSchedule.objects.filter(is_active=True, grade__isnull=True)
print(f"学年未設定のClassSchedule: {schedules.count()}件\n")

for schedule in schedules:
    display_name = schedule.display_course_name or ''
    matched = False

    for pattern, grade_code in GRADE_MAPPING.items():
        if pattern in display_name:
            grade = grades.get(grade_code)
            if grade:
                schedule.grade = grade
                schedule.save(update_fields=['grade'])
                updated_count += 1
                matched = True
                if updated_count <= 10:
                    print(f"  更新: {schedule.schedule_code} -> {grade.grade_name}")
                break

    if not matched:
        no_match_count += 1
        if no_match_count <= 5:
            print(f"  マッチなし: {schedule.schedule_code} ({display_name})")

print(f"\n=== 結果 ===")
print(f"更新: {updated_count}件")
print(f"マッチなし: {no_match_count}件")
print(f"学年設定済みClassSchedule: {ClassSchedule.objects.filter(is_active=True, grade__isnull=False).count()}件")

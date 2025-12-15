"""
StudentSchoolからStudentEnrollmentを同期

StudentSchoolにclass_scheduleが紐付いているレコードを元に、
StudentEnrollmentレコードを作成（カレンダー表示用）

Usage:
    cd backend && python scripts/sync_student_enrollment.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from apps.students.models import StudentSchool, StudentEnrollment
from datetime import date


def sync_enrollment():
    print("=== StudentSchool → StudentEnrollment 同期 ===")

    # class_scheduleが設定されているStudentSchoolを取得
    student_schools = StudentSchool.objects.filter(
        class_schedule__isnull=False,
        deleted_at__isnull=True
    ).select_related('student', 'school', 'brand', 'class_schedule')

    print(f"対象StudentSchool: {student_schools.count()}件")

    created = 0
    updated = 0
    skipped = 0

    for ss in student_schools:
        try:
            # 既存のEnrollmentを確認（同じ生徒×クラススケジュールで有効なもの）
            existing = StudentEnrollment.objects.filter(
                student=ss.student,
                class_schedule=ss.class_schedule,
                end_date__isnull=True,
                deleted_at__isnull=True
            ).first()

            if existing:
                # 既存レコードを更新（必要に応じて）
                needs_update = False
                if existing.day_of_week != ss.day_of_week:
                    existing.day_of_week = ss.day_of_week
                    needs_update = True
                if existing.start_time != ss.start_time:
                    existing.start_time = ss.start_time
                    needs_update = True
                if existing.end_time != ss.end_time:
                    existing.end_time = ss.end_time
                    needs_update = True

                if needs_update:
                    existing.save()
                    updated += 1
                else:
                    skipped += 1
            else:
                # 新規作成
                StudentEnrollment.objects.create(
                    tenant_id=ss.tenant_id,
                    student=ss.student,
                    school=ss.school,
                    brand=ss.brand,
                    class_schedule=ss.class_schedule,
                    day_of_week=ss.day_of_week,
                    start_time=ss.start_time,
                    end_time=ss.end_time,
                    status=StudentEnrollment.Status.ENROLLED,
                    change_type=StudentEnrollment.ChangeType.NEW_ENROLLMENT,
                    effective_date=ss.start_date or date(2025, 1, 1),
                    notes=f'StudentSchoolから自動同期 ({ss.id})'
                )
                created += 1

        except Exception as e:
            print(f"Error: {ss.student} - {e}")

    print(f"\n=== 結果 ===")
    print(f"作成: {created}")
    print(f"更新: {updated}")
    print(f"スキップ（変更なし）: {skipped}")


if __name__ == '__main__':
    sync_enrollment()

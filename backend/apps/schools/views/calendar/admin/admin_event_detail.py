"""
AdminCalendarEventDetailView - 管理者用カレンダーイベント詳細API
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q

from apps.core.permissions import IsTenantUser
from apps.core.exceptions import ValidationException, NotFoundError
from apps.schools.models import LessonCalendar, ClassSchedule


class AdminCalendarEventDetailView(APIView):
    """管理者用カレンダーイベント詳細API

    特定のクラス×日付の詳細情報（受講者一覧、出欠状況）を返す。
    """
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get(self, request):
        """
        ?schedule_id=xxx&date=2024-12-25
        """
        from datetime import datetime
        from apps.lessons.models import AbsenceTicket
        from apps.students.models import StudentEnrollment, StudentSchool

        schedule_id = request.query_params.get('schedule_id')
        date_str = request.query_params.get('date')

        if not all([schedule_id, date_str]):
            raise ValidationException('schedule_id と date は必須です')

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationException('日付形式が不正です（YYYY-MM-DD）')

        # ClassScheduleを取得
        try:
            schedule = ClassSchedule.objects.select_related(
                'brand', 'school', 'room', 'grade'
            ).get(id=schedule_id)
        except ClassSchedule.DoesNotExist:
            raise NotFoundError('スケジュールが見つかりません')

        # LessonCalendarからlesson_type取得
        lesson_cal = LessonCalendar.objects.filter(
            lesson_date=target_date,
            calendar_code=schedule.calendar_pattern
        ).first() if schedule.calendar_pattern else None

        lesson_type = lesson_cal.lesson_type if lesson_cal else 'A'

        # このクラスに登録されている生徒一覧（対象日時点で有効なenrollmentのみ）
        enrollments = StudentEnrollment.objects.filter(
            class_schedule_id=schedule_id,
            status='enrolled',
            deleted_at__isnull=True,
            effective_date__lte=target_date,  # 適用開始日が対象日以前
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=target_date)  # 終了日が未設定または対象日以降
        ).select_related('student', 'student__guardian').order_by(
            'student__grade_text',  # 学年順
            'student__last_name_kana',  # 名前カナ順
            'student__first_name_kana'
        )

        # AbsenceTicketから欠席情報を取得
        absent_tickets = AbsenceTicket.objects.filter(
            class_schedule_id=schedule_id,
            absence_date=target_date,
            deleted_at__isnull=True
        ).values_list('student_id', flat=True)
        absent_student_ids = set(str(sid) for sid in absent_tickets)

        # 出欠記録を取得（当日分）
        students_list = []
        present_count = 0
        absent_count = 0

        for enrollment in enrollments:
            student = enrollment.student
            if not student:
                continue

            # AbsenceTicketで欠席判定
            student_id_str = str(student.id)
            if student_id_str in absent_student_ids:
                status_value = 'absent'
                absent_count += 1
            else:
                status_value = 'unknown'

            students_list.append({
                'id': str(student.id),
                'studentNo': student.student_no,
                'name': f"{student.last_name}{student.first_name}",
                'nameKana': f"{student.last_name_kana}{student.first_name_kana}",
                'grade': student.grade_text,
                'guardianName': f"{student.guardian.last_name}{student.guardian.first_name}" if student.guardian else None,
                'guardianPhone': student.guardian.phone if student.guardian else None,
                'enrollmentType': enrollment.change_type,  # change_typeを使用
                'attendanceStatus': status_value,
            })

        # StudentEnrollmentがない場合、StudentSchoolから生徒を取得（フォールバック）
        if not students_list and schedule.school_id and schedule.brand_id:
            student_schools = StudentSchool.objects.filter(
                school_id=schedule.school_id,
                brand_id=schedule.brand_id,
                enrollment_status='active',
                deleted_at__isnull=True
            ).select_related('student', 'student__guardian').order_by(
                'student__grade_text',  # 学年順
                'student__last_name_kana',  # 名前カナ順
                'student__first_name_kana'
            )

            # グレードでフィルタ（クラスにグレードが設定されている場合）
            if schedule.grade_id:
                student_schools = student_schools.filter(student__grade_id=schedule.grade_id)

            for ss in student_schools:
                student = ss.student
                if not student or student.status != 'enrolled':
                    continue

                # AbsenceTicketで欠席判定
                student_id_str = str(student.id)
                if student_id_str in absent_student_ids:
                    status_value = 'absent'
                    absent_count += 1
                else:
                    status_value = 'unknown'

                students_list.append({
                    'id': str(student.id),
                    'studentNo': student.student_no,
                    'name': f"{student.last_name}{student.first_name}",
                    'nameKana': f"{student.last_name_kana or ''}{student.first_name_kana or ''}",
                    'grade': student.grade_text,
                    'guardianName': f"{student.guardian.last_name}{student.guardian.first_name}" if student.guardian else None,
                    'guardianPhone': student.guardian.phone if student.guardian else None,
                    'enrollmentType': 'school_fallback',  # フォールバック識別用
                    'attendanceStatus': status_value,
                })

        return Response({
            'scheduleId': schedule_id,
            'date': date_str,
            'schedule': {
                'className': schedule.class_name,
                'displayCourseName': schedule.display_course_name,
                'startTime': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                'endTime': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                'brandName': schedule.brand.brand_name if schedule.brand else None,
                'schoolName': schedule.school.school_name if schedule.school else None,
                'roomName': schedule.room.classroom_name if schedule.room else schedule.room_name,
                'capacity': schedule.capacity,
                'lessonType': lesson_type,
                'lessonTypeLabel': {
                    'A': '外国人あり',
                    'B': '日本人のみ',
                    'P': 'ペア',
                    'Y': 'インター',
                }.get(lesson_type, lesson_type),
                'calendarPattern': schedule.calendar_pattern,
            },
            'summary': {
                'totalEnrolled': len(students_list),
                'presentCount': present_count,
                'absentCount': absent_count,
                'unknownCount': len(students_list) - present_count - absent_count,
            },
            'students': students_list
        })

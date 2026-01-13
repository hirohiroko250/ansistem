"""
Student Calendar Views - 生徒カレンダー表示Views
StudentCalendarView
"""
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class StudentCalendarView(APIView):
    """生徒のカレンダー表示用API

    開講時間割（ClassSchedule）と年間カレンダー（LessonCalendar）を組み合わせて
    生徒のカレンダーイベントを生成する
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.schools.models import ClassSchedule, LessonCalendar
        from apps.contracts.models import StudentItem
        from apps.students.models import Student
        from datetime import datetime as dt
        import calendar as cal

        # tenant_idはrequest.tenant_idまたはrequest.user.tenant_idから取得
        tenant_id = getattr(request, 'tenant_id', None)
        if tenant_id is None and hasattr(request, 'user') and hasattr(request.user, 'tenant_id'):
            tenant_id = request.user.tenant_id
        # student_id または student パラメータを受け付ける
        student_id = request.query_params.get('student_id') or request.query_params.get('student')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not student_id:
            return Response({'error': 'student_id is required'}, status=400)

        # 生徒取得
        try:
            student = Student.objects.get(id=student_id, tenant_id=tenant_id)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=404)

        # 日付範囲の設定
        if year and month:
            year = int(year)
            month = int(month)
            date_from = dt(year, month, 1).date()
            _, last_day = cal.monthrange(year, month)
            date_to = dt(year, month, last_day).date()
        elif date_from and date_to:
            date_from = dt.fromisoformat(date_from).date()
            date_to = dt.fromisoformat(date_to).date()
        else:
            # デフォルトは今月
            today = dt.now().date()
            date_from = today.replace(day=1)
            _, last_day = cal.monthrange(today.year, today.month)
            date_to = today.replace(day=last_day)

        # 生徒の受講クラス（ClassSchedule）を取得
        student_items = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True
        ).select_related('brand', 'school', 'course', 'class_schedule')

        # StudentItemから受講ClassScheduleのIDを収集
        direct_schedule_ids = set()
        fallback_schedules = []
        brand_ids = set()
        school_ids = set()

        for item in student_items:
            if item.brand_id:
                brand_ids.add(item.brand_id)
            if item.school_id:
                school_ids.add(item.school_id)

            if item.class_schedule_id:
                direct_schedule_ids.add(item.class_schedule_id)
            elif item.day_of_week is not None and item.start_time:
                fallback_schedules.append({
                    'day_of_week': item.day_of_week,
                    'start_time': item.start_time,
                    'brand_id': str(item.brand_id) if item.brand_id else None,
                    'school_id': str(item.school_id) if item.school_id else None,
                })

        # 生徒の主校舎・主ブランドも追加
        if student.primary_school_id:
            school_ids.add(student.primary_school_id)
        if student.primary_brand_id:
            brand_ids.add(student.primary_brand_id)

        # 直接紐付けられたClassScheduleを取得
        class_schedules = list(ClassSchedule.objects.filter(
            id__in=direct_schedule_ids,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('school', 'brand', 'brand_category'))

        # フォールバック: class_scheduleがないStudentItemの場合
        if fallback_schedules:
            all_class_schedules = ClassSchedule.objects.filter(
                is_active=True,
                deleted_at__isnull=True
            )
            if school_ids:
                all_class_schedules = all_class_schedules.filter(school_id__in=school_ids)
            if brand_ids:
                all_class_schedules = all_class_schedules.filter(brand_id__in=brand_ids)
            all_class_schedules = all_class_schedules.select_related('school', 'brand', 'brand_category')

            def time_diff_minutes(t1, t2):
                if not t1 or not t2:
                    return float('inf')
                return abs((t1.hour * 60 + t1.minute) - (t2.hour * 60 + t2.minute))

            for cs in all_class_schedules:
                if cs.id in direct_schedule_ids:
                    continue
                for enrolled in fallback_schedules:
                    dow_match = (enrolled['day_of_week'] == cs.day_of_week)
                    si_start_time = enrolled['start_time']
                    time_match = time_diff_minutes(si_start_time, cs.start_time) <= 30
                    brand_match = (enrolled['brand_id'] == str(cs.brand_id) if cs.brand_id else True)
                    school_match = (enrolled['school_id'] == str(cs.school_id) if cs.school_id else True)

                    if dow_match and time_match and brand_match and school_match:
                        class_schedules.append(cs)
                        break

        # LessonCalendarを取得
        lesson_calendars = LessonCalendar.objects.filter(
            lesson_date__gte=date_from,
            lesson_date__lte=date_to,
        )
        if school_ids:
            lesson_calendars = lesson_calendars.filter(school_id__in=school_ids)
        if brand_ids:
            lesson_calendars = lesson_calendars.filter(brand_id__in=brand_ids)

        # カレンダーをdate+school+brandでインデックス化
        calendar_map = {}
        for lc in lesson_calendars:
            key = (lc.lesson_date, str(lc.school_id), str(lc.brand_id) if lc.brand_id else None)
            calendar_map[key] = lc

        # 欠席チケット（AbsenceTicket）を取得（キャンセル済みは除外）
        from ..models import AbsenceTicket
        absence_tickets = AbsenceTicket.objects.filter(
            student=student,
            absence_date__gte=date_from,
            absence_date__lte=date_to,
        ).exclude(
            status=AbsenceTicket.Status.CANCELLED
        ).select_related('class_schedule')

        absence_map = {}
        for at in absence_tickets:
            key = (at.absence_date, str(at.class_schedule_id) if at.class_schedule_id else None)
            absence_map[key] = at

        # カレンダーイベントを生成
        events = []
        today = dt.now().date()
        current_date = date_from
        day_of_week_map = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7}

        while current_date <= date_to:
            if current_date < today:
                current_date += timedelta(days=1)
                continue

            python_weekday = current_date.weekday()
            db_day_of_week = day_of_week_map[python_weekday]

            for cs in class_schedules:
                if cs.day_of_week != db_day_of_week:
                    continue

                cal_key = (current_date, str(cs.school_id), str(cs.brand_id) if cs.brand_id else None)
                lesson_cal = calendar_map.get(cal_key)

                is_closed = False
                is_native_day = False
                lesson_type = 'A'
                notice_message = ''
                holiday_name = ''

                if lesson_cal:
                    is_closed = not lesson_cal.is_open
                    is_native_day = lesson_cal.is_native_day
                    lesson_type = lesson_cal.lesson_type
                    notice_message = lesson_cal.notice_message or ''
                    holiday_name = lesson_cal.holiday_name or ''

                absence_key = (current_date, str(cs.id))
                absence_ticket = absence_map.get(absence_key)
                is_absent = absence_ticket is not None

                start_datetime = dt.combine(current_date, cs.start_time)
                end_datetime = dt.combine(current_date, cs.end_time)

                event_type = 'lesson'
                event_status = 'scheduled'
                if is_closed:
                    event_type = 'closed'
                elif is_absent:
                    event_type = 'absent'
                    event_status = 'absent'
                elif is_native_day:
                    event_type = 'native'

                events.append({
                    'id': f'{cs.id}_{current_date.isoformat()}',
                    'classScheduleId': str(cs.id),
                    'title': cs.class_name or cs.display_course_name or 'レッスン',
                    'start': start_datetime.isoformat(),
                    'end': end_datetime.isoformat(),
                    'date': current_date.isoformat(),
                    'dayOfWeek': db_day_of_week,
                    'period': cs.period,
                    'type': event_type,
                    'status': event_status,
                    'lessonType': lesson_type,
                    'isClosed': is_closed,
                    'isAbsent': is_absent,
                    'isNativeDay': is_native_day,
                    'holidayName': holiday_name,
                    'noticeMessage': notice_message,
                    'schoolId': str(cs.school_id),
                    'schoolName': cs.school.school_name if cs.school else '',
                    'brandId': str(cs.brand_id) if cs.brand_id else None,
                    'brandName': cs.brand.brand_name if cs.brand else '',
                    'brandCategoryName': cs.brand_category.category_name if cs.brand_category else '',
                    'roomName': cs.room_name or '',
                    'className': cs.class_name,
                    'displayCourseName': cs.display_course_name,
                    'displayPairName': cs.display_pair_name,
                    'transferGroup': cs.transfer_group,
                    'calendarPattern': cs.calendar_pattern,
                    'absenceTicketId': str(absence_ticket.id) if absence_ticket else None,
                })

            current_date += timedelta(days=1)

        # 振替予約を追加
        from ..models import Attendance
        makeup_attendances = Attendance.objects.filter(
            student=student,
            status=Attendance.Status.MAKEUP,
            schedule__date__gte=date_from,
            schedule__date__lte=date_to,
        ).select_related('schedule', 'schedule__school')

        for attendance in makeup_attendances:
            lesson_schedule = attendance.schedule
            if not lesson_schedule:
                continue

            start_datetime = dt.combine(lesson_schedule.date, lesson_schedule.start_time)
            end_datetime = dt.combine(lesson_schedule.date, lesson_schedule.end_time)

            events.append({
                'id': f'makeup_{attendance.id}',
                'classScheduleId': None,
                'title': '振替授業',
                'start': start_datetime.isoformat(),
                'end': end_datetime.isoformat(),
                'date': lesson_schedule.date.isoformat(),
                'dayOfWeek': lesson_schedule.date.weekday() + 1,
                'period': None,
                'type': 'makeup',
                'status': 'makeup',
                'lessonType': 'A',
                'isClosed': False,
                'isAbsent': False,
                'isNativeDay': False,
                'holidayName': '',
                'noticeMessage': attendance.notes or '',
                'schoolId': str(lesson_schedule.school_id) if lesson_schedule.school_id else None,
                'schoolName': lesson_schedule.school.school_name if lesson_schedule.school else '',
                'brandId': None,
                'brandName': '',
                'brandCategoryName': '',
                'roomName': '',
                'className': '振替授業',
                'displayCourseName': '振替授業',
                'displayPairName': '',
                'transferGroup': '',
                'calendarPattern': '',
                'absenceTicketId': None,
            })

        return Response({
            'studentId': str(student.id),
            'studentName': f'{student.last_name}{student.first_name}',
            'dateFrom': date_from.isoformat(),
            'dateTo': date_to.isoformat(),
            'events': events,
        })

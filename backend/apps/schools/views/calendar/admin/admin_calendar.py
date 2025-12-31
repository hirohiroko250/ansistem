"""
AdminCalendarView - 管理者用カレンダーAPI
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Count, Q

from apps.core.permissions import IsTenantUser
from apps.schools.models import LessonCalendar, ClassSchedule, SchoolClosure


class AdminCalendarView(APIView):
    """管理者用カレンダーAPI

    ClassSchedule（基本時間割）とLessonCalendar（日別情報）を
    組み合わせてカレンダーデータを返す。
    出欠情報、ABスワップ、休校日も含む。
    """
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get(self, request):
        """
        指定月のカレンダーデータを返す
        ?school_id=xxx&year=2024&month=12
        ?brand_id=xxx (オプション)
        """
        from datetime import date, timedelta
        import calendar as cal
        from apps.students.models import StudentEnrollment

        school_id = request.query_params.get('school_id')
        brand_id = request.query_params.get('brand_id')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not all([school_id, year, month]):
            return Response(
                {'error': 'school_id, year, month are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return Response(
                {'error': 'year and month must be integers'},
                status=status.HTTP_400_BAD_REQUEST
            )

        first_day = date(year, month, 1)
        last_day = date(year, month, cal.monthrange(year, month)[1])

        # ClassScheduleを取得
        schedules_qs = ClassSchedule.objects.filter(
            school_id=school_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('brand', 'brand_category', 'room', 'grade')

        if brand_id:
            schedules_qs = schedules_qs.filter(brand_id=brand_id)

        # 曜日ごとにスケジュールをグループ化
        schedules_by_day = {}
        for sched in schedules_qs:
            if sched.day_of_week not in schedules_by_day:
                schedules_by_day[sched.day_of_week] = []
            schedules_by_day[sched.day_of_week].append(sched)

        # LessonCalendarを取得（calendar_patternごと）
        calendar_patterns = set(s.calendar_pattern for s in schedules_qs if s.calendar_pattern)
        lesson_calendars = LessonCalendar.objects.filter(
            lesson_date__gte=first_day,
            lesson_date__lte=last_day
        ).filter(
            Q(calendar_code__in=calendar_patterns) |
            Q(school_id=school_id)
        )
        lesson_cal_dict = {}
        for lc in lesson_calendars:
            key = (lc.lesson_date, lc.calendar_code or f"{lc.school_id}_{lc.brand_id}")
            lesson_cal_dict[key] = lc

        # SchoolClosureを取得
        closures = SchoolClosure.objects.filter(
            school_id=school_id,
            closure_date__gte=first_day,
            closure_date__lte=last_day,
            deleted_at__isnull=True
        )
        if brand_id:
            closures = closures.filter(Q(brand_id=brand_id) | Q(brand_id__isnull=True))
        closure_dates = {c.closure_date: c for c in closures}

        # StudentEnrollmentを取得（各クラスの受講者数）
        enrollments = StudentEnrollment.objects.filter(
            class_schedule__school_id=school_id,
            status='enrolled',
            deleted_at__isnull=True
        ).values('class_schedule_id').annotate(count=Count('id'))
        enrollment_counts = {e['class_schedule_id']: e['count'] for e in enrollments}

        # 日付ごとのカレンダーデータを生成
        calendar_data = []
        current_date = first_day
        day_names = {1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'}

        while current_date <= last_day:
            day_of_week = current_date.isoweekday()
            is_weekend = day_of_week in [6, 7]

            day_data = {
                'date': current_date.isoformat(),
                'day': current_date.day,
                'dayOfWeek': day_of_week,
                'dayName': day_names.get(day_of_week, ''),
                'isWeekend': is_weekend,
                'isClosed': False,
                'closureReason': None,
                'events': [],
            }

            # 休校日チェック
            closure = closure_dates.get(current_date)
            if closure:
                day_data['isClosed'] = True
                day_data['closureReason'] = closure.reason

            # 該当曜日のスケジュールを取得
            day_schedules = schedules_by_day.get(day_of_week, [])

            for sched in day_schedules:
                # LessonCalendarからlesson_type取得
                cal_key = (current_date, sched.calendar_pattern) if sched.calendar_pattern else None
                lesson_cal = lesson_cal_dict.get(cal_key) if cal_key else None

                # 開講チェック
                is_open = True
                lesson_type = 'A'  # デフォルト
                if lesson_cal:
                    is_open = lesson_cal.is_open
                    lesson_type = lesson_cal.lesson_type or 'A'
                if closure and not closure.schedule_id:
                    is_open = False

                if not is_open:
                    continue

                # 受講者数
                enrolled_count = enrollment_counts.get(sched.id, 0)

                event_data = {
                    'id': str(sched.id),
                    'scheduleCode': sched.schedule_code,
                    'className': sched.class_name,
                    'displayCourseName': sched.display_course_name,
                    'startTime': sched.start_time.strftime('%H:%M') if sched.start_time else None,
                    'endTime': sched.end_time.strftime('%H:%M') if sched.end_time else None,
                    'period': sched.period,
                    'brandId': str(sched.brand.id) if sched.brand else None,
                    'brandName': sched.brand.brand_name if sched.brand else None,
                    'brandColor': sched.brand.color_primary if sched.brand else None,
                    'lessonType': lesson_type,
                    'lessonTypeLabel': {
                        'A': '外国人あり',
                        'B': '日本人のみ',
                        'P': 'ペア',
                        'Y': 'インター',
                    }.get(lesson_type, lesson_type),
                    'capacity': sched.capacity,
                    'enrolledCount': enrolled_count,
                    'availableSeats': max(0, sched.capacity - enrolled_count),
                    'roomName': sched.room.classroom_name if sched.room else sched.room_name,
                    'calendarPattern': sched.calendar_pattern,
                    'ticketName': sched.ticket_name,
                }
                day_data['events'].append(event_data)

            # イベントを時間順にソート
            day_data['events'].sort(key=lambda x: x['startTime'] or '00:00')

            calendar_data.append(day_data)
            current_date += timedelta(days=1)

        return Response({
            'year': year,
            'month': month,
            'schoolId': school_id,
            'brandId': brand_id,
            'days': calendar_data
        })

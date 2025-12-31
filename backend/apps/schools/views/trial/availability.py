"""
Trial Availability Views - 体験枠空き状況Views
PublicTrialAvailabilityView, PublicTrialMonthlyAvailabilityView
"""
from datetime import datetime, date
import calendar as cal
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from ...models import SchoolSchedule, LessonCalendar, ClassSchedule
from .utils import get_school_year_from_birth_date


class PublicTrialAvailabilityView(APIView):
    """体験枠空き状況API（日付指定・認証不要）

    機能:
    - LessonCalendarで休講日チェック
    - 外国人講師チェック: lesson_type='B'（日本人のみ）の日は体験不可
    - birth_dateで生徒の学年をフィルター
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        指定日の体験枠空き状況を返す
        ?school_id=xxx&brand_id=xxx&date=2024-12-25&birth_date=2014-05-15
        """
        from apps.students.models import TrialBooking

        school_id = request.query_params.get('school_id')
        brand_id = request.query_params.get('brand_id')
        date_str = request.query_params.get('date')
        birth_date_str = request.query_params.get('birth_date')

        if not all([school_id, brand_id, date_str]):
            return Response(
                {'error': 'school_id, brand_id, date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 生年月日から生徒の学年を取得
        student_school_year = None
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                student_school_year = get_school_year_from_birth_date(birth_date)
            except ValueError:
                pass

        # 曜日を取得（1=月曜日）
        day_of_week = target_date.isoweekday()

        # ClassScheduleからcalendar_patternを取得
        class_schedules = ClassSchedule.objects.filter(
            school_id=school_id,
            brand_id=brand_id,
            day_of_week=day_of_week,
            is_active=True,
            deleted_at__isnull=True
        )
        calendar_patterns = set(cs.calendar_pattern for cs in class_schedules if cs.calendar_pattern)

        # LessonCalendarで休校日・外国人講師チェック
        calendar_entry = None
        is_japanese_only = False

        if calendar_patterns:
            for pattern in calendar_patterns:
                entry = LessonCalendar.objects.filter(
                    calendar_code=pattern,
                    lesson_date=target_date
                ).first()
                if entry:
                    calendar_entry = entry
                    if entry.lesson_type == 'B':
                        is_japanese_only = True
                    break

        if not calendar_entry:
            calendar_entry = LessonCalendar.objects.filter(
                brand_id=brand_id,
                school_id=school_id,
                lesson_date=target_date
            ).first()
            if calendar_entry and calendar_entry.lesson_type == 'B':
                is_japanese_only = True

        # 休講日チェック
        if calendar_entry and not calendar_entry.is_open:
            return Response({
                'date': date_str,
                'isAvailable': False,
                'reason': 'closed',
                'holidayName': calendar_entry.holiday_name or '休講日',
                'slots': []
            })

        # 日本人講師のみの日は体験不可
        if is_japanese_only:
            return Response({
                'date': date_str,
                'isAvailable': False,
                'reason': 'japanese_only',
                'message': 'この日は日本人講師のみのため体験授業は受け付けておりません',
                'lessonType': 'B',
                'slots': []
            })

        # ClassScheduleから該当曜日のスケジュールを取得
        class_schedules = ClassSchedule.objects.filter(
            school_id=school_id,
            brand_id=brand_id,
            day_of_week=day_of_week,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('grade').prefetch_related('grade__school_years').order_by('start_time')

        # 生徒の学年でフィルター
        if student_school_year:
            filtered_schedules = []
            for cs in class_schedules:
                if cs.grade:
                    if cs.grade.school_years.filter(id=student_school_year.id).exists():
                        filtered_schedules.append(cs)
                else:
                    filtered_schedules.append(cs)
            class_schedules = filtered_schedules

        # SchoolScheduleも取得
        school_schedules = SchoolSchedule.objects.filter(
            school_id=school_id,
            brand_id=brand_id,
            day_of_week=day_of_week,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('time_slot')

        ss_by_time = {}
        for ss in school_schedules:
            time_key = f"{ss.time_slot.start_time.strftime('%H:%M')}"
            ss_by_time[time_key] = ss

        slots = []

        if class_schedules:
            for cs in class_schedules:
                start_time_key = cs.start_time.strftime('%H:%M')
                ss = ss_by_time.get(start_time_key)
                if ss:
                    booked_count = TrialBooking.get_booked_count(ss.id, target_date)
                else:
                    booked_count = 0

                trial_capacity = cs.trial_capacity or 2
                available_count = max(0, trial_capacity - booked_count)
                time_str = f"{cs.start_time.strftime('%H:%M')}-{cs.end_time.strftime('%H:%M')}"

                slots.append({
                    'scheduleId': str(ss.id) if ss else str(cs.id),
                    'classScheduleId': str(cs.id),
                    'className': cs.class_name,
                    'time': time_str,
                    'startTime': cs.start_time.strftime('%H:%M'),
                    'endTime': cs.end_time.strftime('%H:%M'),
                    'trialCapacity': trial_capacity,
                    'bookedCount': booked_count,
                    'availableCount': available_count,
                    'isAvailable': available_count > 0,
                    'gradeName': cs.grade.grade_name if cs.grade else None,
                    'gradeId': str(cs.grade.id) if cs.grade else None,
                    'gradeSortOrder': cs.grade.sort_order if cs.grade else 9999,
                    'displayCourseName': cs.display_course_name,
                })
        else:
            for ss in school_schedules:
                booked_count = TrialBooking.get_booked_count(ss.id, target_date)
                trial_capacity = ss.trial_capacity or 2
                available_count = max(0, trial_capacity - booked_count)
                time_str = f"{ss.time_slot.start_time.strftime('%H:%M')}-{ss.time_slot.end_time.strftime('%H:%M')}"

                slots.append({
                    'scheduleId': str(ss.id),
                    'classScheduleId': None,
                    'className': None,
                    'time': time_str,
                    'startTime': ss.time_slot.start_time.strftime('%H:%M'),
                    'endTime': ss.time_slot.end_time.strftime('%H:%M'),
                    'trialCapacity': trial_capacity,
                    'bookedCount': booked_count,
                    'availableCount': available_count,
                    'isAvailable': available_count > 0,
                    'gradeName': None,
                    'gradeId': None,
                    'gradeSortOrder': 9999,
                    'displayCourseName': None,
                })

        return Response({
            'date': date_str,
            'schoolId': school_id,
            'brandId': brand_id,
            'isAvailable': any(s['isAvailable'] for s in slots),
            'lessonType': calendar_entry.lesson_type if calendar_entry else None,
            'slots': slots
        })


class PublicTrialMonthlyAvailabilityView(APIView):
    """体験予約月間空き状況API（認証不要）

    指定月の各日の体験枠空き状況を返す
    カレンダー上で体験可能な日を表示するために使用
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        ?school_id=xxx&brand_id=xxx&year=2025&month=12
        """
        from apps.students.models import TrialBooking

        school_id = request.query_params.get('school_id')
        brand_id = request.query_params.get('brand_id')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not all([school_id, brand_id, year, month]):
            return Response(
                {'error': 'school_id, brand_id, year, month are required'},
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

        # スケジュールを取得
        class_schedules = ClassSchedule.objects.filter(
            school_id=school_id,
            brand_id=brand_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('grade')

        if class_schedules.exists():
            schedules_by_day = {}
            for sched in class_schedules:
                if sched.day_of_week not in schedules_by_day:
                    schedules_by_day[sched.day_of_week] = []
                schedules_by_day[sched.day_of_week].append({
                    'id': sched.id,
                    'trial_capacity': sched.trial_capacity or 2,
                })
            use_class_schedule = True
        else:
            school_schedules = SchoolSchedule.objects.filter(
                school_id=school_id,
                brand_id=brand_id,
                is_active=True,
                deleted_at__isnull=True
            ).select_related('time_slot')

            schedules_by_day = {}
            for sched in school_schedules:
                if sched.day_of_week not in schedules_by_day:
                    schedules_by_day[sched.day_of_week] = []
                schedules_by_day[sched.day_of_week].append({
                    'id': sched.id,
                    'trial_capacity': sched.trial_capacity or 2,
                })
            use_class_schedule = False

        # 休講日を取得
        closures = LessonCalendar.objects.filter(
            brand_id=brand_id,
            school_id=school_id,
            lesson_date__gte=first_day,
            lesson_date__lte=last_day,
            is_open=False
        ).values_list('lesson_date', flat=True)
        closure_dates = set(closures)

        # 日本人講師のみの日を取得
        japanese_only_entries = LessonCalendar.objects.filter(
            brand_id=brand_id,
            school_id=school_id,
            lesson_date__gte=first_day,
            lesson_date__lte=last_day,
            lesson_type='B'
        ).values_list('lesson_date', flat=True)
        japanese_only_dates = set(japanese_only_entries)

        if use_class_schedule:
            calendar_patterns = set(cs.calendar_pattern for cs in class_schedules if cs.calendar_pattern)
            if calendar_patterns:
                pattern_entries = LessonCalendar.objects.filter(
                    calendar_code__in=calendar_patterns,
                    lesson_date__gte=first_day,
                    lesson_date__lte=last_day,
                    lesson_type='B'
                ).values_list('lesson_date', flat=True)
                japanese_only_dates.update(pattern_entries)

        # 日付ごとの空き状況を計算
        daily_availability = []
        current_date = first_day
        while current_date <= last_day:
            day_of_week = current_date.isoweekday()

            day_data = {
                'date': current_date.isoformat(),
                'dayOfWeek': day_of_week,
                'isOpen': True,
                'totalCapacity': 0,
                'bookedCount': 0,
                'availableCount': 0,
                'isAvailable': False,
            }

            if current_date in closure_dates:
                day_data['isOpen'] = False
                day_data['reason'] = 'closed'
                daily_availability.append(day_data)
                next_day = current_date.day + 1
                if next_day > cal.monthrange(year, month)[1]:
                    break
                current_date = date(year, month, next_day)
                continue

            if current_date in japanese_only_dates:
                day_data['isOpen'] = False
                day_data['reason'] = 'japanese_only'
                daily_availability.append(day_data)
                next_day = current_date.day + 1
                if next_day > cal.monthrange(year, month)[1]:
                    break
                current_date = date(year, month, next_day)
                continue

            if day_of_week in schedules_by_day:
                day_schedules = schedules_by_day[day_of_week]
                total_capacity = 0
                total_booked = 0

                for sched_info in day_schedules:
                    trial_cap = sched_info['trial_capacity']
                    total_capacity += trial_cap
                    if not use_class_schedule:
                        booked = TrialBooking.get_booked_count(sched_info['id'], current_date)
                        total_booked += booked

                available = max(0, total_capacity - total_booked)
                day_data['totalCapacity'] = total_capacity
                day_data['bookedCount'] = total_booked
                day_data['availableCount'] = available
                day_data['isAvailable'] = available > 0 or total_capacity > 0
            else:
                day_data['isOpen'] = False
                day_data['reason'] = 'no_schedule'

            daily_availability.append(day_data)

            next_day = current_date.day + 1
            if next_day > cal.monthrange(year, month)[1]:
                break
            current_date = date(year, month, next_day)

        return Response({
            'year': year,
            'month': month,
            'schoolId': school_id,
            'brandId': brand_id,
            'days': daily_availability
        })

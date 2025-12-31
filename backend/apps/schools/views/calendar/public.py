"""
Public Calendar Views - 公開カレンダーAPI（認証不要）
PublicLessonCalendarView, PublicCalendarSeatsView
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.schools.models import LessonCalendar, ClassSchedule


class PublicLessonCalendarView(APIView):
    """開講カレンダーAPI（認証不要・保護者向け）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        指定月の開講カレンダーを返す
        ?brand_id=xxx&school_id=xxx&year=2024&month=12
        """
        from datetime import date
        import calendar as cal

        brand_id = request.query_params.get('brand_id')
        school_id = request.query_params.get('school_id')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not all([brand_id, school_id, year, month]):
            return Response(
                {'error': 'brand_id, school_id, year, month are required'},
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

        # 月の開始日と終了日
        first_day = date(year, month, 1)
        last_day = date(year, month, cal.monthrange(year, month)[1])

        calendars = LessonCalendar.objects.filter(
            brand_id=brand_id,
            school_id=school_id,
            lesson_date__gte=first_day,
            lesson_date__lte=last_day
        ).order_by('lesson_date')

        calendar_data = []
        for item in calendars:
            calendar_data.append({
                'date': item.lesson_date.isoformat(),
                'dayOfWeek': item.day_of_week,
                'isOpen': item.is_open,
                'lessonType': item.lesson_type,
                'displayLabel': item.display_label,
                'ticketType': item.ticket_type,
                'ticketSequence': item.ticket_sequence,
                'noticeMessage': item.notice_message,
                'holidayName': item.holiday_name,
                'isNativeDay': item.lesson_type == 'A',  # Aパターン = 外国人講師あり
                'isJapaneseOnly': item.lesson_type == 'B',  # Bパターン = 日本人講師のみ
            })

        return Response({
            'year': year,
            'month': month,
            'brandId': brand_id,
            'schoolId': school_id,
            'calendar': calendar_data
        })


class PublicCalendarSeatsView(APIView):
    """通常授業月間座席状況API（認証不要）

    指定月の各日の座席状況を返す
    受講生と残り席数を表示するために使用
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        ?school_id=xxx&brand_id=xxx&year=2025&month=12
        """
        from datetime import date
        import calendar as cal

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

        # 月の開始日と終了日
        first_day = date(year, month, 1)
        last_day = date(year, month, cal.monthrange(year, month)[1])

        # ClassScheduleから校舎・ブランドの開講時間割を取得
        class_schedules = ClassSchedule.objects.filter(
            school_id=school_id,
            brand_id=brand_id,
            is_active=True,
            deleted_at__isnull=True
        )

        # 曜日ごとの時間割をまとめる
        schedules_by_day = {}
        for sched in class_schedules:
            if sched.day_of_week not in schedules_by_day:
                schedules_by_day[sched.day_of_week] = []
            schedules_by_day[sched.day_of_week].append(sched)

        # LessonCalendarで休講日を取得
        lesson_cal = LessonCalendar.objects.filter(
            brand_id=brand_id,
            school_id=school_id,
            lesson_date__gte=first_day,
            lesson_date__lte=last_day
        )
        lesson_cal_dict = {lc.lesson_date: lc for lc in lesson_cal}

        # 日付ごとの座席状況を計算
        daily_seats = []
        current_date = first_day
        while current_date <= last_day:
            day_of_week = current_date.isoweekday()  # 1=月曜日

            day_data = {
                'date': current_date.isoformat(),
                'dayOfWeek': day_of_week,
                'isOpen': True,
                'totalCapacity': 0,
                'enrolledCount': 0,
                'availableSeats': 0,
                'lessonType': None,
                'ticketType': None,
                'holidayName': None,
            }

            # LessonCalendarから授業情報を取得
            cal_entry = lesson_cal_dict.get(current_date)
            if cal_entry:
                day_data['isOpen'] = cal_entry.is_open
                day_data['lessonType'] = cal_entry.lesson_type
                day_data['ticketType'] = cal_entry.ticket_type
                day_data['holidayName'] = cal_entry.holiday_name

                if not cal_entry.is_open:
                    daily_seats.append(day_data)
                    next_day = current_date.day + 1
                    if next_day > cal.monthrange(year, month)[1]:
                        break
                    current_date = date(year, month, next_day)
                    continue

            # 当該曜日の時間割があるか
            if day_of_week in schedules_by_day:
                day_schedules = schedules_by_day[day_of_week]
                total_capacity = 0
                total_enrolled = 0

                for sched in day_schedules:
                    total_capacity += sched.capacity
                    total_enrolled += sched.reserved_seats or 0

                day_data['totalCapacity'] = total_capacity
                day_data['enrolledCount'] = total_enrolled
                day_data['availableSeats'] = max(0, total_capacity - total_enrolled)
            else:
                # 開講曜日ではない
                day_data['isOpen'] = False

            daily_seats.append(day_data)

            # 次の日に進む
            next_day = current_date.day + 1
            if next_day > cal.monthrange(year, month)[1]:
                break
            current_date = date(year, month, next_day)

        return Response({
            'year': year,
            'month': month,
            'schoolId': school_id,
            'brandId': brand_id,
            'days': daily_seats
        })

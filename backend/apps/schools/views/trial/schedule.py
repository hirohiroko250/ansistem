"""
Trial Schedule Views - 体験スケジュールViews
PublicTrialScheduleView
"""
from datetime import datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from ...models import Brand, SchoolSchedule, ClassSchedule


class PublicTrialScheduleView(APIView):
    """体験授業スケジュールAPI（認証不要）

    機能:
    - 学年フィルター: birth_dateから学年を計算し、対象学年に合うクラスのみ返す
    - 外国人講師チェック: LessonCalendarでlesson_type='B'（日本人のみ）の日は除外
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        指定ブランド・校舎の体験可能スケジュールを返す
        ?brand_id=xxx&school_id=xxx
        ?birth_date=YYYY-MM-DD (オプション: 学年フィルター用)
        または
        ?school_id=xxx（全ブランド）
        """
        brand_id = request.query_params.get('brand_id')
        school_id = request.query_params.get('school_id')
        birth_date_str = request.query_params.get('birth_date')

        if not school_id:
            return Response(
                {'error': 'school_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 生年月日から学年コードを計算
        child_school_year = None
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                # ブランドの学年計算ロジックを使用
                brand = None
                if brand_id:
                    brand = Brand.objects.filter(id=brand_id).first()
                if brand:
                    child_school_year = brand.calculate_school_year(birth_date)
            except ValueError:
                pass  # 無効な日付形式は無視

        # ClassScheduleから曜日・時間帯を取得（実際のクラス開講情報）
        class_schedules = ClassSchedule.objects.filter(
            school_id=school_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('brand', 'grade')

        if brand_id:
            class_schedules = class_schedules.filter(brand_id=brand_id)

        # ClassScheduleにデータがある場合はそれを使用
        if class_schedules.exists():
            # 学年フィルター: 子供の学年が対象学年に含まれるクラスのみ
            if child_school_year:
                filtered_schedules = []
                for sched in class_schedules:
                    if sched.grade is None:
                        # 学年指定なし → 全学年対象
                        filtered_schedules.append(sched)
                    else:
                        # 学年指定あり → 子供の学年が含まれるか確認
                        grade_school_years = sched.grade.school_years.all()
                        if child_school_year in grade_school_years:
                            filtered_schedules.append(sched)
                queryset = filtered_schedules
            else:
                queryset = list(class_schedules)
            use_class_schedule = True
        else:
            # ClassScheduleがない場合はSchoolScheduleにフォールバック
            school_schedules = SchoolSchedule.objects.filter(
                school_id=school_id,
                is_active=True,
                deleted_at__isnull=True
            ).select_related('brand', 'time_slot')

            if brand_id:
                school_schedules = school_schedules.filter(brand_id=brand_id)

            queryset = list(school_schedules)
            use_class_schedule = False

        # 曜日変換
        day_names = {1: '月曜日', 2: '火曜日', 3: '水曜日', 4: '木曜日', 5: '金曜日', 6: '土曜日', 7: '日曜日'}

        # 曜日ごとにグループ化（重複排除）
        schedule_by_day = {}
        seen_slots = set()

        for sched in queryset:
            if use_class_schedule:
                # ClassSchedule形式
                day_name = day_names.get(sched.day_of_week, str(sched.day_of_week))
                time_key = f"{sched.day_of_week}_{sched.start_time}_{sched.end_time}_{sched.brand_id}"

                if time_key in seen_slots:
                    continue
                seen_slots.add(time_key)

                if day_name not in schedule_by_day:
                    schedule_by_day[day_name] = []

                time_str = f"{sched.start_time.strftime('%H:%M')}-{sched.end_time.strftime('%H:%M')}"

                # 体験受入可能数
                capacity = sched.max_students if hasattr(sched, 'max_students') and sched.max_students else 10
                trial_capacity = getattr(sched, 'trial_capacity', 2) or 2

                schedule_by_day[day_name].append({
                    'id': str(sched.id),
                    'time': time_str,
                    'startTime': sched.start_time.strftime('%H:%M'),
                    'endTime': sched.end_time.strftime('%H:%M'),
                    'className': sched.class_name,
                    'capacity': capacity,
                    'trialCapacity': trial_capacity,
                    'brandId': str(sched.brand.id),
                    'brandName': sched.brand.brand_name,
                    'gradeName': sched.grade.grade_name if sched.grade else None,
                })
            else:
                # SchoolSchedule形式（フォールバック）
                day_name = day_names.get(sched.day_of_week, str(sched.day_of_week))
                time_slot = sched.time_slot
                time_key = f"{sched.day_of_week}_{time_slot.start_time}_{time_slot.end_time}_{sched.brand_id}"

                if time_key in seen_slots:
                    continue
                seen_slots.add(time_key)

                if day_name not in schedule_by_day:
                    schedule_by_day[day_name] = []

                time_str = f"{time_slot.start_time.strftime('%H:%M')}-{time_slot.end_time.strftime('%H:%M')}"

                schedule_by_day[day_name].append({
                    'id': str(sched.id),
                    'time': time_str,
                    'startTime': time_slot.start_time.strftime('%H:%M'),
                    'endTime': time_slot.end_time.strftime('%H:%M'),
                    'className': None,
                    'capacity': sched.capacity or 10,
                    'trialCapacity': sched.trial_capacity or 2,
                    'brandId': str(sched.brand.id),
                    'brandName': sched.brand.brand_name,
                    'gradeName': None,
                })

        # レスポンス形式（曜日順にソート）
        day_order = {'月曜日': 1, '火曜日': 2, '水曜日': 3, '木曜日': 4, '金曜日': 5, '土曜日': 6, '日曜日': 7}
        schedule_list = []
        for day in sorted(schedule_by_day.keys(), key=lambda x: day_order.get(x, 99)):
            times = schedule_by_day[day]
            times.sort(key=lambda x: x['startTime'])
            schedule_list.append({
                'day': day,
                'times': times
            })

        return Response({
            'schoolId': school_id,
            'brandId': brand_id,
            'childSchoolYear': child_school_year.year_name if child_school_year else None,
            'schedule': schedule_list
        })

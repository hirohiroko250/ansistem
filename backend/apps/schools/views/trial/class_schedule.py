"""
Public Class Schedule Views - 開講時間割Views
PublicClassScheduleView
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from ...models import ClassSchedule


class PublicClassScheduleView(APIView):
    """開講時間割API（認証不要・保護者向け）

    校舎・ブランドごとの開講時間割を曜日・時限でグループ化して返す
    クラス選択画面やクラス登録画面で使用
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        指定校舎・ブランドの開講時間割を返す
        ?school_id=xxx&brand_id=xxx
        または
        ?school_id=xxx&brand_category_id=xxx（ブランドカテゴリで絞り込み）
        または
        ?school_id=xxx&ticket_id=xxx（チケットIDで絞り込み）
        """
        from apps.contracts.models import Ticket

        school_id = request.query_params.get('school_id')
        brand_id = request.query_params.get('brand_id')
        brand_category_id = request.query_params.get('brand_category_id')
        ticket_id = request.query_params.get('ticket_id')

        if not school_id:
            return Response(
                {'error': 'school_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ClassScheduleから開講時間割を取得
        queryset = ClassSchedule.objects.filter(
            school_id=school_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('brand', 'brand_category', 'school', 'room')

        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        if brand_category_id:
            queryset = queryset.filter(brand_category_id=brand_category_id)
        if ticket_id:
            # チケットIDから同じtransfer_groupのスケジュールを取得
            ticket_schedule = ClassSchedule.objects.filter(ticket_id=ticket_id).first()
            if ticket_schedule and ticket_schedule.transfer_group:
                queryset = queryset.filter(transfer_group=ticket_schedule.transfer_group)
            else:
                ticket = Ticket.objects.filter(ticket_code=ticket_id).first()
                if ticket and ticket.ticket_name:
                    class_names = ['White', 'Yellow', 'Red', 'Purple', 'Kids', 'Jr', 'ジュニア', 'キッズ']
                    transfer_group = None
                    for name in class_names:
                        if name in ticket.ticket_name:
                            transfer_group = name
                            break
                    if transfer_group:
                        queryset = queryset.filter(transfer_group=transfer_group)
                    else:
                        queryset = queryset.filter(ticket_id=ticket_id)
                else:
                    queryset = queryset.filter(ticket_id=ticket_id)

        # 曜日名マッピング
        day_short_names = {1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'}

        # 時間帯ごとにグループ化
        schedules_by_time = {}
        for sched in queryset.order_by('day_of_week', 'period', 'start_time'):
            start_hour = sched.start_time.strftime('%H:00') if sched.start_time else '00:00'

            if start_hour not in schedules_by_time:
                schedules_by_time[start_hour] = {day: [] for day in range(1, 8)}

            schedule_data = {
                'id': str(sched.id),
                'scheduleCode': sched.schedule_code,
                'className': sched.class_name,
                'classType': sched.class_type,
                'displayCourseName': sched.display_course_name,
                'displayPairName': sched.display_pair_name,
                'displayDescription': sched.display_description,
                'period': sched.period,
                'startTime': sched.start_time.strftime('%H:%M') if sched.start_time else None,
                'endTime': sched.end_time.strftime('%H:%M') if sched.end_time else None,
                'durationMinutes': sched.duration_minutes,
                'capacity': sched.capacity,
                'trialCapacity': sched.trial_capacity,
                'reservedSeats': sched.reserved_seats,
                'availableSeats': max(0, sched.capacity - sched.reserved_seats),
                'transferGroup': sched.transfer_group,
                'calendarPattern': sched.calendar_pattern,
                'approvalType': sched.approval_type,
                'roomName': sched.room.classroom_name if sched.room else sched.room_name,
                'brandId': str(sched.brand.id) if sched.brand else None,
                'brandName': sched.brand.brand_name if sched.brand else None,
                'brandCategoryId': str(sched.brand_category.id) if sched.brand_category else None,
                'brandCategoryName': sched.brand_category.category_name if sched.brand_category else None,
                'ticketName': sched.ticket_name,
                'ticketId': sched.ticket_id,
                'gradeCode': getattr(sched, 'grade', None) and sched.grade.grade_code if hasattr(sched, 'grade') and sched.grade else None,
                'gradeName': getattr(sched, 'grade', None) and sched.grade.grade_name if hasattr(sched, 'grade') and sched.grade else None,
            }
            schedules_by_time[start_hour][sched.day_of_week].append(schedule_data)

        # レスポンス形式に変換
        time_slots_response = []
        for time_key in sorted(schedules_by_time.keys()):
            day_schedules = schedules_by_time[time_key]
            days_availability = {}
            for day_num in range(1, 8):
                schedules_for_day = day_schedules[day_num]
                if not schedules_for_day:
                    days_availability[day_short_names[day_num]] = {
                        'status': 'none',
                        'schedules': []
                    }
                else:
                    total_capacity = sum(s['capacity'] for s in schedules_for_day)
                    total_reserved = sum(s['reservedSeats'] for s in schedules_for_day)
                    available = total_capacity - total_reserved

                    if available <= 0:
                        slot_status = 'full'
                    elif available <= 2:
                        slot_status = 'few'
                    else:
                        slot_status = 'available'

                    days_availability[day_short_names[day_num]] = {
                        'status': slot_status,
                        'totalCapacity': total_capacity,
                        'totalReserved': total_reserved,
                        'availableSeats': available,
                        'schedules': schedules_for_day
                    }

            time_slots_response.append({
                'time': time_key,
                'days': days_availability
            })

        return Response({
            'schoolId': school_id,
            'brandId': brand_id,
            'brandCategoryId': brand_category_id,
            'timeSlots': time_slots_response,
            'dayLabels': ['月', '火', '水', '木', '金', '土', '日']
        })

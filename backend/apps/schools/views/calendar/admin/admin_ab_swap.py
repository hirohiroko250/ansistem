"""
AdminCalendarABSwapView - ABスワップAPI
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.permissions import IsTenantUser
from apps.schools.models import LessonCalendar, ClassSchedule


class AdminCalendarABSwapView(APIView):
    """ABスワップAPI

    指定した日付・カレンダーパターンのABタイプを切り替える。
    A -> B, B -> A のスワップを行う。
    """
    permission_classes = [IsAuthenticated, IsTenantUser]

    def post(self, request):
        """
        ABスワップを実行

        Body:
            calendar_pattern: カレンダーパターン (例: 1001_SKAEC_A)
            date: 日付 (YYYY-MM-DD)
            new_type: 新しいタイプ (A, B) - オプション、指定しない場合は自動切り替え
        """
        from datetime import datetime
        import logging

        logger = logging.getLogger(__name__)

        calendar_pattern = request.data.get('calendar_pattern')
        date_str = request.data.get('date')
        new_type = request.data.get('new_type')

        if not all([calendar_pattern, date_str]):
            return Response(
                {'error': 'calendar_pattern and date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lesson_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # LessonCalendarを取得または作成
            lesson_calendar = LessonCalendar.objects.filter(
                calendar_code=calendar_pattern,
                lesson_date=lesson_date
            ).first()

            if not lesson_calendar:
                # ClassScheduleからschool, brand, tenant情報を取得
                class_schedule = ClassSchedule.objects.filter(
                    calendar_pattern=calendar_pattern,
                    deleted_at__isnull=True
                ).first()

                if not class_schedule:
                    return Response(
                        {'error': f'ClassSchedule not found for calendar_pattern: {calendar_pattern}'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # 新しいLessonCalendarを作成
                lesson_calendar = LessonCalendar.objects.create(
                    tenant_id=class_schedule.tenant_id,
                    calendar_code=calendar_pattern,
                    lesson_date=lesson_date,
                    school=class_schedule.school,
                    brand=class_schedule.brand,
                    lesson_type='A',  # デフォルト
                    is_open=True,
                )

            old_type = lesson_calendar.lesson_type or 'A'

            # 新しいタイプを決定
            if new_type:
                if new_type not in ['A', 'B', 'P', 'Y']:
                    return Response(
                        {'error': 'new_type must be A, B, P, or Y'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                lesson_calendar.lesson_type = new_type
            else:
                # 自動切り替え: A <-> B
                if old_type == 'A':
                    lesson_calendar.lesson_type = 'B'
                elif old_type == 'B':
                    lesson_calendar.lesson_type = 'A'
                else:
                    return Response(
                        {'error': f'Cannot auto-swap type {old_type}. Please specify new_type.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            lesson_calendar.save()

            # 操作ログを記録
            try:
                from apps.schools.models import CalendarOperationLog
                CalendarOperationLog.log_ab_swap(
                    tenant_id=lesson_calendar.tenant_id,
                    school=lesson_calendar.school,
                    brand=lesson_calendar.brand,
                    lesson_calendar=lesson_calendar,
                    old_type=old_type,
                    new_type=lesson_calendar.lesson_type,
                    user=request.user if request.user.is_authenticated else None,
                )
            except Exception as log_error:
                # ログ記録に失敗してもスワップは成功とする
                logger.warning(f"Failed to log AB swap: {log_error}")

            return Response({
                'success': True,
                'calendar_pattern': calendar_pattern,
                'date': date_str,
                'old_type': old_type,
                'new_type': lesson_calendar.lesson_type,
                'message': f'{old_type} → {lesson_calendar.lesson_type} に変更しました',
            })

        except Exception as e:
            logger.error(f"AB swap error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

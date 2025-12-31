"""
Google Calendar Views - Googleカレンダー連携関連
GoogleCalendarEventsView, GoogleCalendarListView
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.permissions import IsTenantUser


class GoogleCalendarEventsView(APIView):
    """Google Calendar イベント取得API

    Google Calendarからイベントを取得して返す。
    月表示と週表示に対応。
    """
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get(self, request):
        """
        Google Calendarのイベントを取得

        Query Parameters:
            calendar_id: GoogleカレンダーID（必須）
            view: 'month' or 'week' (デフォルト: 'month')
            year: 年 (view=monthの場合必須)
            month: 月 (view=monthの場合必須)
            week_start: 週の開始日 (view=weekの場合必須, YYYY-MM-DD形式)

        Returns:
            イベントリスト
        """
        from datetime import datetime
        from ..services.google_calendar import GoogleCalendarService

        calendar_id = request.query_params.get('calendar_id')
        view = request.query_params.get('view', 'month')
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        week_start = request.query_params.get('week_start')

        if not calendar_id:
            return Response(
                {'error': 'calendar_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = GoogleCalendarService()

        if view == 'month':
            if not all([year, month]):
                return Response(
                    {'error': 'year and month are required for month view'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                events = service.get_events_for_month(
                    calendar_id,
                    int(year),
                    int(month)
                )
            except Exception as e:
                return Response(
                    {'error': f'Failed to fetch events: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        elif view == 'week':
            if not week_start:
                return Response(
                    {'error': 'week_start is required for week view'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                week_start_date = datetime.strptime(week_start, '%Y-%m-%d')
                events = service.get_events_for_week(calendar_id, week_start_date)
            except ValueError:
                return Response(
                    {'error': 'week_start must be in YYYY-MM-DD format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {'error': f'Failed to fetch events: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {'error': 'view must be "month" or "week"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'calendarId': calendar_id,
            'view': view,
            'events': events
        })


class GoogleCalendarListView(APIView):
    """Google Calendar 一覧取得API

    アクセス可能なカレンダー一覧を返す。
    """
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get(self, request):
        """
        アクセス可能なカレンダー一覧を取得

        Returns:
            カレンダーリスト
        """
        from ..services.google_calendar import GoogleCalendarService

        service = GoogleCalendarService()
        calendars = service.list_calendars()

        return Response({
            'calendars': calendars
        })

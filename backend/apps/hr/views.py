"""
HR Views - 勤怠管理ビュー
"""
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum

from apps.core.permissions import IsTenantUser
from .models import HRAttendance
from .serializers import HRAttendanceSerializer


class HRAttendanceViewSet(viewsets.ModelViewSet):
    """勤怠記録ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = HRAttendanceSerializer

    def get_queryset(self):
        queryset = HRAttendance.objects.filter(
            tenant_id=getattr(self.request, 'tenant_id', None),
            user=self.request.user
        )

        # 日付範囲フィルタ
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        # ステータスフィルタ
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-date')

    @action(detail=False, methods=['get'])
    def today(self, request):
        """今日の勤怠記録を取得"""
        today = timezone.localdate()
        try:
            attendance = HRAttendance.objects.get(
                tenant_id=getattr(request, 'tenant_id', None),
                user=request.user,
                date=today
            )
            return Response(HRAttendanceSerializer(attendance).data)
        except HRAttendance.DoesNotExist:
            return Response(
                {'detail': '今日の勤怠記録がありません'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def clock_in(self, request):
        """出勤打刻"""
        today = timezone.localdate()
        now = timezone.now()
        tenant_id = getattr(request, 'tenant_id', None)

        # 既存の記録をチェック
        existing = HRAttendance.objects.filter(
            tenant_id=tenant_id,
            user=request.user,
            date=today
        ).first()

        if existing and existing.clock_in:
            return Response(
                {'error': '既に出勤打刻済みです', 'message': '既に出勤打刻済みです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # QRコード打刻かどうか
        qr_code = request.data.get('qrCode')
        school_id = request.data.get('schoolId')

        if existing:
            existing.clock_in = now
            existing.status = HRAttendance.AttendanceStatus.WORKING
            existing.qr_code_used = bool(qr_code)
            if school_id:
                existing.school_id = school_id
            existing.save()
            attendance = existing
        else:
            attendance = HRAttendance.objects.create(
                tenant_id=tenant_id,
                user=request.user,
                date=today,
                clock_in=now,
                status=HRAttendance.AttendanceStatus.WORKING,
                qr_code_used=bool(qr_code),
                school_id=school_id if school_id else None
            )

        return Response({
            'id': str(attendance.id),
            'clockInTime': attendance.clock_in.isoformat() if attendance.clock_in else None,
            'status': attendance.status,
            'message': '出勤打刻が完了しました'
        })

    @action(detail=False, methods=['post'])
    def clock_out(self, request):
        """退勤打刻"""
        today = timezone.localdate()
        now = timezone.now()
        tenant_id = getattr(request, 'tenant_id', None)

        try:
            attendance = HRAttendance.objects.get(
                tenant_id=tenant_id,
                user=request.user,
                date=today
            )
        except HRAttendance.DoesNotExist:
            return Response(
                {'error': '出勤打刻がありません', 'message': '先に出勤打刻をしてください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if attendance.clock_out:
            return Response(
                {'error': '既に退勤打刻済みです', 'message': '既に退勤打刻済みです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not attendance.clock_in:
            return Response(
                {'error': '出勤打刻がありません', 'message': '先に出勤打刻をしてください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 日報を更新
        daily_report = request.data.get('dailyReport')
        if daily_report:
            attendance.daily_report = daily_report

        attendance.clock_out = now
        attendance.status = HRAttendance.AttendanceStatus.COMPLETED
        attendance.save()

        return Response({
            'id': str(attendance.id),
            'clockInTime': attendance.clock_in.isoformat() if attendance.clock_in else None,
            'clockOutTime': attendance.clock_out.isoformat() if attendance.clock_out else None,
            'workMinutes': attendance.work_minutes,
            'status': attendance.status,
            'message': '退勤打刻が完了しました'
        })

    @action(detail=False, methods=['post'])
    def break_start(self, request):
        """休憩開始"""
        return Response({'message': '休憩開始しました'})

    @action(detail=False, methods=['post'])
    def break_end(self, request):
        """休憩終了"""
        return Response({'message': '休憩終了しました'})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """月別勤怠サマリー"""
        year = request.query_params.get('year', timezone.localdate().year)
        month = request.query_params.get('month', timezone.localdate().month)
        tenant_id = getattr(request, 'tenant_id', None)

        queryset = HRAttendance.objects.filter(
            tenant_id=tenant_id,
            user=request.user,
            date__year=year,
            date__month=month
        )

        aggregates = queryset.aggregate(
            total_work_minutes=Sum('work_minutes'),
            total_overtime_minutes=Sum('overtime_minutes'),
            total_break_minutes=Sum('break_minutes')
        )

        work_days = queryset.filter(
            status=HRAttendance.AttendanceStatus.COMPLETED
        ).count()

        absent_days = queryset.filter(
            status=HRAttendance.AttendanceStatus.ABSENT
        ).count()

        leave_days = queryset.filter(
            status=HRAttendance.AttendanceStatus.LEAVE
        ).count()

        total_work_minutes = aggregates['total_work_minutes'] or 0

        return Response({
            'userId': str(request.user.id),
            'year': int(year),
            'month': int(month),
            'totalWorkDays': work_days,
            'totalWorkMinutes': total_work_minutes,
            'totalOvertimeMinutes': aggregates['total_overtime_minutes'] or 0,
            'totalBreakMinutes': aggregates['total_break_minutes'] or 0,
            'absentDays': absent_days,
            'leaveDays': leave_days,
            'averageWorkMinutes': total_work_minutes // work_days if work_days > 0 else 0
        })

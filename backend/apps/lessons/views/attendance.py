"""
Attendance Views - 出席記録Views
AttendanceViewSet
"""
from datetime import timedelta
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from ..models import Attendance, MakeupLesson
from ..serializers import AttendanceSerializer


class AttendanceViewSet(viewsets.ModelViewSet):
    """出席記録 ViewSet"""
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Attendance.objects.all()
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        student_id = self.request.query_params.get('student')
        schedule_id = self.request.query_params.get('schedule')
        status_filter = self.request.query_params.get('status')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if date_from:
            queryset = queryset.filter(schedule__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(schedule__date__lte=date_to)

        return queryset.select_related('student', 'schedule')

    def partial_update(self, request, *args, **kwargs):
        """欠席登録など出欠更新"""
        instance = self.get_object()

        # ステータス更新
        new_status = request.data.get('status')
        if new_status:
            instance.status = new_status

        # 欠席理由
        absence_reason = request.data.get('absence_reason')
        if absence_reason:
            instance.absence_reason = absence_reason

        # 欠席連絡日時
        if new_status in ['absent', 'absent_notice']:
            instance.absence_notified_at = timezone.now()

        instance.save()

        # 振替申請も行う場合
        if request.data.get('request_makeup') and new_status in ['absent', 'absent_notice']:
            MakeupLesson.objects.create(
                tenant_id=instance.tenant_id,
                original_schedule=instance.schedule,
                student=instance.student,
                reason=absence_reason or '欠席による振替',
                requested_by=request.user,
                valid_until=instance.schedule.date + timedelta(days=90),
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

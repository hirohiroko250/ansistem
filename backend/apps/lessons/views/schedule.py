"""
LessonSchedule Views - 授業スケジュールViews
LessonScheduleViewSet
"""
from datetime import datetime
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import LessonSchedule
from ..serializers import (
    LessonScheduleListSerializer,
    LessonScheduleDetailSerializer,
    LessonScheduleCreateSerializer,
)


class LessonScheduleViewSet(viewsets.ModelViewSet):
    """授業スケジュール ViewSet"""
    queryset = LessonSchedule.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return LessonScheduleListSerializer
        elif self.action == 'create':
            return LessonScheduleCreateSerializer
        return LessonScheduleDetailSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = LessonSchedule.objects.select_related(
            'school', 'classroom', 'subject', 'student', 'teacher', 'time_slot'
        )
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        # フィルタリング
        student_id = self.request.query_params.get('student')
        school_id = self.request.query_params.get('school')
        teacher_id = self.request.query_params.get('teacher')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        lesson_status = self.request.query_params.get('status')
        lesson_type = self.request.query_params.get('lesson_type')

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if lesson_status:
            queryset = queryset.filter(status=lesson_status)
        if lesson_type:
            queryset = queryset.filter(lesson_type=lesson_type)

        # カレンダー形式の場合
        if self.request.query_params.get('format') == 'calendar':
            queryset = queryset.select_related('school', 'subject', 'teacher', 'student')

        return queryset.order_by('date', 'start_time')

    def list(self, request, *args, **kwargs):
        """一覧取得（カレンダー形式対応）"""
        if request.query_params.get('format') == 'calendar':
            queryset = self.filter_queryset(self.get_queryset())
            events = []
            for schedule in queryset:
                start_datetime = datetime.combine(schedule.date, schedule.start_time)
                end_datetime = datetime.combine(schedule.date, schedule.end_time)
                events.append({
                    'id': str(schedule.id),
                    'title': schedule.subject.subject_name if schedule.subject else schedule.class_name or '授業',
                    'start': start_datetime.isoformat(),
                    'end': end_datetime.isoformat(),
                    'type': schedule.lesson_type,
                    'status': schedule.status,
                    'resourceId': str(schedule.school_id) if schedule.school_id else None,
                })
            return Response(events)
        return super().list(request, *args, **kwargs)

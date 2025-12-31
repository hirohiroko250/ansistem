"""
MakeupLesson Views - 振替Views
MakeupLessonViewSet
"""
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import LessonSchedule, MakeupLesson
from ..serializers import MakeupLessonListSerializer, MakeupLessonDetailSerializer
from apps.schools.models import LessonCalendar


class MakeupLessonViewSet(viewsets.ModelViewSet):
    """振替 ViewSet"""
    queryset = MakeupLesson.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return MakeupLessonListSerializer
        return MakeupLessonDetailSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = MakeupLesson.objects.all()
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        student_id = self.request.query_params.get('student')
        status_filter = self.request.query_params.get('status')

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related(
            'student', 'original_schedule', 'makeup_schedule'
        )

    def create(self, request, *args, **kwargs):
        """振替申請"""
        original_schedule_id = request.data.get('original_schedule')
        student_id = request.data.get('student')
        preferred_date = request.data.get('preferred_date')
        preferred_time_slot_id = request.data.get('preferred_time_slot')
        reason = request.data.get('reason', '')

        try:
            original_schedule = LessonSchedule.objects.get(id=original_schedule_id)
        except LessonSchedule.DoesNotExist:
            return Response(
                {'error': '元スケジュールが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 振替申請作成
        makeup = MakeupLesson.objects.create(
            tenant_id=request.tenant_id,
            original_schedule=original_schedule,
            student_id=student_id,
            preferred_date=preferred_date,
            preferred_time_slot_id=preferred_time_slot_id,
            reason=reason,
            requested_by=request.user,
            valid_until=original_schedule.date + timedelta(days=90),
        )

        serializer = MakeupLessonDetailSerializer(makeup)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='available-dates')
    def available_dates(self, request):
        """振替可能日を取得"""
        course_id = request.query_params.get('course')
        school_id = request.query_params.get('school')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if not date_from:
            date_from = datetime.now().date().isoformat()
        if not date_to:
            date_to = (datetime.now() + timedelta(days=60)).date().isoformat()

        # LessonCalendarから開講日を取得
        queryset = LessonCalendar.objects.filter(
            tenant_id=request.tenant_id,
            is_open=True,
            lesson_date__gte=date_from,
            lesson_date__lte=date_to,
        )

        if school_id:
            queryset = queryset.filter(school_id=school_id)

        available_dates = []
        for calendar in queryset:
            available_dates.append({
                'date': calendar.lesson_date.isoformat(),
                'dayOfWeek': calendar.day_of_week,
                'lessonType': calendar.lesson_type,
                'displayLabel': calendar.display_label,
            })

        return Response(available_dates)

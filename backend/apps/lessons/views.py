"""
Lessons Views
授業スケジュール・出欠・振替のAPI
"""
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q
from django.utils import timezone

from .models import (
    TimeSlot, LessonSchedule, LessonRecord,
    Attendance, MakeupLesson, GroupLessonEnrollment
)
from .serializers import (
    TimeSlotSerializer,
    LessonScheduleListSerializer,
    LessonScheduleDetailSerializer,
    LessonScheduleCreateSerializer,
    LessonRecordSerializer,
    AttendanceSerializer,
    MakeupLessonListSerializer,
    MakeupLessonDetailSerializer,
    GroupLessonEnrollmentSerializer,
    CalendarEventSerializer,
)
from apps.schools.models import LessonCalendar


class TimeSlotViewSet(viewsets.ModelViewSet):
    """時間割 ViewSet"""
    queryset = TimeSlot.objects.all()
    serializer_class = TimeSlotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = TimeSlot.objects.filter(is_active=True)
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        school_id = self.request.query_params.get('school')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        return queryset


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
        queryset = LessonSchedule.objects.all()
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


class LessonRecordViewSet(viewsets.ModelViewSet):
    """授業実績 ViewSet"""
    queryset = LessonRecord.objects.all()
    serializer_class = LessonRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = LessonRecord.objects.all()
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        student_id = self.request.query_params.get('student')
        if student_id:
            queryset = queryset.filter(schedule__student_id=student_id)

        return queryset.select_related('schedule', 'schedule__student', 'schedule__teacher')


class GroupLessonEnrollmentViewSet(viewsets.ModelViewSet):
    """集団授業受講者 ViewSet"""
    queryset = GroupLessonEnrollment.objects.all()
    serializer_class = GroupLessonEnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = GroupLessonEnrollment.objects.all()
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        schedule_id = self.request.query_params.get('schedule')
        student_id = self.request.query_params.get('student')

        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        return queryset.select_related('student', 'schedule')

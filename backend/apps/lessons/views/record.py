"""
Lesson Record Views - 授業実績・集団授業受講Views
LessonRecordViewSet, GroupLessonEnrollmentViewSet
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models import LessonRecord, GroupLessonEnrollment
from ..serializers import LessonRecordSerializer, GroupLessonEnrollmentSerializer


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

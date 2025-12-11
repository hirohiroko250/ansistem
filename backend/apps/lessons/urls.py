"""
Lessons URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TimeSlotViewSet,
    LessonScheduleViewSet,
    AttendanceViewSet,
    MakeupLessonViewSet,
    LessonRecordViewSet,
    GroupLessonEnrollmentViewSet,
    StudentCalendarView,
    MarkAbsenceView,
)

app_name = 'lessons'

router = DefaultRouter()
router.register('time-slots', TimeSlotViewSet, basename='time-slot')
router.register('schedules', LessonScheduleViewSet, basename='schedule')
router.register('attendances', AttendanceViewSet, basename='attendance')
router.register('makeups', MakeupLessonViewSet, basename='makeup')
router.register('records', LessonRecordViewSet, basename='record')
router.register('enrollments', GroupLessonEnrollmentViewSet, basename='enrollment')

urlpatterns = [
    # 生徒カレンダー（開講時間割 + 年間カレンダー）
    path('student-calendar/', StudentCalendarView.as_view(), name='student-calendar'),
    # 欠席登録（カレンダーから）
    path('mark-absence/', MarkAbsenceView.as_view(), name='mark-absence'),
    path('', include(router.urls)),
]

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
    AbsenceTicketListView,
    UseAbsenceTicketView,
    TransferAvailableClassesView,
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
    # 欠席チケット（振替チケット）一覧
    path('absence-tickets/', AbsenceTicketListView.as_view(), name='absence-tickets'),
    # 振替予約（欠席チケット使用）
    path('use-absence-ticket/', UseAbsenceTicketView.as_view(), name='use-absence-ticket'),
    # 振替可能クラス取得
    path('transfer-available-classes/', TransferAvailableClassesView.as_view(), name='transfer-available-classes'),
    path('', include(router.urls)),
]

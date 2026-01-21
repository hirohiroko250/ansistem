"""
HR URLs - 勤怠管理URL
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HRAttendanceViewSet,
    StaffAvailabilityViewSet,
    StaffAvailabilityBookingViewSet,
    StaffWorkScheduleViewSet,
    StaffProfileViewSet,
    StaffReviewViewSet,
)

app_name = 'hr'

router = DefaultRouter()
router.register('attendances', HRAttendanceViewSet, basename='attendance')
router.register('availabilities', StaffAvailabilityViewSet, basename='availability')
router.register('availability-bookings', StaffAvailabilityBookingViewSet, basename='availability-booking')
router.register('work-schedules', StaffWorkScheduleViewSet, basename='work-schedule')
router.register('profiles', StaffProfileViewSet, basename='profile')
router.register('reviews', StaffReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),
]

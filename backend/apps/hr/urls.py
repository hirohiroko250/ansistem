"""
HR URLs - 勤怠管理URL
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HRAttendanceViewSet

app_name = 'hr'

router = DefaultRouter()
router.register('attendances', HRAttendanceViewSet, basename='attendance')

urlpatterns = [
    path('', include(router.urls)),
]

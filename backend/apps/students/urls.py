"""
Students URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, GuardianViewSet, StudentSchoolViewSet, StudentGuardianViewSet

app_name = 'students'

router = DefaultRouter()
# /api/v1/students/ で直接アクセスできるように空文字列で登録
router.register('', StudentViewSet, basename='student')
router.register('guardians', GuardianViewSet, basename='guardian')
router.register('student-schools', StudentSchoolViewSet, basename='student-school')
router.register('student-guardians', StudentGuardianViewSet, basename='student-guardian')

urlpatterns = [
    path('', include(router.urls)),
]

"""
Students URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudentViewSet, GuardianViewSet, StudentSchoolViewSet, StudentGuardianViewSet,
    SuspensionRequestViewSet, WithdrawalRequestViewSet,
    BankAccountViewSet, BankAccountChangeRequestViewSet
)

app_name = 'students'

router = DefaultRouter()
# 具体的なパスを先に登録（空文字列より先にマッチさせる）
router.register('guardians', GuardianViewSet, basename='guardian')
router.register('student-schools', StudentSchoolViewSet, basename='student-school')
router.register('student-guardians', StudentGuardianViewSet, basename='student-guardian')
router.register('suspension-requests', SuspensionRequestViewSet, basename='suspension-request')
router.register('withdrawal-requests', WithdrawalRequestViewSet, basename='withdrawal-request')
router.register('bank-accounts', BankAccountViewSet, basename='bank-account')
router.register('bank-account-requests', BankAccountChangeRequestViewSet, basename='bank-account-request')
# /api/v1/students/ で直接アクセスできるように空文字列で登録（最後に登録）
router.register('', StudentViewSet, basename='student')

urlpatterns = [
    path('', include(router.urls)),
]

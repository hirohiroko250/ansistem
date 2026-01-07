"""
Authentication URLs
"""
from django.urls import path
from .views import (
    LoginView,
    RegisterView,
    EmployeeRegisterView,
    LogoutView,
    TokenRefreshAPIView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PasswordChangeView,
    CheckEmailView,
    CheckPhoneView,
    MeView,
    ImpersonateGuardianView,
)

app_name = 'authentication'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('register/employee/', EmployeeRegisterView.as_view(), name='register_employee'),
    path('check-email/', CheckEmailView.as_view(), name='check_email'),
    path('check-phone/', CheckPhoneView.as_view(), name='check_phone'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshAPIView.as_view(), name='token_refresh'),
    path('refresh/', TokenRefreshAPIView.as_view(), name='refresh'),  # フロントエンド互換用
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-change/', PasswordChangeView.as_view(), name='password_change'),
    path('me/', MeView.as_view(), name='me'),
    path('impersonate-guardian/', ImpersonateGuardianView.as_view(), name='impersonate_guardian'),
]

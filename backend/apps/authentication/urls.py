"""
Authentication URLs
"""
from django.urls import path
from .views import (
    LoginView,
    RegisterView,
    LogoutView,
    TokenRefreshAPIView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    CheckEmailView,
    CheckPhoneView,
    MeView,
)

app_name = 'authentication'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('check-email/', CheckEmailView.as_view(), name='check_email'),
    path('check-phone/', CheckPhoneView.as_view(), name='check_phone'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshAPIView.as_view(), name='token_refresh'),
    path('refresh/', TokenRefreshAPIView.as_view(), name='refresh'),  # フロントエンド互換用
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('me/', MeView.as_view(), name='me'),
]

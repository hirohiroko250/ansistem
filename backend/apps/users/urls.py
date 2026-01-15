"""
Users URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, ProfileView, ChildAccountViewSet, SwitchAccountView,
    MyQRCodeView, RegenerateQRCodeView
)

app_name = 'users'

router = DefaultRouter()
router.register('', UserViewSet, basename='user')

# 子アカウント管理用ルーター
child_router = DefaultRouter()
child_router.register('', ChildAccountViewSet, basename='child-account')

urlpatterns = [
    path('profile/', ProfileView.as_view(), name='profile'),
    path('my-qr/', MyQRCodeView.as_view(), name='my-qr'),  # 自分のQRコード取得
    path('regenerate-qr/', RegenerateQRCodeView.as_view(), name='regenerate-qr'),  # QRコード再発行
    path('children/', include(child_router.urls)),  # 子アカウント管理
    path('switch-account/', SwitchAccountView.as_view(), name='switch-account'),  # アカウント切り替え
    path('', include(router.urls)),
]

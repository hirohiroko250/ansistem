"""
Users URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ProfileView, ChildAccountViewSet, SwitchAccountView

app_name = 'users'

router = DefaultRouter()
router.register('', UserViewSet, basename='user')

# 子アカウント管理用ルーター
child_router = DefaultRouter()
child_router.register('', ChildAccountViewSet, basename='child-account')

urlpatterns = [
    path('profile/', ProfileView.as_view(), name='profile'),
    path('children/', include(child_router.urls)),  # 子アカウント管理
    path('switch-account/', SwitchAccountView.as_view(), name='switch-account'),  # アカウント切り替え
    path('', include(router.urls)),
]

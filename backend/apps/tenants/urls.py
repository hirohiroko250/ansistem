from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenantViewSet, PositionViewSet,
    FeatureMasterViewSet, PositionPermissionViewSet,
)

app_name = 'tenants'

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'positions', PositionViewSet, basename='position')
router.register(r'features', FeatureMasterViewSet, basename='feature')
router.register(r'permissions', PositionPermissionViewSet, basename='permission')

urlpatterns = [
    path('', include(router.urls)),
]

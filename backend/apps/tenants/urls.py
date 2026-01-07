from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenantViewSet, PositionViewSet,
    FeatureMasterViewSet, PositionPermissionViewSet,
    EmployeeViewSet, EmployeeGroupViewSet,
    DepartmentListView, RoleListView, PublicPositionListView,
)

app_name = 'tenants'

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'positions', PositionViewSet, basename='position')
router.register(r'features', FeatureMasterViewSet, basename='feature')
router.register(r'permissions', PositionPermissionViewSet, basename='permission')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'employee-groups', EmployeeGroupViewSet, basename='employee-group')

urlpatterns = [
    # 公開APIを先に定義（ルーターより優先させる）
    path('positions/public/', PublicPositionListView.as_view(), name='position-list-public'),
    path('departments/', DepartmentListView.as_view(), name='department-list'),
    path('roles/', RoleListView.as_view(), name='role-list'),
    # ルーターURL
    path('', include(router.urls)),
]

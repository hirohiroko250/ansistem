"""
Contracts URLs - シンプル版
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, DiscountViewSet, CourseViewSet,
    PackViewSet,
    SeminarViewSet, CertificationViewSet,
    ContractViewSet, StudentItemViewSet, StudentDiscountViewSet,
    SeminarEnrollmentViewSet, CertificationEnrollmentViewSet,
    OperationHistoryViewSet,
    # 公開API
    PublicBrandListView, PublicCourseListView, PublicCourseDetailView,
    PublicPackListView, PublicPackDetailView,
)

app_name = 'contracts'

router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')
router.register('discounts', DiscountViewSet, basename='discount')
router.register('courses', CourseViewSet, basename='course')
router.register('packs', PackViewSet, basename='pack')
router.register('seminars', SeminarViewSet, basename='seminar')
router.register('certifications', CertificationViewSet, basename='certification')
router.register('student-items', StudentItemViewSet, basename='student-item')
router.register('student-discounts', StudentDiscountViewSet, basename='student-discount')
router.register('seminar-enrollments', SeminarEnrollmentViewSet, basename='seminar-enrollment')
router.register('certification-enrollments', CertificationEnrollmentViewSet, basename='certification-enrollment')
router.register('operation-history', OperationHistoryViewSet, basename='operation-history')
# ContractViewSetは最後に登録（空のベースパスなので他のルートより後に）
router.register('', ContractViewSet, basename='contract')

urlpatterns = [
    # 公開API（認証不要）
    path('public/brands/', PublicBrandListView.as_view(), name='public-brand-list'),
    path('public/courses/', PublicCourseListView.as_view(), name='public-course-list'),
    path('public/courses/<uuid:pk>/', PublicCourseDetailView.as_view(), name='public-course-detail'),
    path('public/packs/', PublicPackListView.as_view(), name='public-pack-list'),
    path('public/packs/<uuid:pk>/', PublicPackDetailView.as_view(), name='public-pack-detail'),

    # 認証必要API
    path('', include(router.urls)),
]

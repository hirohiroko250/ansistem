"""
Course Views - コース・パック管理
CourseViewSet, PackViewSet
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from ..models import Course, Pack
from ..serializers import (
    CourseListSerializer, CourseDetailSerializer,
    PackListSerializer, PackDetailSerializer,
)


class CourseViewSet(CSVMixin, viewsets.ModelViewSet):
    """コースビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'courses'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Course.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('brand', 'school', 'grade').prefetch_related('course_items__product')

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()


class PackViewSet(CSVMixin, viewsets.ModelViewSet):
    """パックビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'packs'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Pack.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('brand').prefetch_related('pack_courses__course')

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return PackListSerializer
        return PackDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

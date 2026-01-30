"""
Event Views - 講習・検定管理
SeminarViewSet, CertificationViewSet, SeminarEnrollmentViewSet, CertificationEnrollmentViewSet
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from ..models import Seminar, Certification, SeminarEnrollment, CertificationEnrollment
from ..serializers import (
    SeminarListSerializer, SeminarDetailSerializer,
    CertificationListSerializer, CertificationDetailSerializer,
    SeminarEnrollmentListSerializer, SeminarEnrollmentDetailSerializer,
    CertificationEnrollmentListSerializer, CertificationEnrollmentDetailSerializer,
)


class SeminarViewSet(CSVMixin, viewsets.ModelViewSet):
    """講習ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'seminars'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Seminar.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('brand', 'grade')

        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(year=year)

        seminar_type = self.request.query_params.get('seminar_type')
        if seminar_type:
            queryset = queryset.filter(seminar_type=seminar_type)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return SeminarListSerializer
        return SeminarDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()


class CertificationViewSet(CSVMixin, viewsets.ModelViewSet):
    """検定ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'certifications'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Certification.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('brand')

        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(year=year)

        certification_type = self.request.query_params.get('certification_type')
        if certification_type:
            queryset = queryset.filter(certification_type=certification_type)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # brand_ids フィルター（カンマ区切り複数ブランド対応）
        brand_ids = self.request.query_params.get('brand_ids')
        if brand_ids:
            brand_id_list = [bid.strip() for bid in brand_ids.split(',') if bid.strip()]
            if brand_id_list:
                queryset = queryset.filter(brand_id__in=brand_id_list)
        else:
            # brand_id フィルター（単一ブランド）
            brand_id = self.request.query_params.get('brand_id')
            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return CertificationListSerializer
        return CertificationDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()


class SeminarEnrollmentViewSet(CSVMixin, viewsets.ModelViewSet):
    """講習申込ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'seminar_enrollments'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = SeminarEnrollment.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'seminar')

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        seminar_id = self.request.query_params.get('seminar_id')
        if seminar_id:
            queryset = queryset.filter(seminar_id=seminar_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return SeminarEnrollmentListSerializer
        return SeminarEnrollmentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """申込確定"""
        enrollment = self.get_object()
        enrollment.status = SeminarEnrollment.Status.CONFIRMED
        enrollment.save()
        return Response(SeminarEnrollmentDetailSerializer(enrollment).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """申込キャンセル"""
        enrollment = self.get_object()
        enrollment.status = SeminarEnrollment.Status.CANCELLED
        enrollment.save()
        return Response(SeminarEnrollmentDetailSerializer(enrollment).data)


class CertificationEnrollmentViewSet(CSVMixin, viewsets.ModelViewSet):
    """検定申込ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'certification_enrollments'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = CertificationEnrollment.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'certification')

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        certification_id = self.request.query_params.get('certification_id')
        if certification_id:
            queryset = queryset.filter(certification_id=certification_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return CertificationEnrollmentListSerializer
        return CertificationEnrollmentDetailSerializer

    def perform_create(self, serializer):
        # 検定の購入締切チェック
        certification = serializer.validated_data.get('certification')
        if certification:
            can_purchase, error_message = certification.can_purchase()
            if not can_purchase:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'certification': error_message})

        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """申込確定"""
        enrollment = self.get_object()
        enrollment.status = CertificationEnrollment.Status.CONFIRMED
        enrollment.save()
        return Response(CertificationEnrollmentDetailSerializer(enrollment).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """申込キャンセル"""
        enrollment = self.get_object()
        enrollment.status = CertificationEnrollment.Status.CANCELLED
        enrollment.save()
        return Response(CertificationEnrollmentDetailSerializer(enrollment).data)

    @action(detail=True, methods=['post'])
    def record_result(self, request, pk=None):
        """結果記録"""
        enrollment = self.get_object()
        result = request.data.get('result')  # 'passed' or 'failed'
        score = request.data.get('score')

        if result == 'passed':
            enrollment.status = CertificationEnrollment.Status.PASSED
        elif result == 'failed':
            enrollment.status = CertificationEnrollment.Status.FAILED

        if score is not None:
            enrollment.score = score

        enrollment.save()
        return Response(CertificationEnrollmentDetailSerializer(enrollment).data)

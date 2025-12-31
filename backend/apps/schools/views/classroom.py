"""
Classroom Views - 教室関連
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from ..models import Classroom
from ..serializers import ClassroomListSerializer, ClassroomDetailSerializer


class ClassroomViewSet(CSVMixin, viewsets.ModelViewSet):
    """教室ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'classrooms'
    csv_export_fields = [
        'classroom_code', 'classroom_name', 'school.school_code', 'school.school_name',
        'capacity', 'floor', 'room_type', 'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'classroom_code': '教室コード',
        'classroom_name': '教室名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'capacity': '定員',
        'floor': '階数',
        'room_type': '教室種別',
        'sort_order': '表示順',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '教室コード': 'classroom_code',
        '教室名': 'classroom_name',
        '定員': 'capacity',
        '階数': 'floor',
        '教室種別': 'room_type',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['教室コード', '教室名']
    csv_unique_fields = ['classroom_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Classroom.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('school')

        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ClassroomListSerializer
        return ClassroomDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['get'])
    def export(self, request):
        """CSVエクスポート"""
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """CSVインポート"""
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        """CSVテンプレートダウンロード"""
        return self.get_csv_template(request)

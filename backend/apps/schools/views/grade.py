"""
Grade & Subject Views - 学年・教科関連
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from ..models import Grade, Subject
from ..serializers import GradeSerializer, SubjectSerializer


class GradeViewSet(CSVMixin, viewsets.ModelViewSet):
    """学年ビューセット"""
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'grades'
    csv_export_fields = [
        'id', 'grade_code', 'grade_name', 'grade_name_short', 'category',
        'school_year', 'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'id': 'ID',
        'grade_code': '学年コード',
        'grade_name': '学年名',
        'grade_name_short': '学年名略称',
        'category': 'カテゴリ',
        'school_year': '学校学年',
        'sort_order': '表示順',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        'ID': 'id',
        '学年コード': 'grade_code',
        '学年名': 'grade_name',
        '学年名略称': 'grade_name_short',
        'カテゴリ': 'category',
        '学校学年': 'school_year',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['学年コード', '学年名']
    csv_unique_fields = ['grade_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Grade.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset

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


class SubjectViewSet(CSVMixin, viewsets.ModelViewSet):
    """教科ビューセット"""
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'subjects'
    csv_export_fields = [
        'id', 'subject_code', 'subject_name', 'subject_name_short', 'category',
        'color', 'icon', 'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'id': 'ID',
        'subject_code': '教科コード',
        'subject_name': '教科名',
        'subject_name_short': '教科名略称',
        'category': 'カテゴリ',
        'color': '表示色',
        'icon': 'アイコン',
        'sort_order': '表示順',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        'ID': 'id',
        '教科コード': 'subject_code',
        '教科名': 'subject_name',
        '教科名略称': 'subject_name_short',
        'カテゴリ': 'category',
        '表示色': 'color',
        'アイコン': 'icon',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['教科コード', '教科名']
    csv_unique_fields = ['subject_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Subject.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset

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

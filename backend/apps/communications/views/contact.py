"""
Contact Views - 対応履歴管理Views
ContactLogViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.utils import timezone

from apps.core.permissions import IsTenantUser
from apps.core.csv_utils import CSVMixin
from ..models import ContactLog
from ..serializers import (
    ContactLogListSerializer, ContactLogDetailSerializer, ContactLogCreateSerializer,
    ContactLogCommentSerializer,
)


class ContactLogViewSet(CSVMixin, viewsets.ModelViewSet):
    """対応履歴ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'contact_logs'
    csv_export_fields = [
        'contact_type', 'subject', 'content',
        'student.student_no', 'student.full_name',
        'guardian.guardian_no', 'guardian.full_name',
        'school.school_code', 'school.school_name',
        'handled_by.email', 'priority', 'status',
        'follow_up_date', 'tags', 'created_at', 'tenant_id'
    ]
    csv_export_headers = {
        'contact_type': '対応種別',
        'subject': '件名',
        'content': '内容',
        'student.student_no': '生徒番号',
        'student.full_name': '生徒名',
        'guardian.guardian_no': '保護者番号',
        'guardian.full_name': '保護者名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'handled_by.email': '対応者',
        'priority': '優先度',
        'status': 'ステータス',
        'follow_up_date': 'フォローアップ日',
        'tags': 'タグ',
        'created_at': '作成日時',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '対応種別': 'contact_type',
        '件名': 'subject',
        '内容': 'content',
        '優先度': 'priority',
        'ステータス': 'status',
        'フォローアップ日': 'follow_up_date',
    }
    csv_required_fields = ['対応種別', '件名', '内容']
    csv_unique_fields = []

    def get_queryset(self):
        from apps.core.permissions import is_admin_user
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = ContactLog.objects.select_related('student', 'guardian', 'school', 'handled_by', 'resolved_by')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        # フィルター
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        contact_type = self.request.query_params.get('contact_type')
        if contact_type:
            queryset = queryset.filter(contact_type=contact_type)

        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(guardian_id=guardian_id)

        handled_by = self.request.query_params.get('handled_by')
        if handled_by:
            queryset = queryset.filter(handled_by_id=handled_by)

        # 検索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(subject__icontains=search) |
                Q(content__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ContactLogListSerializer
        elif self.action == 'create':
            return ContactLogCreateSerializer
        return ContactLogDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            handled_by=self.request.user
        )

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """解決"""
        contact_log = self.get_object()
        contact_log.status = ContactLog.Status.RESOLVED
        contact_log.resolved_at = timezone.now()
        contact_log.resolved_by = request.user
        contact_log.save()
        return Response(ContactLogDetailSerializer(contact_log).data)

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """コメント追加"""
        contact_log = self.get_object()
        serializer = ContactLogCommentSerializer(data={
            **request.data,
            'contact_log': contact_log.id
        })
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """統計"""
        queryset = self.get_queryset()
        stats = {
            'total': queryset.count(),
            'by_status': {},
            'by_priority': {},
            'by_type': {},
        }

        for status_choice in ContactLog.Status.choices:
            stats['by_status'][status_choice[0]] = queryset.filter(
                status=status_choice[0]
            ).count()

        for priority_choice in ContactLog.Priority.choices:
            stats['by_priority'][priority_choice[0]] = queryset.filter(
                priority=priority_choice[0]
            ).count()

        for type_choice in ContactLog.ContactType.choices:
            stats['by_type'][type_choice[0]] = queryset.filter(
                contact_type=type_choice[0]
            ).count()

        return Response(stats)

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

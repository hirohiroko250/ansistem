"""
Announcement Views - お知らせ管理Views
AnnouncementViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from ..models import Announcement
from ..serializers import (
    AnnouncementListSerializer, AnnouncementDetailSerializer, AnnouncementCreateSerializer,
)


class AnnouncementViewSet(CSVMixin, viewsets.ModelViewSet):
    """お知らせビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'announcements'
    csv_export_fields = [
        'title', 'content', 'target_type', 'status',
        'scheduled_at', 'sent_at', 'sent_count', 'read_count',
        'created_at', 'tenant_id'
    ]
    csv_export_headers = {
        'title': 'タイトル',
        'content': '内容',
        'target_type': '配信対象',
        'status': 'ステータス',
        'scheduled_at': '送信予定日時',
        'sent_at': '送信日時',
        'sent_count': '送信数',
        'read_count': '既読数',
        'created_at': '作成日時',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        'タイトル': 'title',
        '内容': 'content',
        '配信対象': 'target_type',
        '送信予定日時': 'scheduled_at',
    }
    csv_required_fields = ['タイトル', '内容']
    csv_unique_fields = []

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Announcement.objects.filter(
            tenant_id=tenant_id
        ).select_related('created_by')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        target_type = self.request.query_params.get('target_type')
        if target_type:
            queryset = queryset.filter(target_type=target_type)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return AnnouncementListSerializer
        elif self.action == 'create':
            return AnnouncementCreateSerializer
        return AnnouncementDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'send']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user
        )

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """お知らせ送信"""
        announcement = self.get_object()

        if announcement.status == Announcement.Status.SENT:
            return Response(
                {'error': '既に送信済みです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # TODO: 実際の送信処理（通知作成、メール送信等）

        announcement.status = Announcement.Status.SENT
        announcement.sent_at = timezone.now()
        # announcement.sent_count = ... (送信数をカウント)
        announcement.save()

        return Response(AnnouncementDetailSerializer(announcement).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """送信キャンセル"""
        announcement = self.get_object()

        if announcement.status != Announcement.Status.SCHEDULED:
            return Response(
                {'error': '予約状態のお知らせのみキャンセルできます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        announcement.status = Announcement.Status.CANCELLED
        announcement.save(update_fields=['status'])

        return Response(AnnouncementDetailSerializer(announcement).data)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """CSVエクスポート"""
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """CSVインポート"""
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def announcement_template(self, request):
        """CSVテンプレートダウンロード"""
        return self.get_csv_template(request)

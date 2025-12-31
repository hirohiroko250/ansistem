"""
Invoice ViewSet - 請求書管理API
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.billing.models import Invoice, MonthlyBillingDeadline
from apps.billing.serializers import (
    InvoiceSerializer, InvoicePreviewSerializer, InvoiceConfirmSerializer,
)
from .mixins import InvoiceExportMixin, InvoiceImportMixin, InvoiceBillingMixin

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(summary='請求書一覧'),
    retrieve=extend_schema(summary='請求書詳細'),
)
class InvoiceViewSet(
    InvoiceExportMixin,
    InvoiceImportMixin,
    InvoiceBillingMixin,
    viewsets.ModelViewSet
):
    """請求書管理API"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.core.permissions import is_admin_user

        queryset = Invoice.objects.select_related('guardian', 'confirmed_by').prefetch_related('lines')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=self.request.user.tenant_id)

        # guardian_idでフィルタ
        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(guardian_id=guardian_id)

        return queryset

    def check_deadline_editable(self, invoice):
        """請求書の請求月が編集可能かチェック"""
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        if not MonthlyBillingDeadline.is_month_editable(tenant_id, invoice.billing_year, invoice.billing_month):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                f'{invoice.billing_year}年{invoice.billing_month}月分は締め済みのため編集できません'
            )

    def update(self, request, *args, **kwargs):
        """請求書更新時に締め状態をチェック"""
        instance = self.get_object()
        self.check_deadline_editable(instance)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """請求書部分更新時に締め状態をチェック"""
        instance = self.get_object()
        self.check_deadline_editable(instance)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """請求書削除時に締め状態をチェック"""
        instance = self.get_object()
        self.check_deadline_editable(instance)
        return super().destroy(request, *args, **kwargs)

    @extend_schema(summary='請求書プレビュー', request=InvoicePreviewSerializer)
    @action(detail=False, methods=['post'])
    def preview(self, request):
        """請求書のプレビューを生成（確定前）"""
        serializer = InvoicePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # TODO: 請求書プレビュー生成ロジック
        # - 保護者に紐づく生徒のStudentItemを取得
        # - 対象月の請求金額を計算
        # - マイル割引を計算（use_milesが指定されている場合）

        return Response({
            'message': 'プレビュー生成ロジックは後で実装',
            'data': serializer.validated_data,
        })

    @extend_schema(summary='請求書確定', request=InvoiceConfirmSerializer)
    @action(detail=False, methods=['post'])
    def confirm(self, request):
        """請求書を確定（下書き→発行済）"""
        serializer = InvoiceConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invoice = get_object_or_404(
            Invoice,
            id=serializer.validated_data['invoice_id'],
            tenant_id=request.user.tenant_id
        )

        if invoice.status != Invoice.Status.DRAFT:
            return Response(
                {'error': 'この請求書は既に確定されています'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice.confirm(request.user)
        return Response(InvoiceSerializer(invoice).data)

    @extend_schema(summary='保護者の請求書一覧')
    @action(detail=False, methods=['get'], url_path='by-guardian/(?P<guardian_id>[^/.]+)')
    def by_guardian(self, request, guardian_id=None):
        """保護者IDで請求書を取得"""
        invoices = self.get_queryset().filter(guardian_id=guardian_id)
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

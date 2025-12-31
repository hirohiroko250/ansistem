"""
Refund ViewSet - 返金申請管理API
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view

from ..models import RefundRequest
from ..serializers import (
    RefundRequestSerializer, RefundRequestCreateSerializer, RefundApproveSerializer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# RefundRequest ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='返金申請一覧'),
    retrieve=extend_schema(summary='返金申請詳細'),
)
class RefundRequestViewSet(viewsets.ModelViewSet):
    """返金申請管理API"""
    serializer_class = RefundRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RefundRequest.objects.filter(
            tenant_id=self.request.user.tenant_id
        ).select_related('guardian', 'invoice', 'requested_by', 'approved_by')

    @extend_schema(summary='返金申請作成', request=RefundRequestCreateSerializer)
    @action(detail=False, methods=['post'])
    def create_request(self, request):
        """返金申請を作成"""
        serializer = RefundRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 申請番号生成
        today = timezone.now()
        prefix = f"REF-{today.strftime('%Y%m%d')}-"
        last = RefundRequest.objects.filter(
            tenant_id=request.user.tenant_id,
            request_no__startswith=prefix
        ).order_by('-request_no').first()
        if last:
            new_num = int(last.request_no.split('-')[-1]) + 1
        else:
            new_num = 1
        request_no = f"{prefix}{new_num:04d}"

        refund_request = RefundRequest.objects.create(
            tenant_id=request.user.tenant_id,
            request_no=request_no,
            guardian_id=data['guardian_id'],
            invoice_id=data.get('invoice_id'),
            refund_amount=data['refund_amount'],
            refund_method=data['refund_method'],
            reason=data['reason'],
            requested_by=request.user,
        )

        return Response(
            RefundRequestSerializer(refund_request).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(summary='返金申請承認/却下', request=RefundApproveSerializer)
    @action(detail=False, methods=['post'])
    def approve(self, request):
        """返金申請を承認または却下"""
        serializer = RefundApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        refund_request = get_object_or_404(
            RefundRequest,
            id=data['request_id'],
            tenant_id=request.user.tenant_id
        )

        if refund_request.status != RefundRequest.Status.PENDING:
            return Response(
                {'error': 'この申請は既に処理されています'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if data['approve']:
            refund_request.approve(request.user)
        else:
            refund_request.status = RefundRequest.Status.REJECTED
            refund_request.approved_by = request.user
            refund_request.approved_at = timezone.now()
            refund_request.process_notes = data.get('reject_reason', '')
            refund_request.save()

        return Response(RefundRequestSerializer(refund_request).data)

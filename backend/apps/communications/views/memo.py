"""
Memo Views - 伝言メモ・TEL登録メモ
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.core.permissions import IsTenantUser
from apps.communications.models import MessageMemo, TelMemo
from apps.communications.serializers import (
    MessageMemoSerializer,
    MessageMemoCreateSerializer,
    TelMemoSerializer,
    TelMemoCreateSerializer,
)


class MessageMemoViewSet(viewsets.ModelViewSet):
    """伝言メモ ViewSet"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = MessageMemo.objects.filter(
            deleted_at__isnull=True
        ).select_related(
            'student', 'student__guardian', 'created_by', 'completed_by'
        )

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        # ステータスフィルタ
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 優先度フィルタ
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        # 生徒IDフィルタ
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return MessageMemoCreateSerializer
        return MessageMemoSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        serializer.save(
            tenant_id=tenant_id,
            created_by=self.request.user,
        )

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """メモを完了にする"""
        memo = self.get_object()
        memo.status = MessageMemo.Status.COMPLETED
        memo.completed_by = request.user
        memo.completed_at = timezone.now()
        memo.save()
        return Response(MessageMemoSerializer(memo).data)

    @action(detail=False, methods=['get'])
    def pending_count(self, request):
        """未対応メモ数を取得"""
        count = self.get_queryset().filter(status=MessageMemo.Status.PENDING).count()
        return Response({'count': count})


class TelMemoViewSet(viewsets.ModelViewSet):
    """TEL登録メモ ViewSet"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = TelMemo.objects.filter(
            deleted_at__isnull=True
        ).select_related(
            'student', 'student__guardian', 'created_by'
        )

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        # 発信/着信フィルタ
        call_direction = self.request.query_params.get('call_direction')
        if call_direction:
            queryset = queryset.filter(call_direction=call_direction)

        # 通話結果フィルタ
        call_result = self.request.query_params.get('call_result')
        if call_result:
            queryset = queryset.filter(call_result=call_result)

        # 生徒IDフィルタ
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return TelMemoCreateSerializer
        return TelMemoSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        serializer.save(
            tenant_id=tenant_id,
            created_by=self.request.user,
        )

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['get'])
    def count(self, request):
        """TELメモ数を取得"""
        count = self.get_queryset().count()
        return Response({'count': count})

"""
Message Views - メッセージ管理Views
MessageViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone

from apps.core.permissions import IsTenantUser
from ..models import Channel, Message, ChatLog
from ..serializers import MessageSerializer, MessageCreateSerializer


class MessageViewSet(viewsets.ModelViewSet):
    """メッセージビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_tenant_id(self):
        """tenant_idを取得（request.tenant_idまたはユーザーの保護者プロファイルから）"""
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            tenant_id = self.request.user.guardian_profile.tenant_id
        return tenant_id

    def get_queryset(self):
        from apps.core.permissions import is_admin_user
        tenant_id = self.get_tenant_id()
        queryset = Message.objects.filter(
            is_deleted=False
        ).select_related('channel', 'sender', 'sender_guardian', 'reply_to', 'channel__guardian', 'channel__school')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        # channel_id でフィルタ
        channel_id = self.request.query_params.get('channel_id')
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)

        # guardian_id でフィルタ（チャンネルの保護者または送信者保護者）
        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(
                Q(channel__guardian_id=guardian_id) | Q(sender_guardian_id=guardian_id)
            )

        # 作成日時の昇順（古いメッセージが先）
        return queryset.order_by('created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        # 保護者の場合は sender_guardian も設定
        sender_guardian = None
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            sender_guardian = self.request.user.guardian_profile

        tenant_id = self.get_tenant_id()

        # tenant_idがない場合（管理者等）、チャンネルから取得
        if not tenant_id:
            channel_id = serializer.validated_data.get('channel')
            if channel_id:
                channel = Channel.objects.filter(id=channel_id.id if hasattr(channel_id, 'id') else channel_id).first()
                if channel:
                    tenant_id = channel.tenant_id

        serializer.save(
            tenant_id=tenant_id,
            sender=self.request.user,
            sender_guardian=sender_guardian
        )

    def create(self, request, *args, **kwargs):
        """メッセージ作成（レスポンスは詳細シリアライザーを使用）"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[MessageViewSet.create] Received data: {request.data}")

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"[MessageViewSet.create] Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)

        # チャットログを作成
        try:
            tenant_id = self.get_tenant_id()
            chat_log = ChatLog.create_from_message(serializer.instance, tenant_id)
            logger.info(f"[MessageViewSet.create] ChatLog created: {chat_log.id}")
        except Exception as e:
            logger.error(f"[MessageViewSet.create] Failed to create ChatLog: {e}")

        # レスポンスは詳細シリアライザーを使用
        response_serializer = MessageSerializer(serializer.instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def edit(self, request, pk=None):
        """メッセージ編集"""
        message = self.get_object()
        if message.sender != request.user:
            return Response(
                {'error': '自分のメッセージのみ編集できます'},
                status=status.HTTP_403_FORBIDDEN
            )

        message.content = request.data.get('content', message.content)
        message.is_edited = True
        message.edited_at = timezone.now()
        message.save()
        return Response(MessageSerializer(message).data)

    @action(detail=True, methods=['post'])
    def delete_message(self, request, pk=None):
        """メッセージ削除（論理削除）"""
        message = self.get_object()
        if message.sender != request.user:
            return Response(
                {'error': '自分のメッセージのみ削除できます'},
                status=status.HTTP_403_FORBIDDEN
            )

        message.is_deleted = True
        message.save(update_fields=['is_deleted'])
        return Response({'status': 'deleted'})

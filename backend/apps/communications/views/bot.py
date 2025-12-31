"""
Bot Views - ボット関連Views
BotConfigViewSet, BotFAQViewSet, BotChatViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from ..models import Channel, BotConfig, BotFAQ, BotConversation
from ..serializers import (
    BotConfigSerializer, BotFAQSerializer, BotChatSerializer,
)
from ..services import BotService


class BotConfigViewSet(viewsets.ModelViewSet):
    """ボット設定ビューセット"""
    serializer_class = BotConfigSerializer
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return BotConfig.objects.filter(tenant_id=tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def active(self, request):
        """アクティブなボット設定を取得（保護者向け）"""
        tenant_id = getattr(request, 'tenant_id', None)
        bot = BotConfig.objects.filter(
            tenant_id=tenant_id,
            is_active=True
        ).first()

        if bot:
            return Response({
                'id': str(bot.id),
                'name': bot.name,
                'welcomeMessage': bot.welcome_message,
                'botType': bot.bot_type,
                'aiEnabled': bot.ai_enabled,
            })
        else:
            # デフォルトのボット情報を返す
            return Response({
                'id': 'ai-assistant',
                'name': 'AIアシスタント',
                'welcomeMessage': 'こんにちは！何かお手伝いできることはありますか？',
                'botType': 'GENERAL',
                'aiEnabled': False,
            })


class BotFAQViewSet(viewsets.ModelViewSet):
    """ボットFAQビューセット"""
    serializer_class = BotFAQSerializer
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = BotFAQ.objects.filter(tenant_id=tenant_id)

        bot_config_id = self.request.query_params.get('bot_config_id')
        if bot_config_id:
            queryset = queryset.filter(bot_config_id=bot_config_id)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class BotChatViewSet(viewsets.ViewSet):
    """ボットチャットビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    @action(detail=False, methods=['post'])
    def chat(self, request):
        """ボットとチャット"""
        serializer = BotChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.validated_data['message']
        channel_id = serializer.validated_data.get('channel_id')

        # tenant_idを取得（request.tenant_idまたは保護者プロファイルから）
        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id and hasattr(request.user, 'guardian_profile') and request.user.guardian_profile:
            tenant_id = request.user.guardian_profile.tenant_id

        # ボットサービスで応答を生成
        bot_service = BotService(tenant_id=tenant_id)
        response = bot_service.get_response(
            message=message,
            channel_id=channel_id,
            user=request.user
        )

        return Response(response)

    @action(detail=False, methods=['post'])
    def escalate(self, request):
        """スタッフに転送"""
        channel_id = request.data.get('channel_id')
        if not channel_id:
            return Response(
                {'error': 'channel_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # チャンネルタイプを変更
        try:
            channel = Channel.objects.get(
                id=channel_id,
                tenant_id=request.tenant_id
            )
            channel.channel_type = Channel.ChannelType.SUPPORT
            channel.save(update_fields=['channel_type'])

            # 通知を作成（管理者向け）
            # TODO: 適切なスタッフに通知

            return Response({
                'status': 'escalated',
                'message': 'スタッフにお繋ぎします。しばらくお待ちください。'
            })
        except Channel.DoesNotExist:
            return Response(
                {'error': 'Channel not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def feedback(self, request):
        """フィードバック"""
        conversation_id = request.data.get('conversation_id')
        was_helpful = request.data.get('was_helpful')

        if not conversation_id:
            return Response(
                {'error': 'conversation_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            conversation = BotConversation.objects.get(
                id=conversation_id,
                tenant_id=request.tenant_id
            )
            conversation.was_helpful = was_helpful
            conversation.save(update_fields=['was_helpful'])
            return Response({'status': 'ok'})
        except BotConversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

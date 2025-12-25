"""
Communications Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Count
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from .models import (
    Channel, ChannelMember, Message, MessageRead,
    ContactLog, ContactLogComment, Notification,
    BotConfig, BotFAQ, BotConversation,
    Announcement, AnnouncementRead,
    FeedPost, FeedMedia, FeedLike, FeedComment, FeedCommentLike, FeedBookmark,
    ChatLog
)
from .serializers import (
    ChannelListSerializer, ChannelDetailSerializer, ChannelCreateSerializer,
    ChannelMemberSerializer, MessageSerializer, MessageCreateSerializer,
    ContactLogListSerializer, ContactLogDetailSerializer, ContactLogCreateSerializer,
    ContactLogCommentSerializer, NotificationSerializer,
    BotConfigSerializer, BotFAQSerializer, BotConversationSerializer, BotChatSerializer,
    AnnouncementListSerializer, AnnouncementDetailSerializer, AnnouncementCreateSerializer,
    FeedPostListSerializer, FeedPostDetailSerializer, FeedPostCreateSerializer,
    FeedMediaSerializer, FeedCommentSerializer, FeedCommentCreateSerializer,
    FeedLikeSerializer, FeedBookmarkSerializer,
    ChatLogSerializer, ChatLogListSerializer
)
from .services import BotService


class ChannelViewSet(viewsets.ModelViewSet):
    """チャンネルビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        from apps.core.permissions import is_admin_user

        # tenant_idを取得（request.tenant_idまたはユーザーの保護者プロファイルから）
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            tenant_id = self.request.user.guardian_profile.tenant_id

        # 管理者は全チャンネルを閲覧可能
        if is_admin_user(self.request.user):
            queryset = Channel.objects.all().select_related('student', 'guardian', 'school')
        else:
            queryset = Channel.objects.filter(
                tenant_id=tenant_id
            ).select_related('student', 'guardian', 'school')
            # 一般ユーザーは自分が参加しているチャンネルのみ
            queryset = queryset.filter(members__user=self.request.user)

        channel_type = self.request.query_params.get('channel_type')
        if channel_type:
            queryset = queryset.filter(channel_type=channel_type)

        is_archived = self.request.query_params.get('is_archived')
        include_archived = self.request.query_params.get('include_archived')
        if is_archived is not None:
            queryset = queryset.filter(is_archived=is_archived.lower() == 'true')
        elif include_archived and include_archived.lower() == 'true':
            # include_archived=true の場合は全てのチャンネルを返す（フィルタしない）
            pass
        else:
            queryset = queryset.filter(is_archived=False)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return ChannelListSerializer
        elif self.action == 'create':
            return ChannelCreateSerializer
        return ChannelDetailSerializer

    def perform_create(self, serializer):
        # tenant_idを取得（request.tenant_idまたはユーザーの保護者プロファイルから）
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            tenant_id = self.request.user.guardian_profile.tenant_id
        serializer.save(tenant_id=tenant_id)

    def create(self, request, *args, **kwargs):
        """チャンネル作成（レスポンスは詳細シリアライザーを使用してidを返す）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # レスポンスは詳細シリアライザーを使用してidを確実に返す
        response_serializer = ChannelDetailSerializer(serializer.instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """チャンネルのメッセージ一覧"""
        channel = self.get_object()
        messages = channel.messages.filter(is_deleted=False).select_related(
            'sender', 'sender_guardian', 'reply_to'
        )

        # ページネーション
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """メッセージ送信"""
        channel = self.get_object()
        serializer = MessageCreateSerializer(data={
            **request.data,
            'channel': channel.id
        })
        serializer.is_valid(raise_exception=True)
        message = serializer.save(
            tenant_id=request.tenant_id,
            sender=request.user
        )

        # チャンネル更新日時を更新
        channel.updated_at = timezone.now()
        channel.save(update_fields=['updated_at'])

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """既読にする"""
        channel = self.get_object()
        member = channel.members.filter(user=request.user).first()
        if member:
            member.last_read_at = timezone.now()
            member.save(update_fields=['last_read_at'])
        return Response({'status': 'ok'})

    @action(detail=True, methods=['get', 'post'])
    def members(self, request, pk=None):
        """メンバー管理"""
        channel = self.get_object()

        if request.method == 'GET':
            members = channel.members.select_related('user', 'guardian').all()
            serializer = ChannelMemberSerializer(members, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = ChannelMemberSerializer(data={
                **request.data,
                'channel': channel.id
            })
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """アーカイブ"""
        channel = self.get_object()
        channel.is_archived = True
        channel.save(update_fields=['is_archived'])
        return Response(ChannelDetailSerializer(channel).data)

    @action(detail=False, methods=['post'], url_path='create-dm')
    def create_dm(self, request):
        """社員間DM（1対1チャット）を作成または取得"""
        target_user_id = request.data.get('target_user_id')
        if not target_user_id:
            return Response(
                {'error': 'target_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id:
            tenant_id = request.user.tenant_id

        # 既存のDMチャンネルを探す
        existing_channel = Channel.objects.filter(
            tenant_id=tenant_id,
            channel_type=Channel.ChannelType.INTERNAL,
            is_archived=False,
            members__user=request.user
        ).filter(
            members__user=target_user
        ).annotate(
            member_count=Count('members')
        ).filter(member_count=2).first()

        if existing_channel:
            return Response(ChannelDetailSerializer(existing_channel).data)

        # 新規DMチャンネル作成
        channel = Channel.objects.create(
            tenant_id=tenant_id,
            channel_type=Channel.ChannelType.INTERNAL,
            name=f"{request.user.full_name or request.user.email} & {target_user.full_name or target_user.email}",
            description="ダイレクトメッセージ"
        )

        # メンバー追加
        ChannelMember.objects.create(
            channel=channel,
            user=request.user,
            role=ChannelMember.Role.MEMBER
        )
        ChannelMember.objects.create(
            channel=channel,
            user=target_user,
            role=ChannelMember.Role.MEMBER
        )

        return Response(ChannelDetailSerializer(channel).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='create-group')
    def create_group(self, request):
        """グループチャットを作成"""
        name = request.data.get('name')
        member_ids = request.data.get('member_ids', [])

        if not name:
            return Response(
                {'error': 'name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id:
            tenant_id = request.user.tenant_id

        # グループチャンネル作成
        channel = Channel.objects.create(
            tenant_id=tenant_id,
            channel_type=Channel.ChannelType.INTERNAL,
            name=name,
            description=request.data.get('description', '')
        )

        # 作成者を管理者として追加
        ChannelMember.objects.create(
            channel=channel,
            user=request.user,
            role=ChannelMember.Role.ADMIN
        )

        # 他のメンバーを追加
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for member_id in member_ids:
            if str(member_id) != str(request.user.id):
                try:
                    user = User.objects.get(id=member_id)
                    ChannelMember.objects.create(
                        channel=channel,
                        user=user,
                        role=ChannelMember.Role.MEMBER
                    )
                except User.DoesNotExist:
                    pass

        return Response(ChannelDetailSerializer(channel).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my-channels')
    def my_channels(self, request):
        """自分が参加しているチャンネル一覧"""
        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id:
            tenant_id = request.user.tenant_id

        channels = Channel.objects.filter(
            tenant_id=tenant_id,
            is_archived=False,
            members__user=request.user
        ).select_related('school').prefetch_related('members__user').distinct()

        channel_type = request.query_params.get('channel_type')
        if channel_type:
            channels = channels.filter(channel_type=channel_type)

        channels = channels.order_by('-updated_at')

        page = self.paginate_queryset(channels)
        if page is not None:
            serializer = ChannelListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ChannelListSerializer(channels, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='get-or-create-for-guardian')
    def get_or_create_for_guardian(self, request):
        """保護者用チャンネルを取得または作成"""
        from apps.students.models import Guardian
        from apps.core.permissions import is_admin_user

        guardian_id = request.data.get('guardian_id')
        if not guardian_id:
            return Response(
                {'error': 'guardian_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 保護者を取得（管理者は全ての保護者にアクセス可能）
        try:
            if is_admin_user(request.user):
                guardian = Guardian.objects.get(id=guardian_id)
            else:
                tenant_id = getattr(request, 'tenant_id', None)
                if not tenant_id:
                    return Response(
                        {'error': 'tenant_id is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                guardian = Guardian.objects.get(id=guardian_id, tenant_id=tenant_id)
        except Guardian.DoesNotExist:
            return Response(
                {'error': 'Guardian not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 保護者のtenant_idを使用
        tenant_id = guardian.tenant_id

        # 既存のチャンネルを探す
        channel = Channel.objects.filter(
            tenant_id=tenant_id,
            guardian=guardian,
            channel_type=Channel.ChannelType.EXTERNAL,
            is_archived=False
        ).first()

        if not channel:
            # 新規チャンネル作成
            channel = Channel.objects.create(
                tenant_id=tenant_id,
                channel_type=Channel.ChannelType.EXTERNAL,
                name=f"{guardian.full_name}",
                guardian=guardian
            )

            # 現在のユーザーをメンバーとして追加
            ChannelMember.objects.create(
                channel=channel,
                user=request.user,
                role=ChannelMember.Role.ADMIN
            )

            # 保護者にユーザーアカウントがあれば追加
            if guardian.user:
                ChannelMember.objects.get_or_create(
                    channel=channel,
                    user=guardian.user,
                    defaults={'role': ChannelMember.Role.MEMBER}
                )

        else:
            # 既存チャンネルにユーザーをメンバーとして追加（まだの場合）
            ChannelMember.objects.get_or_create(
                channel=channel,
                user=request.user,
                defaults={'role': ChannelMember.Role.ADMIN}
            )

        return Response(ChannelDetailSerializer(channel).data)


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


class NotificationViewSet(viewsets.ModelViewSet):
    """通知ビューセット"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return Notification.objects.filter(
            tenant_id=tenant_id,
            user=self.request.user
        )

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """既読にする"""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """全て既読にする"""
        self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """未読数"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})


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


class FeedPostViewSet(viewsets.ModelViewSet):
    """フィード投稿ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = FeedPost.objects.filter(
            tenant_id=tenant_id,
            is_deleted=False,
            is_published=True
        ).select_related('author', 'school').prefetch_related('media', 'target_schools', 'target_grades')

        # 公開範囲フィルター
        visibility = self.request.query_params.get('visibility')
        if visibility:
            queryset = queryset.filter(visibility=visibility)

        # 校舎フィルター
        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(
                Q(school_id=school_id) |
                Q(target_schools__id=school_id) |
                Q(visibility=FeedPost.Visibility.PUBLIC)
            ).distinct()

        # ハッシュタグフィルター
        hashtag = self.request.query_params.get('hashtag')
        if hashtag:
            queryset = queryset.filter(hashtags__contains=[hashtag])

        # 投稿者フィルター
        author_id = self.request.query_params.get('author_id')
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        # 固定投稿を先頭に
        return queryset.order_by('-is_pinned', '-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return FeedPostListSerializer
        elif self.action == 'create':
            return FeedPostCreateSerializer
        return FeedPostDetailSerializer

    def get_permissions(self):
        # 作成・更新・削除は管理者のみ
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'pin', 'unpin']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        from django.utils import timezone as tz
        serializer.save(
            tenant_id=self.request.tenant_id,
            author=self.request.user,
            published_at=tz.now() if serializer.validated_data.get('is_published', True) else None
        )

    def retrieve(self, request, *args, **kwargs):
        """詳細取得時に閲覧数をインクリメント"""
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """論理削除"""
        instance = self.get_object()
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['is_deleted', 'deleted_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """いいね"""
        post = self.get_object()
        if not post.allow_likes:
            return Response(
                {'error': 'この投稿にはいいねできません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        like, created = FeedLike.objects.get_or_create(
            post=post,
            user=request.user
        )

        if created:
            post.like_count += 1
            post.save(update_fields=['like_count'])
            return Response({'status': 'liked', 'like_count': post.like_count})
        else:
            return Response({'status': 'already_liked', 'like_count': post.like_count})

    @action(detail=True, methods=['post'])
    def unlike(self, request, pk=None):
        """いいね解除"""
        post = self.get_object()
        deleted, _ = FeedLike.objects.filter(
            post=post,
            user=request.user
        ).delete()

        if deleted:
            post.like_count = max(0, post.like_count - 1)
            post.save(update_fields=['like_count'])

        return Response({'status': 'unliked', 'like_count': post.like_count})

    @action(detail=True, methods=['get'])
    def likes(self, request, pk=None):
        """いいね一覧"""
        post = self.get_object()
        likes = post.likes.select_related('user', 'guardian').all()
        page = self.paginate_queryset(likes)
        if page is not None:
            serializer = FeedLikeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = FeedLikeSerializer(likes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def bookmark(self, request, pk=None):
        """ブックマーク"""
        post = self.get_object()
        bookmark, created = FeedBookmark.objects.get_or_create(
            post=post,
            user=request.user
        )

        if created:
            return Response({'status': 'bookmarked'})
        else:
            return Response({'status': 'already_bookmarked'})

    @action(detail=True, methods=['post'])
    def unbookmark(self, request, pk=None):
        """ブックマーク解除"""
        post = self.get_object()
        FeedBookmark.objects.filter(
            post=post,
            user=request.user
        ).delete()
        return Response({'status': 'unbookmarked'})

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """コメント一覧・追加"""
        post = self.get_object()

        if request.method == 'GET':
            comments = post.comments.filter(
                is_deleted=False,
                parent__isnull=True  # トップレベルのみ
            ).select_related('user', 'guardian')
            page = self.paginate_queryset(comments)
            if page is not None:
                serializer = FeedCommentSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            serializer = FeedCommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)

        elif request.method == 'POST':
            if not post.allow_comments:
                return Response(
                    {'error': 'この投稿にはコメントできません'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = FeedCommentCreateSerializer(data={
                **request.data,
                'post': post.id
            })
            serializer.is_valid(raise_exception=True)
            comment = serializer.save(user=request.user)

            # コメント数更新
            post.comment_count += 1
            post.save(update_fields=['comment_count'])

            return Response(
                FeedCommentSerializer(comment, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """固定表示"""
        post = self.get_object()
        post.is_pinned = True
        post.pinned_at = timezone.now()
        post.save(update_fields=['is_pinned', 'pinned_at'])
        return Response(FeedPostDetailSerializer(post, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def unpin(self, request, pk=None):
        """固定表示解除"""
        post = self.get_object()
        post.is_pinned = False
        post.pinned_at = None
        post.save(update_fields=['is_pinned', 'pinned_at'])
        return Response(FeedPostDetailSerializer(post, context={'request': request}).data)


class FeedCommentViewSet(viewsets.ModelViewSet):
    """フィードコメントビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = FeedCommentSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return FeedComment.objects.filter(
            post__tenant_id=tenant_id,
            is_deleted=False
        ).select_related('user', 'guardian', 'parent')

    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """返信一覧"""
        comment = self.get_object()
        replies = comment.replies.filter(is_deleted=False).select_related('user', 'guardian')
        serializer = FeedCommentSerializer(replies, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """コメントいいね"""
        comment = self.get_object()
        like, created = FeedCommentLike.objects.get_or_create(
            comment=comment,
            user=request.user
        )

        if created:
            comment.like_count += 1
            comment.save(update_fields=['like_count'])
            return Response({'status': 'liked', 'like_count': comment.like_count})
        return Response({'status': 'already_liked', 'like_count': comment.like_count})

    @action(detail=True, methods=['post'])
    def unlike(self, request, pk=None):
        """コメントいいね解除"""
        comment = self.get_object()
        deleted, _ = FeedCommentLike.objects.filter(
            comment=comment,
            user=request.user
        ).delete()

        if deleted:
            comment.like_count = max(0, comment.like_count - 1)
            comment.save(update_fields=['like_count'])

        return Response({'status': 'unliked', 'like_count': comment.like_count})

    def destroy(self, request, *args, **kwargs):
        """論理削除"""
        comment = self.get_object()
        # 自分のコメントのみ削除可能
        if comment.user != request.user:
            return Response(
                {'error': '自分のコメントのみ削除できます'},
                status=status.HTTP_403_FORBIDDEN
            )

        comment.is_deleted = True
        comment.save(update_fields=['is_deleted'])

        # 投稿のコメント数を減らす
        comment.post.comment_count = max(0, comment.post.comment_count - 1)
        comment.post.save(update_fields=['comment_count'])

        return Response(status=status.HTTP_204_NO_CONTENT)


class FeedBookmarkViewSet(viewsets.ReadOnlyModelViewSet):
    """フィードブックマークビューセット（自分のブックマーク一覧）"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = FeedBookmarkSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return FeedBookmark.objects.filter(
            post__tenant_id=tenant_id,
            user=self.request.user,
            post__is_deleted=False
        ).select_related('post__author', 'post__school').order_by('-created_at')


class ChatLogViewSet(viewsets.ReadOnlyModelViewSet):
    """チャットログビューセット（管理者向け）"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        from apps.core.permissions import is_admin_user
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = ChatLog.objects.select_related('school', 'guardian', 'brand', 'message')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        # フィルタリング
        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)

        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(guardian_id=guardian_id)

        sender_type = self.request.query_params.get('sender_type')
        if sender_type:
            queryset = queryset.filter(sender_type=sender_type)

        # 日付範囲フィルタ
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)

        # 検索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(content__icontains=search) |
                Q(guardian_name__icontains=search) |
                Q(school_name__icontains=search) |
                Q(brand_name__icontains=search)
            )

        return queryset.order_by('-timestamp')

    def get_serializer_class(self):
        if self.action == 'list':
            return ChatLogListSerializer
        return ChatLogSerializer

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """チャットログの統計情報"""
        queryset = self.get_queryset()

        stats = {
            'total_messages': queryset.count(),
            'by_sender_type': {},
            'by_brand': {},
            'by_school': {},
        }

        # 送信者タイプ別
        for sender_type in ['GUARDIAN', 'STAFF', 'BOT']:
            stats['by_sender_type'][sender_type] = queryset.filter(
                sender_type=sender_type
            ).count()

        # ブランド別
        brand_stats = queryset.values('brand_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        stats['by_brand'] = {item['brand_name']: item['count'] for item in brand_stats}

        # 校舎別
        school_stats = queryset.values('school_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        stats['by_school'] = {
            item['school_name'] or 'その他': item['count']
            for item in school_stats
        }

        return Response(stats)

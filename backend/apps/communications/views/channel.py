"""
Channel Views - チャンネル管理Views
ChannelViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone

from apps.core.permissions import IsTenantUser
from ..models import Channel, ChannelMember, Message
from ..serializers import (
    ChannelListSerializer, ChannelDetailSerializer, ChannelCreateSerializer,
    ChannelMemberSerializer, MessageSerializer, MessageCreateSerializer,
)


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

    def _is_channel_admin(self, channel, user):
        """ユーザーがチャンネルの管理者かどうかを判定"""
        from apps.core.permissions import is_admin_user
        # システム管理者は常に管理者として扱う
        if is_admin_user(user):
            return True
        # チャンネルメンバーとしてADMINロールを持っているか
        member = channel.members.filter(user=user).first()
        return member and member.role == ChannelMember.Role.ADMIN

    @action(detail=True, methods=['put', 'patch'], url_path='settings')
    def update_settings(self, request, pk=None):
        """チャンネル設定を更新（名前・説明）"""
        channel = self.get_object()

        # 権限チェック
        if not self._is_channel_admin(channel, request.user):
            return Response(
                {'error': 'チャンネル設定の変更は管理者のみ可能です'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 更新可能なフィールド
        name = request.data.get('name')
        description = request.data.get('description')

        if name is not None:
            if not name.strip():
                return Response(
                    {'error': 'チャンネル名は必須です'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            channel.name = name.strip()

        if description is not None:
            channel.description = description

        channel.save()

        return Response(ChannelDetailSerializer(channel).data)

    @action(detail=True, methods=['get', 'post'])
    def members(self, request, pk=None):
        """メンバー管理"""
        channel = self.get_object()

        if request.method == 'GET':
            members = channel.members.select_related('user', 'guardian').all()
            serializer = ChannelMemberSerializer(members, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            # 権限チェック
            if not self._is_channel_admin(channel, request.user):
                return Response(
                    {'error': 'メンバーの追加は管理者のみ可能です'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # user_idまたはuserを取得
            user_id = request.data.get('user_id') or request.data.get('user')
            if not user_id:
                return Response(
                    {'error': 'user_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from django.contrib.auth import get_user_model
            User = get_user_model()

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 既存メンバーチェック
            if channel.members.filter(user=user).exists():
                return Response(
                    {'error': '既にメンバーです'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # メンバー追加
            role = request.data.get('role', ChannelMember.Role.MEMBER)
            member = ChannelMember.objects.create(
                channel=channel,
                user=user,
                role=role
            )

            return Response(ChannelMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='members/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        """メンバーを削除"""
        channel = self.get_object()

        # 権限チェック（管理者または自分自身の退出）
        is_self = str(request.user.id) == str(user_id)
        if not is_self and not self._is_channel_admin(channel, request.user):
            return Response(
                {'error': 'メンバーの削除は管理者のみ可能です'},
                status=status.HTTP_403_FORBIDDEN
            )

        # メンバーを取得
        member = channel.members.filter(user_id=user_id).first()
        if not member:
            return Response(
                {'error': 'メンバーが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 最後の管理者は削除不可
        if member.role == ChannelMember.Role.ADMIN:
            admin_count = channel.members.filter(role=ChannelMember.Role.ADMIN).count()
            if admin_count <= 1:
                return Response(
                    {'error': '最後の管理者は削除できません。別の管理者を指定してください'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        member.delete()

        return Response({'status': 'removed'})

    @action(detail=True, methods=['put'], url_path='members/(?P<user_id>[^/.]+)/role')
    def update_member_role(self, request, pk=None, user_id=None):
        """メンバーのロールを更新"""
        channel = self.get_object()

        # 権限チェック
        if not self._is_channel_admin(channel, request.user):
            return Response(
                {'error': 'ロールの変更は管理者のみ可能です'},
                status=status.HTTP_403_FORBIDDEN
            )

        # メンバーを取得
        member = channel.members.filter(user_id=user_id).first()
        if not member:
            return Response(
                {'error': 'メンバーが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        new_role = request.data.get('role')
        if new_role not in [r[0] for r in ChannelMember.Role.choices]:
            return Response(
                {'error': f'Invalid role. Valid roles: {[r[0] for r in ChannelMember.Role.choices]}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ADMINからの降格時、最後の管理者チェック
        if member.role == ChannelMember.Role.ADMIN and new_role != ChannelMember.Role.ADMIN:
            admin_count = channel.members.filter(role=ChannelMember.Role.ADMIN).count()
            if admin_count <= 1:
                return Response(
                    {'error': '最後の管理者のロールは変更できません。別の管理者を指定してください'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        member.role = new_role
        member.save(update_fields=['role'])

        return Response(ChannelMemberSerializer(member).data)

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
        from apps.tenants.models import Employee
        User = get_user_model()

        target_user = None
        # まずUser IDで検索
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            # User IDで見つからない場合、Employee IDとして検索し、メールでUserを探す
            try:
                employee = Employee.objects.get(id=target_user_id)
                if employee.email:
                    target_user = User.objects.filter(email=employee.email).first()
            except Employee.DoesNotExist:
                pass

        if not target_user:
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

    @action(detail=True, methods=['get'], url_path='mentionable-users')
    def mentionable_users(self, request, pk=None):
        """メンション可能なユーザー一覧を取得"""
        channel = self.get_object()

        # チャンネルメンバーからアクティブなユーザーを取得
        members = channel.members.select_related('user').filter(
            user__isnull=False,
            user__is_active=True
        ).exclude(user=request.user)  # 自分自身は除外

        users = [
            {
                'id': str(member.user.id),
                'name': member.user.full_name or member.user.email,
                'email': member.user.email,
            }
            for member in members
        ]

        return Response(users)

    @action(detail=True, methods=['post'], url_path='toggle-pin')
    def toggle_pin(self, request, pk=None):
        """チャンネルのピン留めを切り替え"""
        channel = self.get_object()
        member = channel.members.filter(user=request.user).first()

        if not member:
            return Response(
                {'error': 'メンバーではありません'},
                status=status.HTTP_403_FORBIDDEN
            )

        member.is_pinned = not member.is_pinned
        member.save(update_fields=['is_pinned'])

        return Response({
            'status': 'ok',
            'is_pinned': member.is_pinned
        })

    @action(detail=True, methods=['post'], url_path='toggle-mute')
    def toggle_mute(self, request, pk=None):
        """チャンネルのミュートを切り替え"""
        channel = self.get_object()
        member = channel.members.filter(user=request.user).first()

        if not member:
            return Response(
                {'error': 'メンバーではありません'},
                status=status.HTTP_403_FORBIDDEN
            )

        member.is_muted = not member.is_muted
        member.save(update_fields=['is_muted'])

        return Response({
            'status': 'ok',
            'is_muted': member.is_muted
        })

    @action(detail=True, methods=['post'], url_path='unarchive')
    def unarchive(self, request, pk=None):
        """アーカイブ解除"""
        channel = self.get_object()

        # 権限チェック
        if not self._is_channel_admin(channel, request.user):
            return Response(
                {'error': 'アーカイブ解除は管理者のみ可能です'},
                status=status.HTTP_403_FORBIDDEN
            )

        channel.is_archived = False
        channel.save(update_fields=['is_archived'])
        return Response(ChannelDetailSerializer(channel).data)

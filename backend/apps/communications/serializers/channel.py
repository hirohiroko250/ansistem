"""
Channel & Message Serializers - チャンネル・メッセージシリアライザー
"""
from rest_framework import serializers
from apps.communications.models import (
    Channel, ChannelMember, Message, MessageRead
)


class ChannelMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)

    class Meta:
        model = ChannelMember
        fields = [
            'id', 'channel', 'user', 'user_name', 'guardian', 'guardian_name',
            'role', 'last_read_at', 'is_muted', 'is_pinned', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at']


class ChannelListSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_pinned = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()

    class Meta:
        model = Channel
        fields = [
            'id', 'channel_type', 'name', 'student', 'guardian', 'school',
            'is_archived', 'member_count', 'last_message', 'unread_count',
            'is_pinned', 'is_muted', 'created_at', 'updated_at'
        ]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_last_message(self, obj):
        last_msg = obj.messages.filter(is_deleted=False).last()
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content[:100],
                'sender_name': last_msg.sender_name,
                'created_at': last_msg.created_at
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            member = obj.members.filter(user=request.user).first()
            if member:
                from django.db.models import Q
                # 自分が送信したメッセージは除外
                # sender（スタッフ）が自分でない、かつsender_guardian（保護者）も自分に紐づく保護者でない
                exclude_filter = Q(sender=request.user)

                # ユーザーに紐づく保護者があれば、その保護者からのメッセージも除外
                if hasattr(request.user, 'guardian'):
                    exclude_filter |= Q(sender_guardian=request.user.guardian)

                base_query = obj.messages.filter(is_deleted=False).exclude(exclude_filter)

                if member.last_read_at:
                    # last_read_at以降の相手からのメッセージをカウント
                    return base_query.filter(created_at__gt=member.last_read_at).count()
                else:
                    # last_read_atがNoneの場合は相手からの全メッセージを未読とする
                    return base_query.count()
        return 0

    def get_is_pinned(self, obj):
        request = self.context.get('request')
        if request and request.user:
            member = obj.members.filter(user=request.user).first()
            if member:
                return member.is_pinned
        return False

    def get_is_muted(self, obj):
        request = self.context.get('request')
        if request and request.user:
            member = obj.members.filter(user=request.user).first()
            if member:
                return member.is_muted
        return False


class ChannelDetailSerializer(serializers.ModelSerializer):
    members = ChannelMemberSerializer(many=True, read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)

    class Meta:
        model = Channel
        fields = [
            'id', 'tenant_id', 'channel_type', 'name', 'description',
            'student', 'student_name', 'guardian', 'guardian_name',
            'school', 'school_name', 'is_archived', 'members',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant_id', 'created_at', 'updated_at']


class ChannelCreateSerializer(serializers.ModelSerializer):
    member_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Channel
        fields = [
            'id', 'channel_type', 'name', 'description',
            'student', 'guardian', 'school', 'member_ids'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids', [])
        channel = Channel.objects.create(**validated_data)

        # メンバー追加
        request = self.context.get('request')
        if request and request.user:
            # ユーザーが保護者プロファイルを持っている場合、guardianも設定
            guardian = None
            if hasattr(request.user, 'guardian_profile') and request.user.guardian_profile:
                guardian = request.user.guardian_profile

            ChannelMember.objects.create(
                channel=channel,
                user=request.user,
                guardian=guardian,
                role=ChannelMember.Role.ADMIN
            )

        from apps.users.models import User
        for user_id in member_ids:
            try:
                user = User.objects.get(id=user_id)
                ChannelMember.objects.get_or_create(
                    channel=channel,
                    user=user,
                    defaults={'role': ChannelMember.Role.MEMBER}
                )
            except User.DoesNotExist:
                pass

        # サポートチャンネルの場合、自動返信メッセージを作成
        if channel.channel_type == Channel.ChannelType.SUPPORT:
            Message.objects.create(
                tenant_id=channel.tenant_id,
                channel=channel,
                message_type='text',
                content='お問い合わせありがとうございます。担当者が確認次第、折り返しご連絡いたします。しばらくお待ちください。',
                is_bot_message=True,
            )

            # 作業一覧にタスクを作成
            from apps.tasks.models import Task
            Task.objects.create(
                tenant_id=channel.tenant_id,
                task_type='chat',
                title=f'チャット対応: {channel.name}',
                description=f'チャンネル「{channel.name}」が作成されました。対応をお願いします。',
                status='new',
                priority='normal',
                source_type='channel',
                source_id=channel.id,
            )

        return channel


class MessageReactionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        from apps.communications.models import MessageReaction
        model = MessageReaction
        fields = ['id', 'emoji', 'user', 'user_name', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(read_only=True)
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    reply_to_content = serializers.CharField(source='reply_to.content', read_only=True)
    reply_to_sender_name = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    read_count = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    mentions = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'channel', 'message_type', 'sender', 'sender_name', 'sender_email',
            'sender_guardian', 'is_bot_message', 'content',
            'attachment_url', 'attachment_name',
            'reply_to', 'reply_to_content', 'reply_to_sender_name', 'reply_count',
            'read_count', 'reactions', 'mentions',
            'is_edited', 'edited_at', 'is_deleted', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'is_edited', 'edited_at', 'created_at']

    def get_reply_to_sender_name(self, obj):
        """返信先メッセージの送信者名を取得"""
        if obj.reply_to:
            return obj.reply_to.sender_name
        return None

    def get_read_count(self, obj):
        """既読人数を取得"""
        return obj.reads.count()

    def get_reply_count(self, obj):
        """スレッド返信数を取得"""
        return obj.replies.filter(is_deleted=False).count()

    def get_reactions(self, obj):
        """リアクション一覧を絵文字ごとにグループ化して取得"""
        from collections import defaultdict
        reactions = obj.reactions.select_related('user').all()

        # 絵文字ごとにグループ化
        grouped = defaultdict(list)
        for reaction in reactions:
            grouped[reaction.emoji].append({
                'user_id': str(reaction.user_id),
                'user_name': reaction.user.full_name if reaction.user else 'Unknown',
            })

        return [
            {
                'emoji': emoji,
                'count': len(users),
                'users': users,
            }
            for emoji, users in grouped.items()
        ]

    def get_mentions(self, obj):
        """メンション一覧を取得"""
        mentions = obj.mentions.select_related('mentioned_user').all()
        return [
            {
                'user_id': str(mention.mentioned_user_id),
                'user_name': mention.mentioned_user.full_name if mention.mentioned_user else 'Unknown',
                'start_index': mention.start_index,
                'end_index': mention.end_index,
            }
            for mention in mentions
        ]


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['channel', 'message_type', 'content', 'attachment_url', 'attachment_name', 'reply_to']

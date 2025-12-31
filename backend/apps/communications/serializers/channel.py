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
            'role', 'last_read_at', 'is_muted', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at']


class ChannelListSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Channel
        fields = [
            'id', 'channel_type', 'name', 'student', 'guardian', 'school',
            'is_archived', 'member_count', 'last_message', 'unread_count',
            'created_at', 'updated_at'
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
            if member and member.last_read_at:
                return obj.messages.filter(
                    created_at__gt=member.last_read_at,
                    is_deleted=False
                ).count()
        return 0


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


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(read_only=True)
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    reply_to_content = serializers.CharField(source='reply_to.content', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'channel', 'message_type', 'sender', 'sender_name', 'sender_email',
            'sender_guardian', 'is_bot_message', 'content',
            'attachment_url', 'attachment_name',
            'reply_to', 'reply_to_content',
            'is_edited', 'edited_at', 'is_deleted', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'is_edited', 'edited_at', 'created_at']


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['channel', 'message_type', 'content', 'attachment_url', 'attachment_name', 'reply_to']

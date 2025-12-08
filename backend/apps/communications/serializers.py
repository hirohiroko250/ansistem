"""
Communications Serializers
"""
from rest_framework import serializers
from .models import (
    Channel, ChannelMember, Message, MessageRead,
    ContactLog, ContactLogComment, Notification,
    BotConfig, BotFAQ, BotConversation,
    Announcement, AnnouncementRead,
    FeedPost, FeedMedia, FeedLike, FeedComment, FeedCommentLike, FeedBookmark,
    ChatLog
)


# Channel Serializers
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


# Message Serializers
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


# Contact Log Serializers
class ContactLogCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = ContactLogComment
        fields = ['id', 'contact_log', 'user', 'user_name', 'content', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class ContactLogListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    handled_by_name = serializers.CharField(source='handled_by.full_name', read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = ContactLog
        fields = [
            'id', 'contact_type', 'subject', 'student', 'student_name',
            'guardian', 'guardian_name', 'school', 'handled_by', 'handled_by_name',
            'priority', 'status', 'follow_up_date', 'tags',
            'comment_count', 'created_at', 'updated_at'
        ]

    def get_comment_count(self, obj):
        return obj.comments.count()


class ContactLogDetailSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    handled_by_name = serializers.CharField(source='handled_by.full_name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)
    comments = ContactLogCommentSerializer(many=True, read_only=True)

    class Meta:
        model = ContactLog
        fields = [
            'id', 'tenant_id', 'contact_type', 'subject', 'content',
            'student', 'student_name', 'guardian', 'guardian_name',
            'school', 'school_name', 'handled_by', 'handled_by_name',
            'priority', 'status', 'related_channel',
            'follow_up_date', 'follow_up_notes',
            'resolved_at', 'resolved_by', 'resolved_by_name',
            'tags', 'comments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant_id', 'created_at', 'updated_at']


class ContactLogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactLog
        fields = [
            'contact_type', 'subject', 'content',
            'student', 'guardian', 'school',
            'priority', 'status', 'follow_up_date', 'follow_up_notes', 'tags'
        ]


# Notification Serializers
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'content',
            'link_type', 'link_id', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# Bot Serializers
class BotFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotFAQ
        fields = [
            'id', 'bot_config', 'category', 'question', 'keywords',
            'answer', 'next_action', 'sort_order', 'is_active'
        ]
        read_only_fields = ['id']


class BotConfigSerializer(serializers.ModelSerializer):
    faqs = BotFAQSerializer(many=True, read_only=True)
    faq_count = serializers.SerializerMethodField()

    class Meta:
        model = BotConfig
        fields = [
            'id', 'tenant_id', 'name', 'bot_type',
            'welcome_message', 'fallback_message',
            'is_active', 'ai_enabled', 'ai_model', 'ai_system_prompt',
            'faqs', 'faq_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant_id', 'created_at', 'updated_at']

    def get_faq_count(self, obj):
        return obj.faqs.filter(is_active=True).count()


class BotConversationSerializer(serializers.ModelSerializer):
    matched_faq_question = serializers.CharField(source='matched_faq.question', read_only=True)

    class Meta:
        model = BotConversation
        fields = [
            'id', 'channel', 'bot_config', 'user_input', 'bot_response',
            'matched_faq', 'matched_faq_question', 'is_ai_response',
            'escalated_to_staff', 'escalated_at', 'was_helpful', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BotChatSerializer(serializers.Serializer):
    """ボットチャット用"""
    message = serializers.CharField()
    channel_id = serializers.UUIDField(required=False)


# Announcement Serializers
class AnnouncementListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'target_type', 'status',
            'scheduled_at', 'sent_at', 'sent_count', 'read_count',
            'created_by', 'created_by_name', 'created_at'
        ]


class AnnouncementDetailSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    target_schools_detail = serializers.SerializerMethodField()
    target_grades_detail = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            'id', 'tenant_id', 'title', 'content', 'target_type',
            'target_schools', 'target_schools_detail',
            'target_grades', 'target_grades_detail',
            'status', 'scheduled_at', 'sent_at',
            'sent_count', 'read_count',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant_id', 'sent_at', 'sent_count', 'read_count', 'created_at', 'updated_at']

    def get_target_schools_detail(self, obj):
        return [{'id': s.id, 'name': s.school_name} for s in obj.target_schools.all()]

    def get_target_grades_detail(self, obj):
        return [{'id': g.id, 'name': g.grade_name} for g in obj.target_grades.all()]


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'target_type',
            'target_schools', 'target_grades', 'scheduled_at'
        ]


# Feed Serializers
class FeedMediaSerializer(serializers.ModelSerializer):
    """フィードメディアシリアライザー"""
    class Meta:
        model = FeedMedia
        fields = [
            'id', 'media_type', 'file_url', 'thumbnail_url',
            'file_name', 'file_size', 'width', 'height',
            'duration', 'sort_order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class FeedCommentSerializer(serializers.ModelSerializer):
    """フィードコメントシリアライザー"""
    commenter_name = serializers.CharField(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    reply_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = FeedComment
        fields = [
            'id', 'post', 'user', 'user_email', 'guardian', 'guardian_name',
            'commenter_name', 'content', 'parent', 'like_count',
            'reply_count', 'is_liked', 'is_deleted', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'like_count', 'created_at', 'updated_at']

    def get_reply_count(self, obj):
        return obj.replies.filter(is_deleted=False).count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False


class FeedCommentCreateSerializer(serializers.ModelSerializer):
    """フィードコメント作成用シリアライザー"""
    class Meta:
        model = FeedComment
        fields = ['post', 'content', 'parent']


class FeedPostListSerializer(serializers.ModelSerializer):
    """フィード投稿一覧用シリアライザー"""
    author_name = serializers.CharField(read_only=True)
    author_email = serializers.EmailField(source='author.email', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    media = FeedMediaSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = FeedPost
        fields = [
            'id', 'post_type', 'author', 'author_name', 'author_email',
            'school', 'school_name', 'content', 'visibility',
            'hashtags', 'is_pinned', 'allow_comments', 'allow_likes',
            'like_count', 'comment_count', 'view_count',
            'media', 'is_liked', 'is_bookmarked',
            'is_published', 'published_at', 'created_at', 'updated_at'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.bookmarks.filter(user=request.user).exists()
        return False


class FeedPostDetailSerializer(serializers.ModelSerializer):
    """フィード投稿詳細用シリアライザー"""
    author_name = serializers.CharField(read_only=True)
    author_email = serializers.EmailField(source='author.email', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    media = FeedMediaSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    target_schools_detail = serializers.SerializerMethodField()
    target_grades_detail = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = FeedPost
        fields = [
            'id', 'tenant_id', 'post_type', 'author', 'author_name', 'author_email',
            'school', 'school_name', 'content', 'visibility',
            'target_schools', 'target_schools_detail',
            'target_grades', 'target_grades_detail',
            'hashtags', 'is_pinned', 'pinned_at',
            'allow_comments', 'allow_likes',
            'like_count', 'comment_count', 'view_count',
            'media', 'comments', 'is_liked', 'is_bookmarked',
            'is_published', 'published_at',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'tenant_id', 'like_count', 'comment_count', 'view_count',
            'created_at', 'updated_at'
        ]

    def get_comments(self, obj):
        # トップレベルのコメントのみ取得（返信は除く）
        comments = obj.comments.filter(is_deleted=False, parent__isnull=True)[:10]
        return FeedCommentSerializer(
            comments, many=True, context=self.context
        ).data

    def get_target_schools_detail(self, obj):
        return [{'id': str(s.id), 'name': s.school_name} for s in obj.target_schools.all()]

    def get_target_grades_detail(self, obj):
        return [{'id': str(g.id), 'name': g.grade_name} for g in obj.target_grades.all()]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.bookmarks.filter(user=request.user).exists()
        return False


class FeedPostCreateSerializer(serializers.ModelSerializer):
    """フィード投稿作成用シリアライザー"""
    media_items = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = FeedPost
        fields = [
            'post_type', 'school', 'content', 'visibility',
            'target_schools', 'target_grades', 'hashtags',
            'allow_comments', 'allow_likes', 'is_published',
            'media_items'
        ]

    def create(self, validated_data):
        media_items = validated_data.pop('media_items', [])
        target_schools = validated_data.pop('target_schools', [])
        target_grades = validated_data.pop('target_grades', [])

        post = FeedPost.objects.create(**validated_data)

        # ManyToManyフィールドの設定
        if target_schools:
            post.target_schools.set(target_schools)
        if target_grades:
            post.target_grades.set(target_grades)

        # メディアの作成
        for i, media_data in enumerate(media_items):
            FeedMedia.objects.create(
                post=post,
                media_type=media_data.get('media_type', FeedMedia.MediaType.IMAGE),
                file_url=media_data.get('file_url'),
                thumbnail_url=media_data.get('thumbnail_url'),
                file_name=media_data.get('file_name'),
                file_size=media_data.get('file_size'),
                width=media_data.get('width'),
                height=media_data.get('height'),
                duration=media_data.get('duration'),
                sort_order=i
            )

        return post


class FeedLikeSerializer(serializers.ModelSerializer):
    """フィードいいねシリアライザー"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = FeedLike
        fields = ['id', 'post', 'user', 'user_name', 'guardian', 'created_at']
        read_only_fields = ['id', 'created_at']


class FeedBookmarkSerializer(serializers.ModelSerializer):
    """フィードブックマークシリアライザー"""
    post_detail = FeedPostListSerializer(source='post', read_only=True)

    class Meta:
        model = FeedBookmark
        fields = ['id', 'post', 'post_detail', 'created_at']
        read_only_fields = ['id', 'created_at']


# ChatLog Serializers
class ChatLogSerializer(serializers.ModelSerializer):
    """チャットログシリアライザー"""

    class Meta:
        model = ChatLog
        fields = [
            'id', 'tenant_id', 'message', 'school', 'school_name',
            'guardian', 'guardian_name', 'brand', 'brand_name',
            'content', 'sender_type', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class ChatLogListSerializer(serializers.ModelSerializer):
    """チャットログ一覧用シリアライザー"""

    class Meta:
        model = ChatLog
        fields = [
            'id', 'brand_name', 'school_name', 'guardian_name',
            'content', 'sender_type', 'timestamp'
        ]

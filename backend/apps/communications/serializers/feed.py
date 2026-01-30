"""
Feed Serializers - フィードシリアライザー
"""
from rest_framework import serializers
from apps.communications.models import (
    FeedPost, FeedMedia, FeedLike, FeedComment, FeedCommentLike, FeedBookmark
)


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
    target_brands_detail = serializers.SerializerMethodField()
    target_schools_detail = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FeedPost
        fields = [
            'id', 'post_type', 'author', 'author_name', 'author_email',
            'school', 'school_name', 'title', 'content', 'visibility',
            'target_brands', 'target_brands_detail',
            'target_schools', 'target_schools_detail',
            'hashtags', 'is_pinned', 'allow_comments', 'allow_likes',
            'like_count', 'comment_count', 'view_count',
            'media', 'is_liked', 'is_bookmarked',
            'is_published', 'published_at',
            'publish_start_at', 'publish_end_at',
            'approval_status', 'approved_by', 'approved_by_name', 'approved_at',
            'created_at', 'updated_at'
        ]

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.full_name or obj.approved_by.email
        return None

    def get_target_brands_detail(self, obj):
        return [{'id': str(b.id), 'name': b.brand_name} for b in obj.target_brands.all()]

    def get_target_schools_detail(self, obj):
        return [{'id': str(s.id), 'name': s.school_name} for s in obj.target_schools.all()]

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
    target_brands_detail = serializers.SerializerMethodField()
    target_schools_detail = serializers.SerializerMethodField()
    target_grades_detail = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FeedPost
        fields = [
            'id', 'tenant_id', 'post_type', 'author', 'author_name', 'author_email',
            'school', 'school_name', 'title', 'content', 'visibility',
            'target_brands', 'target_brands_detail',
            'target_schools', 'target_schools_detail',
            'target_grades', 'target_grades_detail',
            'hashtags', 'is_pinned', 'pinned_at',
            'allow_comments', 'allow_likes',
            'like_count', 'comment_count', 'view_count',
            'media', 'comments', 'is_liked', 'is_bookmarked',
            'is_published', 'published_at',
            'publish_start_at', 'publish_end_at',
            'approval_status', 'approved_by', 'approved_by_name', 'approved_at',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'tenant_id', 'like_count', 'comment_count', 'view_count',
            'approval_status', 'approved_by', 'approved_at',
            'created_at', 'updated_at'
        ]

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.full_name or obj.approved_by.email
        return None

    def get_comments(self, obj):
        # トップレベルのコメントのみ取得（返信は除く）
        comments = obj.comments.filter(is_deleted=False, parent__isnull=True)[:10]
        return FeedCommentSerializer(
            comments, many=True, context=self.context
        ).data

    def get_target_brands_detail(self, obj):
        return [{'id': str(b.id), 'name': b.brand_name} for b in obj.target_brands.all()]

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
            'post_type', 'school', 'title', 'content', 'visibility',
            'target_brands', 'target_schools', 'target_grades', 'hashtags',
            'allow_comments', 'allow_likes', 'is_published', 'is_pinned',
            'publish_start_at', 'publish_end_at',
            'media_items'
        ]

    def create(self, validated_data):
        media_items = validated_data.pop('media_items', [])
        target_brands = validated_data.pop('target_brands', [])
        target_schools = validated_data.pop('target_schools', [])
        target_grades = validated_data.pop('target_grades', [])

        post = FeedPost.objects.create(**validated_data)

        # ManyToManyフィールドの設定
        if target_brands:
            post.target_brands.set(target_brands)
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

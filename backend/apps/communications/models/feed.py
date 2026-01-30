"""
Feed Models - フィード投稿関連（Instagram風）
FeedPost, FeedMedia, FeedLike, FeedComment, FeedCommentLike, FeedBookmark
"""
import uuid
from django.db import models
from django.conf import settings


class FeedPost(models.Model):
    """フィード投稿（Instagram風）"""

    class PostType(models.TextChoices):
        TEXT = 'TEXT', 'テキスト'
        IMAGE = 'IMAGE', '画像'
        VIDEO = 'VIDEO', '動画'
        GALLERY = 'GALLERY', 'ギャラリー（複数画像）'

    class Visibility(models.TextChoices):
        PUBLIC = 'PUBLIC', '全体公開'
        SCHOOL = 'SCHOOL', '校舎限定'
        GRADE = 'GRADE', '学年限定'
        STAFF = 'STAFF', 'スタッフのみ'

    class ApprovalStatus(models.TextChoices):
        PENDING = 'pending', '申請中'
        APPROVED = 'approved', '承認済'
        REJECTED = 'rejected', '却下'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    post_type = models.CharField(
        max_length=20,
        choices=PostType.choices,
        default=PostType.TEXT,
        verbose_name='投稿種別'
    )
    # 投稿者
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='feed_posts',
        verbose_name='投稿者'
    )
    # 投稿元校舎
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feed_posts',
        verbose_name='校舎'
    )
    # 題名
    title = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='題名'
    )
    # 内容
    content = models.TextField(
        verbose_name='本文'
    )
    # 公開範囲
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        verbose_name='公開範囲'
    )
    # 公開対象の詳細
    target_brands = models.ManyToManyField(
        'schools.Brand',
        blank=True,
        related_name='visible_feed_posts',
        verbose_name='対象ブランド'
    )
    target_schools = models.ManyToManyField(
        'schools.School',
        blank=True,
        related_name='visible_feed_posts',
        verbose_name='対象校舎'
    )
    target_grades = models.ManyToManyField(
        'schools.Grade',
        blank=True,
        related_name='visible_feed_posts',
        verbose_name='対象学年'
    )
    # ハッシュタグ
    hashtags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='ハッシュタグ'
    )
    # 固定表示
    is_pinned = models.BooleanField(
        default=False,
        verbose_name='固定表示'
    )
    pinned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='固定日時'
    )
    # コメント許可
    allow_comments = models.BooleanField(
        default=True,
        verbose_name='コメント許可'
    )
    # いいね許可
    allow_likes = models.BooleanField(
        default=True,
        verbose_name='いいね許可'
    )
    # 統計
    like_count = models.IntegerField(
        default=0,
        verbose_name='いいね数'
    )
    comment_count = models.IntegerField(
        default=0,
        verbose_name='コメント数'
    )
    view_count = models.IntegerField(
        default=0,
        verbose_name='閲覧数'
    )
    # 公開設定
    is_published = models.BooleanField(
        default=True,
        verbose_name='公開済み'
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='公開日時'
    )
    # 公開期間
    publish_start_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='公開開始日時',
        help_text='指定しない場合は即時公開'
    )
    publish_end_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='公開終了日時',
        help_text='指定しない場合は無期限'
    )
    # 承認
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
        verbose_name='承認ステータス',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_feed_posts',
        verbose_name='承認者',
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='承認日時',
    )
    # 削除
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='削除済み'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='削除日時'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'communication_feed_posts'
        verbose_name = 'フィード投稿'
        verbose_name_plural = 'フィード投稿'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.author.email if self.author else 'Unknown'}: {self.content[:50]}..."

    @property
    def author_name(self):
        if self.author:
            return self.author.full_name or self.author.email
        return 'Unknown'


class FeedMedia(models.Model):
    """フィードメディア（画像・動画）"""

    class MediaType(models.TextChoices):
        IMAGE = 'IMAGE', '画像'
        VIDEO = 'VIDEO', '動画'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    post = models.ForeignKey(
        FeedPost,
        on_delete=models.CASCADE,
        related_name='media',
        verbose_name='投稿'
    )
    media_type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
        verbose_name='メディア種別'
    )
    file_url = models.URLField(
        verbose_name='ファイルURL'
    )
    thumbnail_url = models.URLField(
        null=True,
        blank=True,
        verbose_name='サムネイルURL'
    )
    file_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='ファイル名'
    )
    file_size = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ファイルサイズ'
    )
    width = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='幅'
    )
    height = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='高さ'
    )
    duration = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='長さ（秒）'
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name='表示順'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_feed_media'
        verbose_name = 'フィードメディア'
        verbose_name_plural = 'フィードメディア'
        ordering = ['sort_order', 'created_at']

    def __str__(self):
        return f"{self.get_media_type_display()}: {self.file_name or self.file_url}"


class FeedLike(models.Model):
    """フィードいいね"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    post = models.ForeignKey(
        FeedPost,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name='投稿'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='feed_likes',
        verbose_name='ユーザー'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='feed_likes',
        verbose_name='保護者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_feed_likes'
        verbose_name = 'フィードいいね'
        verbose_name_plural = 'フィードいいね'
        unique_together = [['post', 'user'], ['post', 'guardian']]

    def __str__(self):
        liker = self.user.email if self.user else (self.guardian.full_name if self.guardian else 'Unknown')
        return f"{liker} liked {self.post.id}"


class FeedComment(models.Model):
    """フィードコメント"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    post = models.ForeignKey(
        FeedPost,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='投稿'
    )
    # コメント者
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feed_comments',
        verbose_name='ユーザー'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feed_comments',
        verbose_name='保護者'
    )
    content = models.TextField(
        verbose_name='コメント'
    )
    # 返信先
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='返信先'
    )
    # いいね数
    like_count = models.IntegerField(
        default=0,
        verbose_name='いいね数'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='削除済み'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'communication_feed_comments'
        verbose_name = 'フィードコメント'
        verbose_name_plural = 'フィードコメント'
        ordering = ['created_at']

    def __str__(self):
        commenter = self.user.email if self.user else (self.guardian.full_name if self.guardian else 'Unknown')
        return f"{commenter}: {self.content[:50]}..."

    @property
    def commenter_name(self):
        if self.user:
            return self.user.full_name or self.user.email
        if self.guardian:
            return self.guardian.full_name
        return 'Unknown'


class FeedCommentLike(models.Model):
    """フィードコメントいいね"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    comment = models.ForeignKey(
        FeedComment,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name='コメント'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='ユーザー'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='保護者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_feed_comment_likes'
        verbose_name = 'コメントいいね'
        verbose_name_plural = 'コメントいいね'
        unique_together = [['comment', 'user'], ['comment', 'guardian']]


class FeedBookmark(models.Model):
    """フィードブックマーク（保存）"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    post = models.ForeignKey(
        FeedPost,
        on_delete=models.CASCADE,
        related_name='bookmarks',
        verbose_name='投稿'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='feed_bookmarks',
        verbose_name='ユーザー'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='feed_bookmarks',
        verbose_name='保護者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_feed_bookmarks'
        verbose_name = 'フィードブックマーク'
        verbose_name_plural = 'フィードブックマーク'
        unique_together = [['post', 'user'], ['post', 'guardian']]

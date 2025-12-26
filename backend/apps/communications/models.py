"""
Communications Models
内部・外部コミュニケーション、対応履歴、チャットボット
"""
import uuid
from django.db import models
from django.conf import settings


class Channel(models.Model):
    """チャンネル（チャットルーム）"""

    class ChannelType(models.TextChoices):
        INTERNAL = 'INTERNAL', '内部（スタッフ間）'
        EXTERNAL = 'EXTERNAL', '外部（保護者・生徒）'
        SUPPORT = 'SUPPORT', 'サポート'
        BOT = 'BOT', 'ボット'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    channel_type = models.CharField(
        max_length=20,
        choices=ChannelType.choices,
        verbose_name='チャンネル種別'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='チャンネル名'
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name='説明'
    )
    # 外部チャンネルの場合、関連する生徒・保護者
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_channels',
        verbose_name='生徒'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_channels',
        verbose_name='保護者'
    )
    # 内部チャンネルの場合、関連する校舎
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_channels',
        verbose_name='校舎'
    )
    is_archived = models.BooleanField(
        default=False,
        verbose_name='アーカイブ済み'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'communication_channels'
        verbose_name = 'チャンネル'
        verbose_name_plural = 'チャンネル'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class ChannelMember(models.Model):
    """チャンネルメンバー"""

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', '管理者'
        MEMBER = 'MEMBER', 'メンバー'
        READONLY = 'READONLY', '閲覧のみ'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name='チャンネル'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='channel_memberships',
        verbose_name='ユーザー'
    )
    # 保護者がメンバーの場合
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='channel_memberships',
        verbose_name='保護者'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        verbose_name='役割'
    )
    last_read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最終既読日時'
    )
    is_muted = models.BooleanField(
        default=False,
        verbose_name='ミュート'
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='参加日時')

    class Meta:
        db_table = 'communication_channel_members'
        verbose_name = 'チャンネルメンバー'
        verbose_name_plural = 'チャンネルメンバー'
        unique_together = [['channel', 'user'], ['channel', 'guardian']]

    def __str__(self):
        member_name = self.user.email if self.user else self.guardian.full_name if self.guardian else 'Unknown'
        return f"{member_name} in {self.channel.name}"


class Message(models.Model):
    """メッセージ"""

    class MessageType(models.TextChoices):
        TEXT = 'TEXT', 'テキスト'
        IMAGE = 'IMAGE', '画像'
        FILE = 'FILE', 'ファイル'
        SYSTEM = 'SYSTEM', 'システム'
        BOT = 'BOT', 'ボット'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='チャンネル'
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        verbose_name='メッセージ種別'
    )
    # 送信者（スタッフ/管理者）
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_messages',
        verbose_name='送信者'
    )
    # 送信者（保護者）
    sender_guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_messages',
        verbose_name='送信者（保護者）'
    )
    # ボットからの場合
    is_bot_message = models.BooleanField(
        default=False,
        verbose_name='ボットメッセージ'
    )
    content = models.TextField(verbose_name='内容')
    # ファイル添付
    attachment_url = models.URLField(
        null=True,
        blank=True,
        verbose_name='添付ファイルURL'
    )
    attachment_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='添付ファイル名'
    )
    # 返信先
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='返信先'
    )
    is_edited = models.BooleanField(
        default=False,
        verbose_name='編集済み'
    )
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='編集日時'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='削除済み'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_messages'
        verbose_name = 'メッセージ'
        verbose_name_plural = 'メッセージ'
        ordering = ['created_at']

    def __str__(self):
        sender_name = 'Bot' if self.is_bot_message else (
            self.sender.email if self.sender else
            self.sender_guardian.full_name if self.sender_guardian else 'Unknown'
        )
        return f"{sender_name}: {self.content[:50]}..."

    @property
    def sender_name(self):
        if self.is_bot_message:
            return 'アシスタント'
        if self.sender:
            return self.sender.full_name or self.sender.email
        if self.sender_guardian:
            return self.sender_guardian.full_name
        return 'Unknown'


class MessageRead(models.Model):
    """メッセージ既読"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reads',
        verbose_name='メッセージ'
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
    read_at = models.DateTimeField(auto_now_add=True, verbose_name='既読日時')

    class Meta:
        db_table = 'communication_message_reads'
        verbose_name = 'メッセージ既読'
        verbose_name_plural = 'メッセージ既読'
        unique_together = [['message', 'user'], ['message', 'guardian']]


class ContactLog(models.Model):
    """対応履歴/CRM"""

    class ContactType(models.TextChoices):
        PHONE_IN = 'PHONE_IN', '電話（受信）'
        PHONE_OUT = 'PHONE_OUT', '電話（発信）'
        EMAIL_IN = 'EMAIL_IN', 'メール（受信）'
        EMAIL_OUT = 'EMAIL_OUT', 'メール（送信）'
        VISIT = 'VISIT', '来校'
        MEETING = 'MEETING', '面談'
        ONLINE_MEETING = 'ONLINE_MEETING', 'オンライン面談'
        CHAT = 'CHAT', 'チャット'
        OTHER = 'OTHER', 'その他'

    class Priority(models.TextChoices):
        LOW = 'LOW', '低'
        MEDIUM = 'MEDIUM', '中'
        HIGH = 'HIGH', '高'
        URGENT = 'URGENT', '緊急'

    class Status(models.TextChoices):
        OPEN = 'OPEN', '対応中'
        PENDING = 'PENDING', '保留'
        RESOLVED = 'RESOLVED', '解決'
        CLOSED = 'CLOSED', 'クローズ'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    # 対象
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='contact_logs',
        verbose_name='生徒'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='contact_logs',
        verbose_name='保護者'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_logs',
        verbose_name='校舎'
    )
    contact_type = models.CharField(
        max_length=20,
        choices=ContactType.choices,
        verbose_name='対応種別'
    )
    subject = models.CharField(
        max_length=200,
        verbose_name='件名'
    )
    content = models.TextField(
        verbose_name='内容'
    )
    # 対応者
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='handled_contact_logs',
        verbose_name='対応者'
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name='優先度'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name='ステータス'
    )
    # 関連チャンネル（チャットから作成された場合）
    related_channel = models.ForeignKey(
        Channel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_logs',
        verbose_name='関連チャンネル'
    )
    # フォローアップ
    follow_up_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='フォローアップ日'
    )
    follow_up_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name='フォローアップメモ'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='解決日時'
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_contact_logs',
        verbose_name='解決者'
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='タグ'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'communication_contact_logs'
        verbose_name = '対応履歴'
        verbose_name_plural = '対応履歴'
        ordering = ['-created_at']

    def __str__(self):
        target = self.student.full_name if self.student else (
            self.guardian.full_name if self.guardian else 'Unknown'
        )
        return f"{self.get_contact_type_display()}: {target} - {self.subject}"


class ContactLogComment(models.Model):
    """対応履歴コメント"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    contact_log = models.ForeignKey(
        ContactLog,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='対応履歴'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='コメント者'
    )
    content = models.TextField(verbose_name='コメント')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_contact_log_comments'
        verbose_name = '対応履歴コメント'
        verbose_name_plural = '対応履歴コメント'
        ordering = ['created_at']


class Notification(models.Model):
    """通知"""

    class NotificationType(models.TextChoices):
        MESSAGE = 'MESSAGE', '新着メッセージ'
        MENTION = 'MENTION', 'メンション'
        LESSON_REMINDER = 'LESSON_REMINDER', '授業リマインダー'
        LESSON_CANCEL = 'LESSON_CANCEL', '授業キャンセル'
        MAKEUP_REQUEST = 'MAKEUP_REQUEST', '振替リクエスト'
        MAKEUP_APPROVED = 'MAKEUP_APPROVED', '振替承認'
        PAYMENT_DUE = 'PAYMENT_DUE', '支払い期限'
        SYSTEM = 'SYSTEM', 'システム通知'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        verbose_name='通知種別'
    )
    # 通知先
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='ユーザー'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='保護者'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='タイトル'
    )
    content = models.TextField(
        verbose_name='内容'
    )
    # リンク先
    link_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='リンク種別'
    )
    link_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name='リンクID'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='既読'
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='既読日時'
    )
    # プッシュ通知
    is_push_sent = models.BooleanField(
        default=False,
        verbose_name='プッシュ送信済み'
    )
    push_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='プッシュ送信日時'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_notifications'
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()}: {self.title}"


class BotConfig(models.Model):
    """チャットボット設定"""

    class BotType(models.TextChoices):
        FAQ = 'FAQ', 'FAQ応答'
        SCHEDULE = 'SCHEDULE', 'スケジュール確認'
        GENERAL = 'GENERAL', '一般応答'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    name = models.CharField(
        max_length=50,
        verbose_name='ボット名'
    )
    bot_type = models.CharField(
        max_length=20,
        choices=BotType.choices,
        default=BotType.GENERAL,
        verbose_name='ボット種別'
    )
    welcome_message = models.TextField(
        default='こんにちは！何かお手伝いできることはありますか？',
        verbose_name='ウェルカムメッセージ'
    )
    fallback_message = models.TextField(
        default='申し訳ございません。ご質問の内容を理解できませんでした。スタッフにお繋ぎしますか？',
        verbose_name='フォールバックメッセージ'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )
    # AI設定（OpenAI等）
    ai_enabled = models.BooleanField(
        default=False,
        verbose_name='AI応答有効'
    )
    ai_model = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='AIモデル'
    )
    ai_system_prompt = models.TextField(
        null=True,
        blank=True,
        verbose_name='AIシステムプロンプト'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'communication_bot_configs'
        verbose_name = 'ボット設定'
        verbose_name_plural = 'ボット設定'

    def __str__(self):
        return f"{self.name} ({self.get_bot_type_display()})"


class BotFAQ(models.Model):
    """ボットFAQ"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    bot_config = models.ForeignKey(
        BotConfig,
        on_delete=models.CASCADE,
        related_name='faqs',
        verbose_name='ボット設定'
    )
    category = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='カテゴリ'
    )
    question = models.TextField(
        verbose_name='質問'
    )
    # キーワード（マッチング用）
    keywords = models.JSONField(
        default=list,
        verbose_name='キーワード'
    )
    answer = models.TextField(
        verbose_name='回答'
    )
    # 次のアクション
    next_action = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='次のアクション'
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name='表示順'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'communication_bot_faqs'
        verbose_name = 'ボットFAQ'
        verbose_name_plural = 'ボットFAQ'
        ordering = ['category', 'sort_order']

    def __str__(self):
        return f"{self.question[:50]}..."


class BotConversation(models.Model):
    """ボット会話ログ"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='bot_conversations',
        verbose_name='チャンネル'
    )
    bot_config = models.ForeignKey(
        BotConfig,
        on_delete=models.SET_NULL,
        null=True,
        related_name='conversations',
        verbose_name='ボット設定'
    )
    # ユーザー入力
    user_input = models.TextField(
        verbose_name='ユーザー入力'
    )
    # ボット応答
    bot_response = models.TextField(
        verbose_name='ボット応答'
    )
    # マッチしたFAQ
    matched_faq = models.ForeignKey(
        BotFAQ,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='マッチFAQ'
    )
    # AI応答の場合
    is_ai_response = models.BooleanField(
        default=False,
        verbose_name='AI応答'
    )
    # スタッフに転送されたか
    escalated_to_staff = models.BooleanField(
        default=False,
        verbose_name='スタッフ転送'
    )
    escalated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='転送日時'
    )
    # フィードバック
    was_helpful = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='役に立った'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_bot_conversations'
        verbose_name = 'ボット会話'
        verbose_name_plural = 'ボット会話'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_input[:30]}... -> {self.bot_response[:30]}..."


class Announcement(models.Model):
    """お知らせ/一斉配信"""

    class TargetType(models.TextChoices):
        ALL = 'ALL', '全員'
        STUDENTS = 'STUDENTS', '生徒'
        GUARDIANS = 'GUARDIANS', '保護者'
        STAFF = 'STAFF', 'スタッフ'
        SCHOOL = 'SCHOOL', '校舎指定'
        GRADE = 'GRADE', '学年指定'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', '下書き'
        SCHEDULED = 'SCHEDULED', '予約'
        SENT = 'SENT', '送信済み'
        CANCELLED = 'CANCELLED', 'キャンセル'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    title = models.CharField(
        max_length=200,
        verbose_name='タイトル'
    )
    content = models.TextField(
        verbose_name='内容'
    )
    target_type = models.CharField(
        max_length=20,
        choices=TargetType.choices,
        default=TargetType.ALL,
        verbose_name='配信対象'
    )
    # 配信対象の詳細
    target_schools = models.ManyToManyField(
        'schools.School',
        blank=True,
        related_name='announcements',
        verbose_name='対象校舎'
    )
    target_grades = models.ManyToManyField(
        'schools.Grade',
        blank=True,
        related_name='announcements',
        verbose_name='対象学年'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='ステータス'
    )
    # 予約送信
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='送信予定日時'
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='送信日時'
    )
    # 送信者
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_announcements',
        verbose_name='作成者'
    )
    # 送信結果
    sent_count = models.IntegerField(
        default=0,
        verbose_name='送信数'
    )
    read_count = models.IntegerField(
        default=0,
        verbose_name='既読数'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'communication_announcements'
        verbose_name = 'お知らせ'
        verbose_name_plural = 'お知らせ'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class AnnouncementRead(models.Model):
    """お知らせ既読"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='reads',
        verbose_name='お知らせ'
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
    read_at = models.DateTimeField(auto_now_add=True, verbose_name='既読日時')

    class Meta:
        db_table = 'communication_announcement_reads'
        verbose_name = 'お知らせ既読'
        verbose_name_plural = 'お知らせ既読'
        unique_together = [['announcement', 'user'], ['announcement', 'guardian']]


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


class ChatLog(models.Model):
    """チャットログ（メッセージ送信時に自動記録）"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    # 関連メッセージ
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_logs',
        verbose_name='メッセージ'
    )
    # 校舎情報
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_logs',
        verbose_name='校舎'
    )
    school_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='校舎名（スナップショット）'
    )
    # 保護者情報
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_logs',
        verbose_name='保護者'
    )
    guardian_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='保護者名（スナップショット）'
    )
    # ブランド情報
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_logs',
        verbose_name='ブランド'
    )
    brand_name = models.CharField(
        max_length=100,
        default='その他',
        verbose_name='ブランド名（スナップショット）'
    )
    # メッセージ内容
    content = models.TextField(verbose_name='メッセージ内容')
    # 送信者タイプ
    sender_type = models.CharField(
        max_length=20,
        choices=[
            ('GUARDIAN', '保護者'),
            ('STAFF', 'スタッフ'),
            ('BOT', 'ボット'),
        ],
        verbose_name='送信者タイプ'
    )
    # タイムスタンプ
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='タイムスタンプ')

    class Meta:
        db_table = 'communication_chat_logs'
        verbose_name = 'チャットログ'
        verbose_name_plural = 'チャットログ'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant_id', '-timestamp']),
            models.Index(fields=['school', '-timestamp']),
            models.Index(fields=['guardian', '-timestamp']),
            models.Index(fields=['brand', '-timestamp']),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.brand_name} - {self.school_name} - {self.guardian_name}: {self.content[:30]}..."

    @classmethod
    def create_from_message(cls, message, tenant_id):
        """メッセージからチャットログを作成"""
        guardian = message.sender_guardian
        school = None
        brand = None
        brand_name = 'その他'
        school_name = None
        guardian_name = None
        sender_type = 'STAFF'

        # 送信者タイプを判定
        if message.is_bot_message:
            sender_type = 'BOT'
        elif guardian:
            sender_type = 'GUARDIAN'
            guardian_name = guardian.full_name

            # 保護者から校舎・ブランド情報を取得
            # 保護者の生徒から校舎を取得
            students = guardian.students.all()
            if students.exists():
                student = students.first()
                # 生徒のコースから校舎を取得
                contracts = student.contracts.filter(is_active=True).select_related('school', 'brand')
                if contracts.exists():
                    contract = contracts.first()
                    school = contract.school
                    brand = contract.brand
                    if school:
                        school_name = school.school_name
                    if brand:
                        brand_name = brand.brand_name

        # チャンネルから校舎情報を取得（保護者から取得できなかった場合）
        if not school and message.channel and message.channel.school:
            school = message.channel.school
            school_name = school.school_name

        return cls.objects.create(
            tenant_id=tenant_id,
            message=message,
            school=school,
            school_name=school_name,
            guardian=guardian,
            guardian_name=guardian_name,
            brand=brand,
            brand_name=brand_name,
            content=message.content,
            sender_type=sender_type,
        )

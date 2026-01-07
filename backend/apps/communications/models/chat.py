"""
Chat Models - チャット関連
Channel, ChannelMember, Message, MessageRead
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
    is_pinned = models.BooleanField(
        default=False,
        verbose_name='ピン留め'
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


class MessageReaction(models.Model):
    """メッセージリアクション（絵文字）"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reactions',
        verbose_name='メッセージ'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_reactions',
        verbose_name='ユーザー'
    )
    emoji = models.CharField(
        max_length=10,
        verbose_name='絵文字'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_message_reactions'
        verbose_name = 'メッセージリアクション'
        verbose_name_plural = 'メッセージリアクション'
        unique_together = [['message', 'user', 'emoji']]
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.email} - {self.emoji} on {self.message_id}"


class MessageMention(models.Model):
    """メッセージ内のメンション"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='mentions',
        verbose_name='メッセージ'
    )
    mentioned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_mentions',
        verbose_name='メンションされたユーザー'
    )
    # メンションの開始位置（表示用）
    start_index = models.IntegerField(
        default=0,
        verbose_name='開始位置'
    )
    # メンションの終了位置（表示用）
    end_index = models.IntegerField(
        default=0,
        verbose_name='終了位置'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_message_mentions'
        verbose_name = 'メッセージメンション'
        verbose_name_plural = 'メッセージメンション'
        unique_together = [['message', 'mentioned_user']]
        ordering = ['start_index']

    def __str__(self):
        return f"@{self.mentioned_user.email} in {self.message_id}"

"""
Notification Model - 通知
"""
import uuid
from django.db import models
from django.conf import settings


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

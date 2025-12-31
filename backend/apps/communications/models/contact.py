"""
Contact Log Models - 対応履歴/CRM
ContactLog, ContactLogComment
"""
import uuid
from django.db import models
from django.conf import settings

from .chat import Channel


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

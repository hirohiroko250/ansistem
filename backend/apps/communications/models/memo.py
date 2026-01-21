"""
Memo Models - 伝言メモ・TEL登録メモ
"""
import uuid
from django.db import models
from django.conf import settings


class MessageMemo(models.Model):
    """伝言メモ - スタッフ間で共有する生徒に関するメモ"""

    class Priority(models.TextChoices):
        LOW = 'low', '低'
        NORMAL = 'normal', '通常'
        HIGH = 'high', '高'
        URGENT = 'urgent', '緊急'

    class Status(models.TextChoices):
        PENDING = 'pending', '未対応'
        COMPLETED = 'completed', '完了'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True, null=True, blank=True)

    # 対象生徒
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='message_memos',
        verbose_name='生徒'
    )

    # メモ内容
    content = models.TextField(verbose_name='内容')
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
        verbose_name='優先度'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='状態'
    )

    # 作成者・完了者
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_message_memos',
        verbose_name='作成者'
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_message_memos',
        verbose_name='完了者'
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完了日時')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'communications_message_memo'
        verbose_name = '伝言メモ'
        verbose_name_plural = '伝言メモ'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.full_name} - {self.content[:30]}"


class TelMemo(models.Model):
    """TEL登録メモ - 電話対応の記録"""

    class CallDirection(models.TextChoices):
        INCOMING = 'incoming', '着信'
        OUTGOING = 'outgoing', '発信'

    class CallResult(models.TextChoices):
        CONNECTED = 'connected', '通話'
        NO_ANSWER = 'no_answer', '不在'
        BUSY = 'busy', '話し中'
        VOICEMAIL = 'voicemail', '留守電'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True, null=True, blank=True)

    # 対象生徒
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='tel_memos',
        verbose_name='生徒'
    )

    # 電話情報
    phone_number = models.CharField(max_length=20, blank=True, verbose_name='電話番号')
    call_direction = models.CharField(
        max_length=20,
        choices=CallDirection.choices,
        default=CallDirection.INCOMING,
        verbose_name='発信/着信'
    )
    call_result = models.CharField(
        max_length=20,
        choices=CallResult.choices,
        default=CallResult.CONNECTED,
        verbose_name='通話結果'
    )

    # メモ内容
    content = models.TextField(blank=True, verbose_name='内容')

    # 作成者
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tel_memos',
        verbose_name='作成者'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'communications_tel_memo'
        verbose_name = 'TEL登録メモ'
        verbose_name_plural = 'TEL登録メモ'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.full_name} - {self.call_direction} - {self.created_at}"

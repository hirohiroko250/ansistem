"""
Announcement Models - お知らせ/一斉配信
Announcement, AnnouncementRead
"""
import uuid
from django.db import models
from django.conf import settings


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

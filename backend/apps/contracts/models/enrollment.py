"""
Enrollment Models - 申込関連
T55: 講習申込 (SeminarEnrollment)
T56: 検定申込 (CertificationEnrollment)
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class SeminarEnrollment(TenantModel):
    """T55: 講習申込"""

    class Status(models.TextChoices):
        APPLIED = 'applied', '申込済'
        CONFIRMED = 'confirmed', '確定'
        CANCELLED = 'cancelled', 'キャンセル'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='seminar_enrollments',
        verbose_name='生徒'
    )
    seminar = models.ForeignKey(
        'contracts.Seminar',
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name='講習'
    )

    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED
    )
    applied_at = models.DateTimeField('申込日時', auto_now_add=True)

    unit_price = models.DecimalField('単価', max_digits=10, decimal_places=0)
    discount_amount = models.DecimalField('割引額', max_digits=10, decimal_places=0, default=0)
    final_price = models.DecimalField('確定金額', max_digits=10, decimal_places=0)

    billing_month = models.CharField(
        '請求月',
        max_length=7,
        null=True,
        blank=True,
        help_text='請求対象月（YYYY-MM形式）'
    )

    is_required = models.BooleanField('必須講習', default=False)
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't55_seminar_enrollments'
        verbose_name = 'T55_講習申込'
        verbose_name_plural = 'T55_講習申込'
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.student} - {self.seminar}"


class CertificationEnrollment(TenantModel):
    """T56: 検定申込"""

    class Status(models.TextChoices):
        APPLIED = 'applied', '申込済'
        CONFIRMED = 'confirmed', '確定'
        CANCELLED = 'cancelled', 'キャンセル'
        PASSED = 'passed', '合格'
        FAILED = 'failed', '不合格'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='certification_enrollments',
        verbose_name='生徒'
    )
    certification = models.ForeignKey(
        'contracts.Certification',
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name='検定'
    )

    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED
    )
    applied_at = models.DateTimeField('申込日時', auto_now_add=True)

    exam_fee = models.DecimalField('検定料', max_digits=10, decimal_places=0)
    discount_amount = models.DecimalField('割引額', max_digits=10, decimal_places=0, default=0)
    final_price = models.DecimalField('確定金額', max_digits=10, decimal_places=0)

    billing_month = models.CharField(
        '請求月',
        max_length=7,
        null=True,
        blank=True,
        help_text='請求対象月（YYYY-MM形式）'
    )

    score = models.IntegerField('スコア', null=True, blank=True)
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't56_certification_enrollments'
        verbose_name = 'T56_検定申込'
        verbose_name_plural = 'T56_検定申込'
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.student} - {self.certification}"

"""
ContractChangeRequest Model - 契約変更申請
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class ContractChangeRequest(TenantModel):
    """契約変更申請

    休会申請・退会申請を保護者が行うためのモデル
    """

    class RequestType(models.TextChoices):
        CLASS_CHANGE = 'class_change', 'クラス変更'
        SCHOOL_CHANGE = 'school_change', '校舎変更'
        SUSPENSION = 'suspension', '休会申請'
        CANCELLATION = 'cancellation', '退会申請'

    class Status(models.TextChoices):
        PENDING = 'pending', '申請中'
        APPROVED = 'approved', '承認済'
        REJECTED = 'rejected', '却下'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        related_name='change_requests',
        verbose_name='契約'
    )

    request_type = models.CharField(
        '申請種別',
        max_length=20,
        choices=RequestType.choices
    )

    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # クラス/校舎変更用
    new_school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_requests',
        verbose_name='新校舎'
    )
    new_day_of_week = models.IntegerField('新曜日', null=True, blank=True)
    new_start_time = models.TimeField('新開始時間', null=True, blank=True)
    new_class_schedule = models.ForeignKey(
        'schools.ClassSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_requests',
        verbose_name='新クラススケジュール'
    )
    effective_date = models.DateField('適用日', null=True, blank=True)

    # 休会用
    suspend_from = models.DateField('休会開始日', null=True, blank=True)
    suspend_until = models.DateField('休会終了日', null=True, blank=True)
    keep_seat = models.BooleanField('座席保持', default=False)

    # 退会用
    cancel_date = models.DateField('退会日', null=True, blank=True)
    refund_amount = models.DecimalField(
        '相殺金額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )

    reason = models.TextField('理由', blank=True)

    # 申請者情報
    requested_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='contract_change_requests',
        verbose_name='申請者'
    )
    requested_at = models.DateTimeField('申請日時', auto_now_add=True)

    # 処理者情報
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_contract_requests',
        verbose_name='処理者'
    )
    processed_at = models.DateTimeField('処理日時', null=True, blank=True)
    process_notes = models.TextField('処理メモ', blank=True)

    class Meta:
        db_table = 'contract_change_requests'
        verbose_name = '契約変更申請'
        verbose_name_plural = '契約変更申請'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.contract} - {self.get_request_type_display()} ({self.get_status_display()})"

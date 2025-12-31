"""
Refund Models - 返金申請
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class RefundRequest(TenantModel):
    """返金申請

    退会時の返金や過払い返金の申請・承認ワークフロー
    """

    class Status(models.TextChoices):
        PENDING = 'pending', '申請中'
        APPROVED = 'approved', '承認済'
        PROCESSING = 'processing', '処理中'
        COMPLETED = 'completed', '完了'
        REJECTED = 'rejected', '却下'
        CANCELLED = 'cancelled', '取消'

    class RefundMethod(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', '銀行振込'
        CASH = 'cash', '現金'
        OFFSET_NEXT = 'offset_next', '次回相殺'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_no = models.CharField('申請番号', max_length=30)

    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        related_name='refund_requests',
        verbose_name='保護者'
    )

    # 関連請求書
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='refund_requests',
        verbose_name='請求書'
    )

    # 返金情報
    refund_amount = models.DecimalField('返金額', max_digits=12, decimal_places=0)
    refund_method = models.CharField(
        '返金方法',
        max_length=20,
        choices=RefundMethod.choices,
        default=RefundMethod.BANK_TRANSFER
    )

    reason = models.TextField('返金理由')

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 申請者
    requested_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='refund_requests',
        verbose_name='申請者'
    )
    requested_at = models.DateTimeField('申請日時', auto_now_add=True)

    # 承認者
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_refund_requests',
        verbose_name='承認者'
    )
    approved_at = models.DateTimeField('承認日時', null=True, blank=True)

    # 処理情報
    processed_at = models.DateTimeField('処理日時', null=True, blank=True)
    process_notes = models.TextField('処理メモ', blank=True)

    class Meta:
        db_table = 'billing_refund_requests'
        verbose_name = '返金申請'
        verbose_name_plural = '返金申請'
        ordering = ['-requested_at']
        unique_together = ['tenant_id', 'request_no']

    def __str__(self):
        return f"{self.request_no} - {self.guardian} ({self.refund_amount}円)"

    def approve(self, user):
        """承認"""
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

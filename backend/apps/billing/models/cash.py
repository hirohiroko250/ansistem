"""
Cash Models - 現金管理
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class CashManagement(TenantModel):
    """現金管理

    現金での支払い・返金を管理するためのテーブル。
    現金の入出金状況を追跡する。
    """

    class TransactionType(models.TextChoices):
        PAYMENT = 'payment', '入金'
        REFUND = 'refund', '返金'
        ADJUSTMENT = 'adjustment', '調整'

    class Status(models.TextChoices):
        PENDING = 'pending', '未処理'
        COMPLETED = 'completed', '完了'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 保護者
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        related_name='cash_transactions',
        verbose_name='保護者'
    )

    # 関連請求書
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cash_transactions',
        verbose_name='請求書'
    )

    # 取引情報
    transaction_date = models.DateField('取引日')
    amount = models.DecimalField('金額', max_digits=12, decimal_places=0)
    transaction_type = models.CharField(
        '取引種別',
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.PAYMENT
    )

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 受領者情報
    received_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='received_cash_transactions',
        verbose_name='受領者'
    )
    received_at = models.DateTimeField('受領日時', null=True, blank=True)

    # 領収書情報
    receipt_no = models.CharField('領収書番号', max_length=30, blank=True)
    receipt_issued = models.BooleanField('領収書発行済', default=False)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_cash_management'
        verbose_name = '現金管理'
        verbose_name_plural = '現金管理'
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['guardian', 'transaction_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.guardian} - {self.transaction_date} {self.get_transaction_type_display()} {self.amount}円"

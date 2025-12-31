"""
Payment Models - 入金・引落結果
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class Payment(TenantModel):
    """入金記録

    自動引き落とし、振込、現金などの入金を記録
    """

    class Method(models.TextChoices):
        DIRECT_DEBIT = 'direct_debit', '口座振替'
        BANK_TRANSFER = 'bank_transfer', '銀行振込'
        CASH = 'cash', '現金'
        CREDIT_CARD = 'credit_card', 'クレジットカード'
        OFFSET = 'offset', '相殺'
        OTHER = 'other', 'その他'

    class Status(models.TextChoices):
        PENDING = 'pending', '処理中'
        SUCCESS = 'success', '成功'
        FAILED = 'failed', '失敗'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_no = models.CharField('入金番号', max_length=30)

    # 入金者
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name='保護者'
    )

    # 対象請求書 (任意)
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payments',
        verbose_name='請求書'
    )

    # 入金情報
    payment_date = models.DateField('入金日')
    amount = models.DecimalField('入金額', max_digits=12, decimal_places=0)

    # 入金方法
    method = models.CharField(
        '入金方法',
        max_length=20,
        choices=Method.choices,
        default=Method.DIRECT_DEBIT
    )

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 口座振替結果
    debit_result_code = models.CharField('振替結果コード', max_length=10, blank=True)
    debit_result_message = models.CharField('振替結果メッセージ', max_length=200, blank=True)

    # 銀行振込情報
    payer_name = models.CharField('振込人名義', max_length=100, blank=True)
    bank_name = models.CharField('振込元銀行', max_length=100, blank=True)

    notes = models.TextField('備考', blank=True)

    # 登録者
    registered_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='registered_payments',
        verbose_name='登録者'
    )

    class Meta:
        db_table = 'billing_payments'
        verbose_name = '入金'
        verbose_name_plural = '入金'
        ordering = ['-payment_date']
        unique_together = ['tenant_id', 'payment_no']

    def __str__(self):
        return f"{self.payment_no} - {self.guardian} ({self.amount}円)"

    @classmethod
    def generate_payment_no(cls, tenant_id):
        """入金番号を自動生成"""
        today = timezone.now()
        prefix = f"PAY-{today.strftime('%Y%m%d')}-"
        last = cls.objects.filter(
            tenant_id=tenant_id,
            payment_no__startswith=prefix
        ).order_by('-payment_no').first()

        if last:
            last_num = int(last.payment_no.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{prefix}{new_num:04d}"

    def apply_to_invoice(self):
        """請求書に入金を適用"""
        from .invoice import Invoice
        if self.invoice and self.status == self.Status.SUCCESS:
            self.invoice.paid_amount += self.amount
            self.invoice.balance_due = self.invoice.total_amount - self.invoice.paid_amount

            if self.invoice.balance_due <= 0:
                self.invoice.status = Invoice.Status.PAID
            elif self.invoice.paid_amount > 0:
                self.invoice.status = Invoice.Status.PARTIAL

            self.invoice.save()


class DirectDebitResult(TenantModel):
    """引落結果

    自動引き落としの結果を記録するテーブル。
    引き落としの成否や理由を管理し、請求と入金の整合性を保つ。
    """

    class ResultStatus(models.TextChoices):
        SUCCESS = 'success', '成功'
        FAILED = 'failed', '失敗'
        PENDING = 'pending', '処理中'
        CANCELLED = 'cancelled', '取消'

    class FailureReason(models.TextChoices):
        INSUFFICIENT_FUNDS = 'insufficient_funds', '残高不足'
        ACCOUNT_CLOSED = 'account_closed', '口座解約'
        ACCOUNT_NOT_FOUND = 'account_not_found', '口座なし'
        INVALID_ACCOUNT = 'invalid_account', '口座相違'
        REJECTED = 'rejected', '振替拒否'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 保護者
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        related_name='direct_debit_results',
        verbose_name='保護者'
    )

    # 関連請求書
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='direct_debit_results',
        verbose_name='請求書'
    )

    # 引落情報
    debit_date = models.DateField('引落日')
    amount = models.DecimalField('引落金額', max_digits=12, decimal_places=0)

    # 結果
    result_status = models.CharField(
        '結果ステータス',
        max_length=20,
        choices=ResultStatus.choices,
        default=ResultStatus.PENDING
    )
    failure_reason = models.CharField(
        '失敗理由',
        max_length=30,
        choices=FailureReason.choices,
        blank=True
    )
    failure_detail = models.TextField('失敗詳細', blank=True)

    # 通知フラグ
    notice_flag = models.BooleanField('通知済', default=False)
    notice_date = models.DateTimeField('通知日時', null=True, blank=True)

    # 再引落情報
    retry_count = models.IntegerField('再引落回数', default=0)
    next_retry_date = models.DateField('次回再引落日', null=True, blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_direct_debit_results'
        verbose_name = '引落結果'
        verbose_name_plural = '引落結果'
        ordering = ['-debit_date']
        indexes = [
            models.Index(fields=['guardian', 'debit_date']),
            models.Index(fields=['result_status']),
        ]

    def __str__(self):
        return f"{self.guardian} - {self.debit_date} ({self.get_result_status_display()})"

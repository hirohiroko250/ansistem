"""
Debit Export Models - 引落データエクスポート
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class DebitExportBatch(TenantModel):
    """引落データエクスポートバッチ

    決済代行会社へ送信する引落データのバッチを管理。
    エクスポート日時、件数、金額などを記録する。
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', '作成中'
        EXPORTED = 'exported', 'エクスポート済'
        RESULT_IMPORTED = 'result_imported', '結果取込済'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # バッチ番号
    batch_no = models.CharField('バッチ番号', max_length=30)

    # 決済代行会社
    provider = models.ForeignKey(
        'billing.PaymentProvider',
        on_delete=models.CASCADE,
        related_name='export_batches',
        verbose_name='決済代行会社'
    )

    # 請求期間
    billing_period = models.ForeignKey(
        'billing.BillingPeriod',
        on_delete=models.CASCADE,
        related_name='export_batches',
        verbose_name='請求期間'
    )

    # エクスポート情報
    export_date = models.DateTimeField('エクスポート日時', null=True, blank=True)
    exported_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='exported_debit_batches',
        verbose_name='エクスポート実行者'
    )

    # 集計情報
    total_count = models.IntegerField('総件数', default=0)
    total_amount = models.DecimalField('総金額', max_digits=14, decimal_places=0, default=0)

    # 結果集計（結果取込後）
    success_count = models.IntegerField('成功件数', default=0)
    success_amount = models.DecimalField('成功金額', max_digits=14, decimal_places=0, default=0)
    failed_count = models.IntegerField('失敗件数', default=0)
    failed_amount = models.DecimalField('失敗金額', max_digits=14, decimal_places=0, default=0)

    # 結果取込情報
    result_imported_at = models.DateTimeField('結果取込日時', null=True, blank=True)
    result_imported_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='imported_debit_batches',
        verbose_name='結果取込実行者'
    )

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_debit_export_batches'
        verbose_name = '引落エクスポートバッチ'
        verbose_name_plural = '引落エクスポートバッチ'
        ordering = ['-created_at']
        unique_together = ['tenant_id', 'batch_no']

    def __str__(self):
        return f"{self.batch_no} - {self.provider.name} ({self.get_status_display()})"

    @classmethod
    def generate_batch_no(cls, tenant_id, provider_code):
        """バッチ番号を自動生成 (例: UFJ-20251213-0001)"""
        today = timezone.now()
        prefix = f"{provider_code.upper()[:3]}-{today.strftime('%Y%m%d')}-"
        last = cls.objects.filter(
            tenant_id=tenant_id,
            batch_no__startswith=prefix
        ).order_by('-batch_no').first()

        if last:
            last_num = int(last.batch_no.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{prefix}{new_num:04d}"


class DebitExportLine(TenantModel):
    """引落データエクスポート明細

    エクスポートバッチの各明細行を管理。
    口座情報、金額、結果コードなどを記録する。
    """

    class ResultStatus(models.TextChoices):
        PENDING = 'pending', '未処理'
        SUCCESS = 'success', '成功'
        FAILED = 'failed', '失敗'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # バッチ
    batch = models.ForeignKey(
        DebitExportBatch,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name='バッチ'
    )

    # 行番号
    line_no = models.IntegerField('行番号')

    # 保護者・請求書
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        related_name='debit_export_lines',
        verbose_name='保護者'
    )
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='debit_export_lines',
        verbose_name='請求書'
    )

    # エクスポートデータ（口座情報）
    bank_code = models.CharField('銀行コード', max_length=4)
    branch_code = models.CharField('支店コード', max_length=3)
    account_type = models.CharField(
        '預金種目',
        max_length=1,
        help_text='1:普通, 2:当座'
    )
    account_number = models.CharField('口座番号', max_length=8)
    account_holder_kana = models.CharField('口座名義（カナ）', max_length=100)
    amount = models.DecimalField('引落金額', max_digits=12, decimal_places=0)
    customer_code = models.CharField(
        '顧客番号',
        max_length=20,
        help_text='保護者番号など識別用コード'
    )

    # 結果データ（インポート後）
    result_code = models.CharField('結果コード', max_length=10, blank=True)
    result_status = models.CharField(
        '結果ステータス',
        max_length=20,
        choices=ResultStatus.choices,
        default=ResultStatus.PENDING
    )
    result_message = models.CharField('結果メッセージ', max_length=200, blank=True)

    # DirectDebitResultとの紐付け
    direct_debit_result = models.ForeignKey(
        'billing.DirectDebitResult',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='export_lines',
        verbose_name='引落結果'
    )

    # Paymentとの紐付け（成功時）
    payment = models.ForeignKey(
        'billing.Payment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='export_lines',
        verbose_name='入金'
    )

    class Meta:
        db_table = 'billing_debit_export_lines'
        verbose_name = '引落エクスポート明細'
        verbose_name_plural = '引落エクスポート明細'
        ordering = ['batch', 'line_no']
        indexes = [
            models.Index(fields=['batch', 'line_no']),
            models.Index(fields=['guardian']),
            models.Index(fields=['result_status']),
        ]

    def __str__(self):
        return f"{self.batch.batch_no} - {self.line_no}: {self.guardian} ({self.amount}円)"

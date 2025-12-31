"""
Bank Transfer Models - 振込入金・インポート
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class BankTransfer(TenantModel):
    """振込入金

    銀行振込による入金を記録するテーブル。
    振込日・金額・振込人名義・入金ステータスなどを保存する。
    """

    class Status(models.TextChoices):
        PENDING = 'pending', '確認中'
        MATCHED = 'matched', '照合済'
        APPLIED = 'applied', '入金適用済'
        UNMATCHED = 'unmatched', '不明入金'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 保護者 (照合後に設定)
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='bank_transfers',
        verbose_name='保護者'
    )

    # 関連請求書 (入金適用後に設定)
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bank_transfers',
        verbose_name='請求書'
    )

    # 振込情報
    transfer_date = models.DateField('振込日')
    amount = models.DecimalField('振込金額', max_digits=12, decimal_places=0)
    payer_name = models.CharField('振込人名義', max_length=100)
    payer_name_kana = models.CharField('振込人名義（カナ）', max_length=100, blank=True)
    guardian_no_hint = models.CharField('保護者番号（抽出）', max_length=20, blank=True, help_text='振込人名義から抽出したID番号')

    # 振込元情報
    source_bank_name = models.CharField('振込元銀行', max_length=100, blank=True)
    source_branch_name = models.CharField('振込元支店', max_length=100, blank=True)

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 照合情報
    matched_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='matched_bank_transfers',
        verbose_name='照合者'
    )
    matched_at = models.DateTimeField('照合日時', null=True, blank=True)

    # インポート情報
    import_batch_id = models.CharField('インポートバッチID', max_length=50, blank=True)
    import_row_no = models.IntegerField('インポート行番号', null=True, blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_bank_transfers'
        verbose_name = '振込入金'
        verbose_name_plural = '振込入金'
        ordering = ['-transfer_date']
        indexes = [
            models.Index(fields=['transfer_date']),
            models.Index(fields=['payer_name']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.payer_name} - {self.transfer_date} {self.amount}円"

    def match_to_guardian(self, guardian, user):
        """保護者と照合"""
        self.guardian = guardian
        self.status = self.Status.MATCHED
        self.matched_by = user
        self.matched_at = timezone.now()
        self.save()

    def apply_to_invoice(self, invoice, user):
        """請求書に入金を適用"""
        self.invoice = invoice
        self.status = self.Status.APPLIED
        if not self.matched_at:
            self.matched_by = user
            self.matched_at = timezone.now()
        self.save()


class BankTransferImport(TenantModel):
    """振込データインポートバッチ

    CSVやExcelファイルから振込データをインポートするバッチ。
    インポート後、自動照合を行い、保護者との紐付けを試みる。
    """

    class Status(models.TextChoices):
        PENDING = 'pending', '処理中'
        COMPLETED = 'completed', '完了'
        PARTIAL = 'partial', '一部照合済'
        FAILED = 'failed', '失敗'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_no = models.CharField('バッチ番号', max_length=30)

    # ファイル情報
    file_name = models.CharField('ファイル名', max_length=200)
    file_type = models.CharField('ファイル形式', max_length=20, default='csv')

    # インポート結果サマリ
    total_count = models.IntegerField('総件数', default=0)
    matched_count = models.IntegerField('照合済件数', default=0)
    unmatched_count = models.IntegerField('未照合件数', default=0)
    error_count = models.IntegerField('エラー件数', default=0)
    total_amount = models.DecimalField('総金額', max_digits=14, decimal_places=0, default=0)

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 実行者
    imported_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bank_transfer_imports',
        verbose_name='インポート実行者'
    )
    imported_at = models.DateTimeField('インポート日時', auto_now_add=True)

    # 確定情報
    confirmed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmed_bank_transfer_imports',
        verbose_name='確定実行者'
    )
    confirmed_at = models.DateTimeField('確定日時', null=True, blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_bank_transfer_imports'
        verbose_name = '振込インポートバッチ'
        verbose_name_plural = '振込インポートバッチ'
        ordering = ['-imported_at']
        indexes = [
            models.Index(fields=['batch_no']),
            models.Index(fields=['status']),
            models.Index(fields=['-imported_at']),
        ]

    def __str__(self):
        return f"{self.batch_no} - {self.file_name} ({self.total_count}件)"

    def save(self, *args, **kwargs):
        if not self.batch_no:
            self.batch_no = f"BTI-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)

    def update_counts(self):
        """照合状況を再集計"""
        from django.db.models import Sum
        transfers = BankTransfer.objects.filter(import_batch_id=str(self.id))
        self.total_count = transfers.count()
        self.matched_count = transfers.filter(status__in=[BankTransfer.Status.MATCHED, BankTransfer.Status.APPLIED]).count()
        self.unmatched_count = transfers.filter(status=BankTransfer.Status.UNMATCHED).count() + transfers.filter(status=BankTransfer.Status.PENDING).count()
        self.error_count = transfers.filter(status=BankTransfer.Status.CANCELLED).count()
        total = transfers.aggregate(Sum('amount'))['amount__sum']
        self.total_amount = total or 0

        # ステータス更新
        if self.matched_count == self.total_count and self.total_count > 0:
            self.status = self.Status.COMPLETED
        elif self.matched_count > 0:
            self.status = self.Status.PARTIAL
        else:
            self.status = self.Status.PENDING

        self.save()

    def confirm(self, user):
        """インポートを確定（照合済みの振込を入金処理）"""
        self.confirmed_by = user
        self.confirmed_at = timezone.now()
        self.save()

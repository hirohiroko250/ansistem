"""
Invoice Models - 請求書
"""
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class Invoice(TenantModel):
    """請求書

    保護者単位で月次請求書を作成。
    状態遷移: draft → issued → paid / overdue / cancelled
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', '下書き'
        ISSUED = 'issued', '発行済'
        PAID = 'paid', '支払済'
        PARTIAL = 'partial', '一部入金'
        OVERDUE = 'overdue', '滞納'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_no = models.CharField('請求番号', max_length=30)

    # 請求先
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name='保護者'
    )

    # 請求対象月
    billing_year = models.IntegerField('請求年')
    billing_month = models.IntegerField('請求月')

    # 日付
    issue_date = models.DateField('発行日', null=True, blank=True)
    due_date = models.DateField('支払期限', null=True, blank=True)

    # 金額サマリ
    subtotal = models.DecimalField('小計', max_digits=12, decimal_places=0, default=0)
    tax_amount = models.DecimalField('消費税', max_digits=12, decimal_places=0, default=0)
    discount_total = models.DecimalField('割引合計', max_digits=12, decimal_places=0, default=0)
    miles_used = models.IntegerField('使用マイル', default=0)
    miles_discount = models.DecimalField('マイル割引額', max_digits=12, decimal_places=0, default=0)
    total_amount = models.DecimalField('請求合計', max_digits=12, decimal_places=0, default=0)

    # 入金情報
    paid_amount = models.DecimalField('入金済額', max_digits=12, decimal_places=0, default=0)
    balance_due = models.DecimalField('未払額', max_digits=12, decimal_places=0, default=0)

    # 繰越
    carry_over_amount = models.DecimalField(
        '繰越額',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='前月からの繰越額（プラス=未払い繰越、マイナス=過払い繰越）'
    )

    # 支払方法
    class PaymentMethod(models.TextChoices):
        DIRECT_DEBIT = 'direct_debit', '口座引落'
        BANK_TRANSFER = 'bank_transfer', '振込'
        CREDIT_CARD = 'credit_card', 'クレジットカード'
        CASH = 'cash', '現金'
        OTHER = 'other', 'その他'

    payment_method = models.CharField(
        '支払方法',
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.DIRECT_DEBIT
    )

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # 確定情報
    confirmed_at = models.DateTimeField('確定日時', null=True, blank=True)
    confirmed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmed_invoices',
        verbose_name='確定者'
    )

    # 引落データエクスポート・ロック情報
    is_locked = models.BooleanField('編集ロック', default=False, help_text='エクスポート済みで編集不可')
    locked_at = models.DateTimeField('ロック日時', null=True, blank=True)
    locked_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='locked_invoices',
        verbose_name='ロック実行者'
    )
    export_batch_no = models.CharField('エクスポートバッチ番号', max_length=50, blank=True, help_text='引落データ出力時のバッチ番号')

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_invoices'
        verbose_name = '請求書'
        verbose_name_plural = '請求書'
        ordering = ['-billing_year', '-billing_month']
        unique_together = ['tenant_id', 'invoice_no']
        indexes = [
            models.Index(fields=['guardian', 'billing_year', 'billing_month']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.invoice_no} - {self.guardian} ({self.billing_year}/{self.billing_month:02d})"

    @classmethod
    def generate_invoice_no(cls, tenant_id, billing_year, billing_month):
        """請求番号を自動生成 (例: INV-202504-0001)"""
        prefix = f"INV-{billing_year}{billing_month:02d}-"
        last = cls.objects.filter(
            tenant_id=tenant_id,
            invoice_no__startswith=prefix
        ).order_by('-invoice_no').first()

        if last:
            last_num = int(last.invoice_no.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{prefix}{new_num:04d}"

    def calculate_totals(self):
        """明細から合計を再計算"""
        lines = self.lines.all()
        self.subtotal = sum(line.line_total for line in lines)
        self.tax_amount = sum(line.tax_amount for line in lines)
        self.discount_total = sum(line.discount_amount for line in lines)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_total - self.miles_discount
        self.balance_due = self.total_amount - self.paid_amount

    def confirm(self, user):
        """請求を確定"""
        self.status = self.Status.ISSUED
        self.confirmed_at = timezone.now()
        self.confirmed_by = user
        self.issue_date = timezone.now().date()
        self.save()


class InvoiceLine(TenantModel):
    """請求明細行

    各生徒の商品・サービスごとの明細
    """

    class TaxCategory(models.TextChoices):
        TAXABLE_10 = 'tax_10', '課税10%'
        TAXABLE_8 = 'tax_8', '軽減税率8%'
        EXEMPT = 'exempt', '非課税'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name='請求書'
    )

    # 対象生徒
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='invoice_lines',
        verbose_name='生徒'
    )

    # 商品情報
    student_item = models.ForeignKey(
        'contracts.StudentItem',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoice_lines',
        verbose_name='生徒商品'
    )
    product = models.ForeignKey(
        'contracts.Product',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoice_lines',
        verbose_name='商品'
    )

    # 明細内容
    item_name = models.CharField('項目名', max_length=200)
    item_type = models.CharField('項目種別', max_length=30, blank=True)
    description = models.TextField('説明', blank=True)

    # 対象期間
    period_start = models.DateField('対象開始日', null=True, blank=True)
    period_end = models.DateField('対象終了日', null=True, blank=True)

    # 金額
    quantity = models.IntegerField('数量', default=1)
    unit_price = models.DecimalField('単価', max_digits=10, decimal_places=0, default=0)
    line_total = models.DecimalField('小計', max_digits=10, decimal_places=0, default=0)

    # 税
    tax_category = models.CharField(
        '税区分',
        max_length=10,
        choices=TaxCategory.choices,
        default=TaxCategory.TAXABLE_10
    )
    tax_rate = models.DecimalField('税率', max_digits=5, decimal_places=2, default=Decimal('0.10'))
    tax_amount = models.DecimalField('税額', max_digits=10, decimal_places=0, default=0)

    # 割引
    discount_amount = models.DecimalField('割引額', max_digits=10, decimal_places=0, default=0)
    discount_reason = models.CharField('割引理由', max_length=100, blank=True)

    # 割引按分 (他社負担)
    company_discount = models.DecimalField('会社負担割引', max_digits=10, decimal_places=0, default=0)
    partner_discount = models.DecimalField('他社負担割引', max_digits=10, decimal_places=0, default=0)

    sort_order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'billing_invoice_lines'
        verbose_name = '請求明細'
        verbose_name_plural = '請求明細'
        ordering = ['invoice', 'sort_order']

    def __str__(self):
        return f"{self.invoice.invoice_no} - {self.item_name}"

    def calculate(self):
        """金額を計算"""
        self.line_total = self.unit_price * self.quantity
        if self.tax_category == self.TaxCategory.EXEMPT:
            self.tax_amount = Decimal('0')
        else:
            self.tax_amount = (self.line_total - self.discount_amount) * self.tax_rate

"""
Billing Models - 請求・入金・預り金・マイル管理

テーブル:
- Invoice (請求書ヘッダ)
- InvoiceLine (請求明細)
- Payment (入金)
- GuardianBalance (預り金残高)
- OffsetLog (相殺ログ)
- RefundRequest (返金申請)
- MileTransaction (マイル取引)
- DirectDebitResult (引落結果)
- CashManagement (現金管理)
- BankTransfer (振込入金)
"""
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


# =============================================================================
# Invoice (請求書ヘッダ)
# =============================================================================
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


# =============================================================================
# InvoiceLine (請求明細)
# =============================================================================
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
    # TODO: StudentItemとの紐付けを検討
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


# =============================================================================
# Payment (入金)
# =============================================================================
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
        Invoice,
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
        if self.invoice and self.status == self.Status.SUCCESS:
            self.invoice.paid_amount += self.amount
            self.invoice.balance_due = self.invoice.total_amount - self.invoice.paid_amount

            if self.invoice.balance_due <= 0:
                self.invoice.status = Invoice.Status.PAID
            elif self.invoice.paid_amount > 0:
                self.invoice.status = Invoice.Status.PARTIAL

            self.invoice.save()


# =============================================================================
# GuardianBalance (預り金残高)
# =============================================================================
class GuardianBalance(TenantModel):
    """保護者預り金残高

    1保護者に1レコード。入金・相殺時に残高を更新。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    guardian = models.OneToOneField(
        'students.Guardian',
        on_delete=models.CASCADE,
        related_name='balance',
        verbose_name='保護者'
    )

    balance = models.DecimalField('残高', max_digits=12, decimal_places=0, default=0)
    last_updated = models.DateTimeField('最終更新日時', auto_now=True)

    notes = models.TextField('メモ', blank=True)

    class Meta:
        db_table = 'billing_guardian_balances'
        verbose_name = '預り金残高'
        verbose_name_plural = '預り金残高'

    def __str__(self):
        return f"{self.guardian} - {self.balance}円"

    def add_balance(self, amount, reason=''):
        """残高を追加"""
        self.balance += amount
        self.save()

        # ログ記録
        OffsetLog.objects.create(
            tenant_id=self.tenant_id,
            guardian=self.guardian,
            transaction_type=OffsetLog.TransactionType.DEPOSIT,
            amount=amount,
            balance_after=self.balance,
            reason=reason,
        )

    def use_balance(self, amount, invoice=None, reason=''):
        """残高を使用 (相殺)"""
        if amount > self.balance:
            raise ValueError('残高不足')

        self.balance -= amount
        self.save()

        # ログ記録
        OffsetLog.objects.create(
            tenant_id=self.tenant_id,
            guardian=self.guardian,
            invoice=invoice,
            transaction_type=OffsetLog.TransactionType.OFFSET,
            amount=-amount,
            balance_after=self.balance,
            reason=reason,
        )


# =============================================================================
# OffsetLog (相殺ログ)
# =============================================================================
class OffsetLog(TenantModel):
    """相殺・預り金取引ログ

    預り金の入出金履歴を記録
    """

    class TransactionType(models.TextChoices):
        DEPOSIT = 'deposit', '入金'
        OFFSET = 'offset', '相殺'
        REFUND = 'refund', '返金'
        ADJUSTMENT = 'adjustment', '調整'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        related_name='offset_logs',
        verbose_name='保護者'
    )

    # 関連請求書・入金
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='offset_logs',
        verbose_name='請求書'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='offset_logs',
        verbose_name='入金'
    )

    # 取引情報
    transaction_type = models.CharField(
        '取引種別',
        max_length=20,
        choices=TransactionType.choices
    )
    amount = models.DecimalField('金額', max_digits=12, decimal_places=0)
    balance_after = models.DecimalField('取引後残高', max_digits=12, decimal_places=0)

    reason = models.TextField('理由', blank=True)

    class Meta:
        db_table = 'billing_offset_logs'
        verbose_name = '相殺ログ'
        verbose_name_plural = '相殺ログ'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.guardian} - {self.get_transaction_type_display()} {self.amount}円"


# =============================================================================
# RefundRequest (返金申請)
# =============================================================================
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
        Invoice,
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


# =============================================================================
# MileTransaction (マイル取引)
# =============================================================================
class MileTransaction(TenantModel):
    """マイル取引ログ

    マイルの付与・使用履歴を記録。
    ルール:
    - 4pt以上から利用可能
    - 最初は-2ptして開始、以後2ptごとに500円引
    - コース契約が2つ以上のときのみ適用
    """

    class TransactionType(models.TextChoices):
        EARN = 'earn', '付与'
        USE = 'use', '使用'
        EXPIRE = 'expire', '失効'
        ADJUSTMENT = 'adjustment', '調整'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        related_name='mile_transactions',
        verbose_name='保護者'
    )

    # 関連請求書 (使用時)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='mile_transactions',
        verbose_name='請求書'
    )

    # 取引情報
    transaction_type = models.CharField(
        '取引種別',
        max_length=20,
        choices=TransactionType.choices
    )
    miles = models.IntegerField('マイル数')
    balance_after = models.IntegerField('取引後残高')

    # 使用時の割引額
    discount_amount = models.DecimalField(
        '割引額',
        max_digits=10,
        decimal_places=0,
        default=0
    )

    # 付与元情報
    earn_source = models.CharField('付与元', max_length=100, blank=True)
    earn_date = models.DateField('付与日', null=True, blank=True)
    expire_date = models.DateField('有効期限', null=True, blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_mile_transactions'
        verbose_name = 'マイル取引'
        verbose_name_plural = 'マイル取引'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.guardian} - {self.get_transaction_type_display()} {self.miles}pt"

    @classmethod
    def get_balance(cls, guardian):
        """保護者のマイル残高を取得"""
        last = cls.objects.filter(guardian=guardian).order_by('-created_at').first()
        return last.balance_after if last else 0

    @classmethod
    def calculate_discount(cls, miles_to_use):
        """使用マイル数から割引額を計算

        4pt以上から利用可能
        最初の4ptで500円引（-2して開始）
        以後2ptごとに500円引

        例:
        - 4pt → 500円 ((4-2)/2 * 500 = 500)
        - 6pt → 1000円 ((6-2)/2 * 500 = 1000)
        - 8pt → 1500円 ((8-2)/2 * 500 = 1500)
        """
        if miles_to_use < 4:
            return Decimal('0')

        usable_miles = miles_to_use - 2  # 最初の2ptを引く
        discount_units = usable_miles // 2
        return Decimal(discount_units * 500)

    @classmethod
    def can_use_miles(cls, guardian):
        """マイル使用可能か判定

        条件: コース契約が2つ以上
        """
        from apps.contracts.models import Contract
        active_contracts = Contract.objects.filter(
            guardian=guardian,
            status=Contract.Status.ACTIVE
        ).count()
        return active_contracts >= 2


# =============================================================================
# DirectDebitResult (引落結果)
# =============================================================================
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
        Invoice,
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


# =============================================================================
# CashManagement (現金管理)
# =============================================================================
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
        Invoice,
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


# =============================================================================
# BankTransfer (振込入金)
# =============================================================================
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
        Invoice,
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


# =============================================================================
# PaymentProvider (決済代行会社マスタ)
# =============================================================================
class PaymentProvider(TenantModel):
    """決済代行会社マスタ

    UFJファクター、JACCS、中京ファイナンスなどの決済代行会社を管理。
    各社の委託者コード、締日、引落日などを設定する。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 識別情報
    code = models.CharField(
        '識別コード',
        max_length=30,
        help_text='例: ufj_factor, jaccs, chukyo_finance'
    )
    name = models.CharField('名称', max_length=100)

    # 委託者情報
    consignor_code = models.CharField(
        '委託者コード',
        max_length=20,
        help_text='決済代行会社から付与された委託者コード'
    )
    default_bank_code = models.CharField(
        'デフォルト銀行コード',
        max_length=4,
        blank=True,
        help_text='エクスポート時のデフォルト銀行コード'
    )

    # ファイル設定
    file_encoding = models.CharField(
        'ファイルエンコーディング',
        max_length=20,
        default='shift_jis',
        help_text='CSVファイルのエンコーディング'
    )

    # 締日・引落日設定
    closing_day = models.IntegerField(
        '締日',
        default=25,
        help_text='毎月の締日（1-31）'
    )
    debit_day = models.IntegerField(
        '引落日',
        default=27,
        help_text='毎月の引落日（1-31）'
    )

    # ステータス
    is_active = models.BooleanField('有効', default=True)

    # 表示順
    sort_order = models.IntegerField('表示順', default=0)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_payment_providers'
        verbose_name = '決済代行会社'
        verbose_name_plural = '決済代行会社'
        ordering = ['sort_order', 'code']
        unique_together = ['tenant_id', 'code']

    def __str__(self):
        return self.name


# =============================================================================
# BillingPeriod (請求期間/締日管理)
# =============================================================================
class BillingPeriod(TenantModel):
    """請求期間/締日管理

    決済代行会社ごとの請求期間を管理。
    締め処理後は該当月の請求データ変更を禁止する。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 決済代行会社
    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.CASCADE,
        related_name='billing_periods',
        verbose_name='決済代行会社'
    )

    # 対象期間
    year = models.IntegerField('対象年')
    month = models.IntegerField('対象月')

    # 締日
    closing_date = models.DateField(
        '締日',
        help_text='この期間の実際の締日'
    )

    # 締めステータス
    is_closed = models.BooleanField('締め済み', default=False)
    closed_at = models.DateTimeField('締め日時', null=True, blank=True)
    closed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='closed_billing_periods',
        verbose_name='締め実行者'
    )

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_periods'
        verbose_name = '請求期間'
        verbose_name_plural = '請求期間'
        ordering = ['-year', '-month', 'provider']
        unique_together = ['tenant_id', 'provider', 'year', 'month']

    def __str__(self):
        status = '締済' if self.is_closed else '未締'
        return f"{self.provider.name} {self.year}年{self.month:02d}月 ({status})"

    def close(self, user):
        """締め処理を実行"""
        self.is_closed = True
        self.closed_at = timezone.now()
        self.closed_by = user
        self.save()

    def reopen(self):
        """締め解除"""
        self.is_closed = False
        self.closed_at = None
        self.closed_by = None
        self.save()


# =============================================================================
# DebitExportBatch (引落データエクスポートバッチ)
# =============================================================================
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
        PaymentProvider,
        on_delete=models.CASCADE,
        related_name='export_batches',
        verbose_name='決済代行会社'
    )

    # 請求期間
    billing_period = models.ForeignKey(
        BillingPeriod,
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


# =============================================================================
# DebitExportLine (引落データエクスポート明細)
# =============================================================================
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
        Invoice,
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
        DirectDebitResult,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='export_lines',
        verbose_name='引落結果'
    )

    # Paymentとの紐付け（成功時）
    payment = models.ForeignKey(
        Payment,
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

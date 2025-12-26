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
# GuardianBalance (預り金残高/過不足金)
# =============================================================================
class GuardianBalance(TenantModel):
    """保護者預り金残高/過不足金

    1保護者に1レコード。入金・請求確定時に残高を更新。
    - プラス残高: 過払い（預り金）
    - マイナス残高: 不足金（未払い繰越）
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    guardian = models.OneToOneField(
        'students.Guardian',
        on_delete=models.CASCADE,
        related_name='balance',
        verbose_name='保護者'
    )

    balance = models.DecimalField(
        '残高',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='プラス=預り金（過払い）、マイナス=不足金（未払い繰越）'
    )
    last_updated = models.DateTimeField('最終更新日時', auto_now=True)

    notes = models.TextField('メモ', blank=True)

    class Meta:
        db_table = 'billing_guardian_balances'
        verbose_name = '預り金残高'
        verbose_name_plural = '預り金残高'

    def __str__(self):
        if self.balance >= 0:
            return f"{self.guardian} - 預り金 {self.balance:,.0f}円"
        else:
            return f"{self.guardian} - 不足金 {abs(self.balance):,.0f}円"

    @property
    def balance_display(self):
        """残高の表示用文字列"""
        if self.balance >= 0:
            return f"預り金 ¥{self.balance:,.0f}"
        else:
            return f"不足金 ¥{abs(self.balance):,.0f}"

    @property
    def is_deficit(self):
        """不足金があるかどうか"""
        return self.balance < 0

    def add_payment(self, amount, reason='', payment=None):
        """入金を記録（残高を増やす）"""
        self.balance += Decimal(str(amount))
        self.save()

        # ログ記録
        OffsetLog.objects.create(
            tenant_id=self.tenant_id,
            guardian=self.guardian,
            payment=payment,
            transaction_type=OffsetLog.TransactionType.DEPOSIT,
            amount=amount,
            balance_after=self.balance,
            reason=reason,
        )

    def add_billing(self, amount, reason='', invoice=None):
        """請求を記録（残高を減らす）

        請求が発生すると残高が減る（マイナス方向に動く）
        """
        self.balance -= Decimal(str(amount))
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

    def add_balance(self, amount, reason=''):
        """残高を追加（後方互換性のため維持）"""
        self.balance += Decimal(str(amount))
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
        """残高を使用 (相殺)（後方互換性のため維持）"""
        if amount > self.balance:
            raise ValueError('残高不足')

        self.balance -= Decimal(str(amount))
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

    def adjust_balance(self, amount, reason=''):
        """残高を調整（プラス/マイナス両方可）"""
        self.balance += Decimal(str(amount))
        self.save()

        # ログ記録
        OffsetLog.objects.create(
            tenant_id=self.tenant_id,
            guardian=self.guardian,
            transaction_type=OffsetLog.TransactionType.ADJUSTMENT,
            amount=amount,
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
# MonthlyBillingDeadline (月次請求締切管理)
# =============================================================================
class MonthlyBillingDeadline(TenantModel):
    """月次請求締切管理

    内部的な締日管理。決済代行会社とは別に、各月の請求データを締める。
    締日を過ぎると、その月の請求データは編集・削除・割引追加が不可になる。

    例:
    - 12月分請求の締日が25日の場合、12/26以降は12月分の請求データは編集不可
    - 編集不可になる項目: 料金変更、削除、割引追加、コース変更など
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 対象期間
    year = models.IntegerField('対象年')
    month = models.IntegerField('対象月')

    # 締日設定
    closing_day = models.IntegerField(
        '締日',
        default=25,
        help_text='毎月この日を過ぎると、当月分の請求は編集不可になる'
    )

    # 自動締め（締日を過ぎたら自動的にロック）
    auto_close = models.BooleanField(
        '自動締め',
        default=True,
        help_text='締日を過ぎたら自動的にロック状態にする'
    )

    # 手動締め状態
    is_manually_closed = models.BooleanField(
        '手動締め済み',
        default=False,
        help_text='締日前でも手動で締めることが可能'
    )
    manually_closed_at = models.DateTimeField('手動締め日時', null=True, blank=True)
    manually_closed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='manually_closed_deadlines',
        verbose_name='手動締め実行者'
    )

    # 締め解除（特別な場合のみ）
    is_reopened = models.BooleanField('締め解除済み', default=False)
    reopened_at = models.DateTimeField('締め解除日時', null=True, blank=True)
    reopened_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reopened_deadlines',
        verbose_name='締め解除実行者'
    )
    reopen_reason = models.TextField('締め解除理由', blank=True)

    # 確認中状態（経理確認中）
    is_under_review = models.BooleanField(
        '確認中',
        default=False,
        help_text='経理が確認中。経理以外は編集不可'
    )
    under_review_at = models.DateTimeField('確認開始日時', null=True, blank=True)
    under_review_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='review_started_deadlines',
        verbose_name='確認開始者'
    )

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_monthly_deadlines'
        verbose_name = '月次請求締切'
        verbose_name_plural = '月次請求締切'
        ordering = ['-year', '-month']
        unique_together = ['tenant_id', 'year', 'month']

    def __str__(self):
        return f"{self.year}年{self.month:02d}月分請求 ({self.status_display})"

    @property
    def status(self) -> str:
        """ステータスを取得: open, under_review, closed"""
        if self.is_closed:
            return 'closed'
        if self.is_under_review:
            return 'under_review'
        return 'open'

    @property
    def status_display(self) -> str:
        """ステータス表示名"""
        status_map = {
            'open': '未締',
            'under_review': '確認中',
            'closed': '締済',
        }
        return status_map.get(self.status, '未締')

    @property
    def is_closed(self) -> bool:
        """締め状態を判定

        以下のいずれかの場合に締め済みとなる:
        1. 手動で締められた（is_manually_closed=True）
        2. 自動締めが有効で、締日を過ぎている
        3. ただし、締め解除されている場合は未締め扱い
        """
        if self.is_reopened:
            return False

        if self.is_manually_closed:
            return True

        if self.auto_close:
            from datetime import date
            today = date.today()
            try:
                closing_date = date(self.year, self.month, self.closing_day)
            except ValueError:
                # 締日が月末を超える場合は月末日
                import calendar
                last_day = calendar.monthrange(self.year, self.month)[1]
                closing_date = date(self.year, self.month, last_day)

            return today > closing_date

        return False

    @property
    def closing_date(self):
        """実際の締日を取得"""
        from datetime import date
        import calendar
        try:
            return date(self.year, self.month, self.closing_day)
        except ValueError:
            last_day = calendar.monthrange(self.year, self.month)[1]
            return date(self.year, self.month, last_day)

    @property
    def can_edit(self) -> bool:
        """編集可能かどうか（確定済みは編集不可）"""
        return not self.is_closed

    def can_edit_by_user(self, user) -> bool:
        """ユーザーが編集可能かどうか

        - 確定済み: 誰も編集不可
        - 確認中: 経理・管理者のみ編集可
        - 未締め: 誰でも編集可
        """
        if self.is_closed:
            return False
        if self.is_under_review:
            # 経理・管理者権限チェック
            from apps.users.models import User
            allowed_roles = [
                User.Role.ACCOUNTING,
                User.Role.ADMIN,
                User.Role.SUPER_ADMIN,
            ]
            return hasattr(user, 'role') and user.role in allowed_roles
        return True

    def start_review(self, user):
        """確認中にする"""
        self.is_under_review = True
        self.under_review_at = timezone.now()
        self.under_review_by = user
        # 締め解除状態をクリア
        self.is_reopened = False
        self.reopened_at = None
        self.reopened_by = None
        self.reopen_reason = ''
        self.save()

    def cancel_review(self, user):
        """確認中を解除して通常状態に戻す"""
        self.is_under_review = False
        self.under_review_at = None
        self.under_review_by = None
        self.save()

    def close_manually(self, user, notes: str = ''):
        """手動で締める（確定）"""
        self.is_manually_closed = True
        self.manually_closed_at = timezone.now()
        self.manually_closed_by = user
        # 確認中状態をクリア
        self.is_under_review = False
        self.under_review_at = None
        self.under_review_by = None
        # 締め解除状態をクリア
        self.is_reopened = False
        self.reopened_at = None
        self.reopened_by = None
        if notes:
            self.notes = notes
        self.save()

    def reopen(self, user, reason: str):
        """締め解除（要理由）"""
        self.is_reopened = True
        self.reopened_at = timezone.now()
        self.reopened_by = user
        self.reopen_reason = reason
        self.save()

    @classmethod
    def get_or_create_for_month(cls, tenant_id: int, year: int, month: int, closing_day: int = 25):
        """指定月の締切レコードを取得または作成"""
        deadline, created = cls.objects.get_or_create(
            tenant_id=tenant_id,
            year=year,
            month=month,
            defaults={
                'closing_day': closing_day,
                'auto_close': True,
            }
        )
        return deadline, created

    @classmethod
    def is_month_editable(cls, tenant_id: int, year: int, month: int) -> bool:
        """指定月が編集可能かどうかをチェック"""
        try:
            deadline = cls.objects.get(
                tenant_id=tenant_id,
                year=year,
                month=month
            )
            return deadline.can_edit
        except cls.DoesNotExist:
            # レコードがない場合は編集可能（まだ締切管理されていない）
            return True


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


# =============================================================================
# BankTransferImport (振込データインポートバッチ)
# =============================================================================
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


# =============================================================================
# ConfirmedBilling (請求確定)
# =============================================================================
class ConfirmedBilling(TenantModel):
    """請求確定データ

    締日確定時に生徒ごとの請求データをスナップショットとして保存。
    元のStudentItemとは独立して管理され、監査証跡として機能する。
    """

    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', '確定'
        UNPAID = 'unpaid', '未入金'
        PARTIAL = 'partial', '一部入金'
        PAID = 'paid', '入金済'
        CANCELLED = 'cancelled', '取消'

    class PaymentMethod(models.TextChoices):
        DIRECT_DEBIT = 'direct_debit', '口座振替'
        BANK_TRANSFER = 'bank_transfer', '振込'
        CASH = 'cash', '現金'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    billing_no = models.CharField(
        '請求番号',
        max_length=20,
        blank=True,
        db_index=True,
        help_text='例: CB202501-0001'
    )

    # 対象
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='confirmed_billings',
        verbose_name='生徒'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        related_name='confirmed_billings',
        verbose_name='保護者'
    )

    # 請求期間
    year = models.IntegerField('請求年')
    month = models.IntegerField('請求月')
    billing_deadline = models.ForeignKey(
        MonthlyBillingDeadline,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_billings',
        verbose_name='締日'
    )

    # 金額
    subtotal = models.DecimalField('小計', max_digits=12, decimal_places=0, default=0)
    discount_total = models.DecimalField('割引合計', max_digits=12, decimal_places=0, default=0)
    tax_amount = models.DecimalField('税額', max_digits=12, decimal_places=0, default=0)
    total_amount = models.DecimalField('合計金額', max_digits=12, decimal_places=0, default=0)

    # 入金情報
    paid_amount = models.DecimalField('入金済金額', max_digits=12, decimal_places=0, default=0)
    balance = models.DecimalField('残高', max_digits=12, decimal_places=0, default=0)

    # 繰越額（前月からの繰越）
    carry_over_amount = models.DecimalField(
        '繰越額',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='前月からの繰越額（プラス=未払い繰越、マイナス=過払い繰越）'
    )

    # 明細スナップショット（JSON形式で保存）
    items_snapshot = models.JSONField('明細スナップショット', default=list)
    discounts_snapshot = models.JSONField('割引スナップショット', default=list)

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED
    )
    payment_method = models.CharField(
        '支払方法',
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.DIRECT_DEBIT
    )

    # 確定情報
    confirmed_at = models.DateTimeField('確定日時', auto_now_add=True)
    confirmed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_billings',
        verbose_name='確定者'
    )

    # 入金完了情報
    paid_at = models.DateTimeField('入金完了日時', null=True, blank=True)

    # メモ
    notes = models.TextField('備考', blank=True)

    # 退会日情報
    withdrawal_date = models.DateField('全退会日', null=True, blank=True, help_text='生徒の退会日')
    brand_withdrawal_dates = models.JSONField(
        'ブランド退会日',
        default=dict,
        blank=True,
        help_text='ブランドごとの退会日 {brand_id: "YYYY-MM-DD"}'
    )

    # 休会・復会日情報
    suspension_date = models.DateField('休会日', null=True, blank=True, help_text='生徒の休会日')
    return_date = models.DateField('復会日', null=True, blank=True, help_text='生徒の復会日')

    class Meta:
        db_table = 't_confirmed_billing'
        verbose_name = '請求確定'
        verbose_name_plural = '請求確定'
        # 並び順: 保護者 → 生徒 → 請求番号
        ordering = ['guardian__last_name', 'guardian__first_name', 'student__last_name', 'student__first_name', 'billing_no']
        indexes = [
            models.Index(fields=['student', 'year', 'month']),
            models.Index(fields=['guardian', 'year', 'month']),
            models.Index(fields=['status']),
            models.Index(fields=['-confirmed_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant_id', 'student', 'year', 'month'],
                name='unique_confirmed_billing_per_student_month'
            )
        ]

    def __str__(self):
        student_name = self.student.full_name if self.student else '生徒なし'
        return f"{self.year}年{self.month}月分 - {student_name} ({self.total_amount:,}円)"

    def save(self, *args, **kwargs):
        # billing_noを自動採番
        if not self.billing_no:
            self.billing_no = self._generate_billing_no()
        super().save(*args, **kwargs)

    def _generate_billing_no(self):
        """請求番号を生成: CB202501-0001"""
        prefix = f"CB{self.year}{str(self.month).zfill(2)}"

        # 同一年月の最大番号を取得
        last = ConfirmedBilling.objects.filter(
            tenant_id=self.tenant_id,
            billing_no__startswith=prefix
        ).order_by('-billing_no').first()

        if last and last.billing_no:
            try:
                last_num = int(last.billing_no.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        return f"{prefix}-{str(next_num).zfill(4)}"

    def update_payment_status(self):
        """入金状況に基づいてステータスを更新"""
        self.balance = self.total_amount - self.paid_amount
        if self.paid_amount >= self.total_amount:
            self.status = self.Status.PAID
            if not self.paid_at:
                self.paid_at = timezone.now()
        elif self.paid_amount > 0:
            self.status = self.Status.PARTIAL
        else:
            self.status = self.Status.UNPAID
        self.save()

    @classmethod
    def create_from_student_items(cls, tenant_id, student, guardian, year, month, user=None):
        """StudentItemから請求確定データを作成"""
        from apps.contracts.models import StudentItem, StudentDiscount

        # 既存の確定データがあれば取得（更新用）
        confirmed, created = cls.objects.get_or_create(
            tenant_id=tenant_id,
            student=student,
            year=year,
            month=month,
            defaults={'guardian': guardian}
        )

        if not created and confirmed.status == cls.Status.PAID:
            # 既に入金済みの場合は更新しない
            return confirmed, False

        # 該当月のStudentItemを取得
        billing_month_formats = [
            f"{year}-{str(month).zfill(2)}",  # YYYY-MM
            f"{year}{str(month).zfill(2)}",   # YYYYMM
        ]
        items = StudentItem.objects.filter(
            tenant_id=tenant_id,
            student=student,
            billing_month__in=billing_month_formats,
            deleted_at__isnull=True
        ).select_related('product', 'course', 'brand', 'contract')

        # 明細スナップショットを作成
        items_snapshot = []
        subtotal = Decimal('0')
        for item in items:
            # 旧ID優先順: StudentItem.old_id > Product.product_code
            old_id = item.old_id or ''
            if not old_id and item.product:
                old_id = item.product.product_code or ''

            # 請求カテゴリ（商品種別）
            item_type = ''
            item_type_display = ''
            product_name_short = ''
            if item.product:
                item_type = item.product.item_type or ''
                item_type_display = item.product.get_item_type_display() if item.product.item_type else ''
                product_name_short = item.product.product_name_short or ''

            # 契約番号
            contract_no = ''
            contract_id = ''
            if item.contract:
                contract_no = item.contract.contract_no or ''
                contract_id = str(item.contract.id) if item.contract.id else ''

            item_data = {
                'id': str(item.id),
                'old_id': old_id,  # 旧システムID（例: 24AEC_1000007_1）
                'product_name': item.product.product_name if item.product else None,
                'product_name_short': product_name_short,  # 契約名
                'item_type': item_type,  # 請求カテゴリコード
                'item_type_display': item_type_display,  # 請求カテゴリ表示名
                'course_name': item.course.course_name if item.course else None,
                'brand_id': str(item.brand.id) if item.brand else None,
                'brand_name': item.brand.brand_name if item.brand else None,
                'contract_no': contract_no,  # 契約番号
                'contract_id': contract_id,  # 契約ID
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'discount_amount': str(item.discount_amount),
                'final_price': str(item.final_price),
                'notes': item.notes,
            }
            items_snapshot.append(item_data)

        # 設備費は1生徒につき1つのみ（最高額を採用）
        facility_types = ['facility', 'enrollment_facility']
        facility_items = [i for i in items_snapshot if i.get('item_type') in facility_types]
        non_facility_items = [i for i in items_snapshot if i.get('item_type') not in facility_types]

        if len(facility_items) > 1:
            # 最高額の設備費を選択
            highest_facility = max(facility_items, key=lambda x: Decimal(str(x.get('final_price', 0) or 0)))
            items_snapshot = non_facility_items + [highest_facility]

        # 小計を再計算
        subtotal = sum(Decimal(str(i.get('final_price', 0) or 0)) for i in items_snapshot)

        # 割引を取得（生徒レベル + 保護者レベル）
        billing_date = f"{year}-{str(month).zfill(2)}-01"
        discounts = StudentDiscount.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            deleted_at__isnull=True
        ).filter(
            # 生徒に紐づく割引 OR 保護者に紐づく割引（生徒未指定）
            models.Q(student=student) | models.Q(guardian=guardian, student__isnull=True)
        ).filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=billing_date),
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=billing_date)
        )

        discounts_snapshot = []
        discount_total = Decimal('0')

        # 社割用：各授業料アイテムの割引Maxを考慮した割引額を計算
        from apps.contracts.models import Product as ProductModel
        tuition_types = ['tuition', 'TUITION']

        # 社割対象の授業料アイテムと割引額を計算
        shawari_items = []
        for item in items_snapshot:
            if item.get('item_type') not in tuition_types:
                continue
            product_name = item.get('product_name', '') or ''
            if '社割' in product_name:
                continue
            item_amount = Decimal(str(item.get('final_price', 0) or item.get('unit_price', 0)))
            if item_amount <= 0:
                continue
            product_code = item.get('product_code', '') or item.get('old_id', '')
            discount_max_rate = Decimal('50')
            if product_code:
                product_obj = ProductModel.objects.filter(product_code=product_code).first()
                if product_obj and product_obj.discount_max is not None:
                    # discount_max=0の場合は割引なし
                    discount_max_rate = min(Decimal('50'), Decimal(str(product_obj.discount_max)))
            if discount_max_rate > 0:
                shawari_items.append({
                    'product_name': product_name,
                    'item_amount': item_amount,
                    'discount_rate': discount_max_rate,
                    'discount_amount': item_amount * discount_max_rate / Decimal('100'),
                    'item_id': item.get('id', ''),
                })

        # 社割が既に適用されたかチェック（複数の社割レコードがあっても1回のみ適用）
        shawari_applied = False

        for discount in discounts:
            # 社割は各授業料ごとに割引を適用（複数あっても1回のみ）
            if '社割' in (discount.discount_name or ''):
                if shawari_applied:
                    continue  # 既に社割が適用されている場合はスキップ
                if shawari_items:
                    shawari_applied = True
                    # 授業料1本ごとに社割を追加
                    for idx, shawari_item in enumerate(shawari_items):
                        discount_data = {
                            'id': f"{discount.id}_item{idx}" if discount.id else f"shawari_item{idx}",
                            'old_id': discount.old_id or '',
                            'discount_name': f"社割（{shawari_item['product_name']}）",
                            'amount': str(shawari_item['discount_amount']),
                            'discount_unit': 'yen',
                            'discount_rate': str(shawari_item['discount_rate']),
                            'target_item_id': shawari_item['item_id'],
                            'is_shawari': True,
                        }
                        discounts_snapshot.append(discount_data)
                        discount_total += shawari_item['discount_amount']
                continue
            elif discount.discount_unit == 'percent':
                amount = subtotal * discount.amount / 100
            else:
                amount = discount.amount
            discount_data = {
                'id': str(discount.id),
                'old_id': discount.old_id or '',  # 旧システムID
                'discount_name': discount.discount_name,
                'amount': str(amount),
                'discount_unit': discount.discount_unit,
            }
            discounts_snapshot.append(discount_data)
            discount_total += amount

        # 退会日情報を取得
        from apps.students.models import StudentEnrollment, SuspensionRequest

        # 全退会日（生徒の退会日）
        student_withdrawal_date = student.withdrawal_date if hasattr(student, 'withdrawal_date') else None

        # ブランド退会日（各ブランドの終了日）
        brand_withdrawal_dates = {}
        enrollments = StudentEnrollment.objects.filter(
            tenant_id=tenant_id,
            student=student,
            end_date__isnull=False,
            deleted_at__isnull=True
        ).select_related('brand')
        for enrollment in enrollments:
            if enrollment.brand_id and enrollment.end_date:
                brand_withdrawal_dates[str(enrollment.brand_id)] = enrollment.end_date.isoformat()

        # 休会日・復会日を取得
        student_suspension_date = student.suspended_date if hasattr(student, 'suspended_date') else None
        student_return_date = None
        # 最新の復会日を取得
        latest_suspension = SuspensionRequest.objects.filter(
            tenant_id=tenant_id,
            student=student,
            resumed_at__isnull=False,
            deleted_at__isnull=True
        ).order_by('-resumed_at').first()
        if latest_suspension:
            student_return_date = latest_suspension.resumed_at

        # 確定データを更新
        confirmed.guardian = guardian
        confirmed.subtotal = subtotal
        confirmed.discount_total = discount_total
        confirmed.total_amount = subtotal - discount_total
        confirmed.balance = confirmed.total_amount - confirmed.paid_amount
        confirmed.items_snapshot = items_snapshot
        confirmed.discounts_snapshot = discounts_snapshot
        confirmed.withdrawal_date = student_withdrawal_date
        confirmed.brand_withdrawal_dates = brand_withdrawal_dates
        confirmed.suspension_date = student_suspension_date
        confirmed.return_date = student_return_date
        if user:
            confirmed.confirmed_by = user
        confirmed.save()

        # ステータス更新
        if confirmed.paid_amount > 0:
            confirmed.update_payment_status()

        return confirmed, created

    @classmethod
    def create_from_contracts(cls, tenant_id, student, guardian, year, month, user=None):
        """Contract（契約）から請求確定データを作成

        有効な契約のCourseItem（商品構成）から明細を生成
        """
        from apps.contracts.models import Contract, StudentDiscount
        from datetime import date

        # 既存の確定データがあれば取得（更新用）
        confirmed, created = cls.objects.get_or_create(
            tenant_id=tenant_id,
            student=student,
            year=year,
            month=month,
            defaults={'guardian': guardian}
        )

        if not created and confirmed.status == cls.Status.PAID:
            # 既に入金済みの場合は更新しない
            return confirmed, False

        # 対象月の開始日・終了日
        billing_start = date(year, month, 1)
        if month == 12:
            billing_end = date(year + 1, 1, 1)
        else:
            billing_end = date(year, month + 1, 1)

        # 該当月に有効な契約を取得
        contracts = Contract.objects.filter(
            tenant_id=tenant_id,
            student=student,
            status=Contract.Status.ACTIVE,
            start_date__lt=billing_end,  # 請求月末より前に開始
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=billing_start)  # 終了日なし or 請求月開始以降に終了
        ).select_related('course', 'brand', 'school')

        # 明細スナップショットを作成
        items_snapshot = []
        subtotal = Decimal('0')

        for contract in contracts:
            course = contract.course
            if not course:
                continue

            # CourseItem（コース商品構成）から明細を取得
            # 月額請求対象の商品タイプのみ含める（一時費用は除外）
            from apps.contracts.models import Product
            MONTHLY_BILLING_TYPES = [
                Product.ItemType.TUITION,        # 月謝
                Product.ItemType.MONTHLY_FEE,    # 月額費用
                Product.ItemType.FACILITY,       # 施設費
                Product.ItemType.CUSTODY,        # お預かり
                Product.ItemType.SNACK,          # おやつ
                Product.ItemType.LUNCH,          # 給食
                Product.ItemType.ABACUS,         # そろばん
                Product.ItemType.EXTRA_TUITION,  # 追加月謝
                Product.ItemType.TEXTBOOK,       # 教材費（選択されたもののみ）
            ]
            course_items = course.course_items.filter(
                is_active=True,
                product__item_type__in=MONTHLY_BILLING_TYPES
            ).select_related('product')

            # 選択された教材のIDを取得
            selected_textbook_ids = set(contract.selected_textbooks.values_list('id', flat=True))

            for course_item in course_items:
                product = course_item.product
                if not product or not product.is_active:
                    continue

                # 教材費の場合、選択されたもののみを含める
                if product.item_type == Product.ItemType.TEXTBOOK:
                    if product.id not in selected_textbook_ids:
                        continue  # 選択されていない教材はスキップ

                # 価格を取得（price_overrideがあればそちらを使用）
                unit_price = course_item.price_override if course_item.price_override is not None else (product.base_price or Decimal('0'))
                quantity = course_item.quantity or 1
                final_price = unit_price * quantity

                item_data = {
                    'contract_id': str(contract.id),
                    'contract_no': contract.contract_no,
                    'old_id': product.product_code or contract.old_id or '',  # 旧システムID（24AEC_1000007_1形式）
                    'course_id': str(course.id) if course else None,
                    'course_name': course.course_name if course else None,
                    'product_id': str(product.id),
                    'product_name': product.product_name,
                    'product_name_short': product.product_name_short or '',  # 契約名
                    'brand_id': str(contract.brand.id) if contract.brand else None,
                    'brand_name': contract.brand.brand_name if contract.brand else None,
                    'quantity': quantity,
                    'unit_price': str(unit_price),
                    'discount_amount': '0',
                    'final_price': str(final_price),
                    'item_type': product.item_type,  # 請求カテゴリコード
                    'item_type_display': product.get_item_type_display() if product.item_type else '',  # 請求カテゴリ表示名
                }
                items_snapshot.append(item_data)
                subtotal += final_price

        # 講習申込（SeminarEnrollment）を追加
        from apps.contracts.models import SeminarEnrollment
        billing_month_hyphen = f"{year}-{str(month).zfill(2)}"
        billing_month_compact = f"{year}{str(month).zfill(2)}"
        seminar_enrollments = SeminarEnrollment.objects.filter(
            tenant_id=tenant_id,
            student=student,
            status__in=[SeminarEnrollment.Status.APPLIED, SeminarEnrollment.Status.CONFIRMED],
            deleted_at__isnull=True
        ).filter(
            models.Q(billing_month=billing_month_hyphen) | models.Q(billing_month=billing_month_compact)
        ).select_related('seminar', 'seminar__brand')

        for enrollment in seminar_enrollments:
            seminar = enrollment.seminar
            unit_price = enrollment.unit_price or Decimal('0')
            discount_amount = enrollment.discount_amount or Decimal('0')
            final_price = enrollment.final_price or (unit_price - discount_amount)

            # 講習会タイプに基づくitem_type
            seminar_type_map = {
                'spring': 'seminar_spring',
                'summer': 'seminar_summer',
                'winter': 'seminar_winter',
                'autumn': 'seminar_autumn',
                'special': 'seminar_special',
                'other': 'seminar',
            }
            item_type = seminar_type_map.get(seminar.seminar_type, 'seminar') if seminar else 'seminar'

            item_data = {
                'seminar_enrollment_id': str(enrollment.id),
                'old_id': seminar.old_id if seminar else '',
                'seminar_id': str(seminar.id) if seminar else None,
                'seminar_code': seminar.seminar_code if seminar else '',
                'product_name': seminar.seminar_name if seminar else '',
                'product_code': seminar.seminar_code if seminar else '',
                'brand_id': str(seminar.brand.id) if seminar and seminar.brand else None,
                'brand_name': seminar.brand.brand_name if seminar and seminar.brand else None,
                'item_type': item_type,
                'item_type_display': '講習会',
                'is_required': enrollment.is_required,
                'quantity': 1,
                'unit_price': str(unit_price),
                'discount_amount': str(discount_amount),
                'final_price': str(final_price),
                'notes': enrollment.notes or '',
            }
            items_snapshot.append(item_data)
            subtotal += final_price

        # 設備費は1生徒につき1つのみ（最高額を採用）
        facility_types = ['facility', 'enrollment_facility']
        facility_items = [i for i in items_snapshot if i.get('item_type') in facility_types]
        non_facility_items = [i for i in items_snapshot if i.get('item_type') not in facility_types]

        if len(facility_items) > 1:
            # 最高額の設備費を選択
            highest_facility = max(facility_items, key=lambda x: Decimal(str(x.get('final_price', 0) or 0)))
            items_snapshot = non_facility_items + [highest_facility]

        # 小計を再計算
        subtotal = sum(Decimal(str(i.get('final_price', 0) or 0)) for i in items_snapshot)

        # 割引を取得（生徒レベル + 保護者レベル）
        billing_date = f"{year}-{str(month).zfill(2)}-01"
        discounts = StudentDiscount.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            deleted_at__isnull=True
        ).filter(
            # 生徒に紐づく割引 OR 保護者に紐づく割引（生徒未指定）
            models.Q(student=student) | models.Q(guardian=guardian, student__isnull=True)
        ).filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=billing_date),
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=billing_date)
        )

        # 教材費があるかチェック（コロナ割等のカテゴリ限定割引用）
        from apps.contracts.models import Product as ContractProduct
        has_material_fee = any(
            item.get('item_type') in [ContractProduct.ItemType.TEXTBOOK, ContractProduct.ItemType.ENROLLMENT_TEXTBOOK, 'textbook', 'enrollment_textbook']
            for item in items_snapshot
        )

        discounts_snapshot = []
        discount_total = Decimal('0')

        # 社割用：各授業料アイテムの割引Maxを考慮した割引額を計算
        tuition_types = ['tuition', 'TUITION']

        # 社割対象の授業料アイテムと割引額を計算
        shawari_items = []
        for item in items_snapshot:
            if item.get('item_type') not in tuition_types:
                continue
            # 社割のマイナス行は除外
            product_name = item.get('product_name', '') or ''
            if '社割' in product_name:
                continue
            item_amount = Decimal(str(item.get('final_price', 0) or item.get('unit_price', 0)))
            if item_amount <= 0:
                continue
            # 商品の割引Maxを取得（最大50%）
            product_code = item.get('product_code', '') or item.get('old_id', '')
            discount_max_rate = Decimal('50')
            if product_code:
                product_obj = ContractProduct.objects.filter(product_code=product_code).first()
                if product_obj and product_obj.discount_max is not None:
                    # discount_max=0の場合は割引なし
                    discount_max_rate = min(Decimal('50'), Decimal(str(product_obj.discount_max)))
            if discount_max_rate > 0:
                shawari_items.append({
                    'product_name': product_name,
                    'item_amount': item_amount,
                    'discount_rate': discount_max_rate,
                    'discount_amount': item_amount * discount_max_rate / Decimal('100'),
                    'item_id': item.get('id', ''),
                })

        # 社割が既に適用されたかチェック（複数の社割レコードがあっても1回のみ適用）
        shawari_applied = False

        for discount in discounts:
            # コロナ割（教材費のみ）のチェック：教材費がない場合はスキップ
            if 'コロナ' in (discount.discount_name or '') and not has_material_fee:
                continue  # 教材費がない場合はコロナ割を適用しない

            # 社割は各授業料ごとに割引を適用（複数あっても1回のみ）
            if '社割' in (discount.discount_name or ''):
                if shawari_applied:
                    continue  # 既に社割が適用されている場合はスキップ
                if shawari_items:
                    shawari_applied = True
                    # 授業料1本ごとに社割を追加
                    for idx, shawari_item in enumerate(shawari_items):
                        discount_data = {
                            'id': f"{discount.id}_item{idx}" if discount.id else f"shawari_item{idx}",
                            'old_id': discount.old_id or '',
                            'discount_name': f"社割（{shawari_item['product_name']}）",
                            'amount': str(shawari_item['discount_amount']),
                            'discount_unit': 'yen',
                            'discount_rate': str(shawari_item['discount_rate']),
                            'target_item_id': shawari_item['item_id'],
                            'is_shawari': True,
                        }
                        discounts_snapshot.append(discount_data)
                        discount_total += shawari_item['discount_amount']
                continue
            elif discount.discount_unit == 'percent':
                amount = subtotal * discount.amount / 100
            else:
                amount = discount.amount
            discount_data = {
                'id': str(discount.id),
                'old_id': discount.old_id or '',  # 旧システムID
                'discount_name': discount.discount_name,
                'amount': str(amount),
                'discount_unit': discount.discount_unit,
            }
            discounts_snapshot.append(discount_data)
            discount_total += amount

        # FS割引（友達紹介割引）を取得
        from apps.students.models import FSDiscount as FSDiscountModel
        from datetime import date as date_cls
        billing_date_obj = date_cls(year, month, 1)
        fs_discounts = FSDiscountModel.objects.filter(
            tenant_id=tenant_id,
            guardian=guardian,
            status=FSDiscountModel.Status.ACTIVE,
            valid_from__lte=billing_date_obj,
            valid_until__gte=billing_date_obj
        )
        for fs in fs_discounts:
            if fs.discount_type == FSDiscountModel.DiscountType.PERCENTAGE:
                amount = subtotal * fs.discount_value / 100
            else:
                amount = fs.discount_value
            discount_data = {
                'id': str(fs.id),
                'old_id': '',
                'discount_name': 'FS割引（友達紹介）',
                'amount': str(amount),
                'discount_unit': 'percent' if fs.discount_type == FSDiscountModel.DiscountType.PERCENTAGE else 'yen',
            }
            discounts_snapshot.append(discount_data)
            discount_total += amount

        # マイル割引（家族割）を取得
        from apps.pricing.calculations import calculate_mile_discount
        mile_discount_amount, total_miles, mile_discount_name = calculate_mile_discount(guardian)
        if mile_discount_amount > 0:
            discount_data = {
                'id': '',
                'old_id': '',
                'discount_name': mile_discount_name or f'家族割（{total_miles}マイル）',
                'amount': str(mile_discount_amount),
                'discount_unit': 'yen',
            }
            discounts_snapshot.append(discount_data)
            discount_total += mile_discount_amount

        # 前月からの繰越額を取得
        carry_over = cls.get_previous_month_balance(tenant_id, student, year, month)

        # 退会日情報を取得
        from apps.students.models import StudentEnrollment, SuspensionRequest

        # 全退会日（生徒の退会日）
        student_withdrawal_date = student.withdrawal_date if hasattr(student, 'withdrawal_date') else None

        # ブランド退会日（各ブランドの終了日）
        brand_withdrawal_dates = {}
        enrollments = StudentEnrollment.objects.filter(
            tenant_id=tenant_id,
            student=student,
            end_date__isnull=False,
            deleted_at__isnull=True
        ).select_related('brand')
        for enrollment in enrollments:
            if enrollment.brand_id and enrollment.end_date:
                brand_withdrawal_dates[str(enrollment.brand_id)] = enrollment.end_date.isoformat()

        # 休会日・復会日を取得
        student_suspension_date = student.suspended_date if hasattr(student, 'suspended_date') else None
        student_return_date = None
        # 最新の復会日を取得
        latest_suspension = SuspensionRequest.objects.filter(
            tenant_id=tenant_id,
            student=student,
            resumed_at__isnull=False,
            deleted_at__isnull=True
        ).order_by('-resumed_at').first()
        if latest_suspension:
            student_return_date = latest_suspension.resumed_at

        # 確定データを更新
        confirmed.guardian = guardian
        confirmed.subtotal = subtotal
        confirmed.discount_total = discount_total
        confirmed.total_amount = subtotal - discount_total
        confirmed.carry_over_amount = carry_over
        # 残高 = 今月請求 + 繰越 - 入金済
        confirmed.balance = confirmed.total_amount + carry_over - confirmed.paid_amount
        confirmed.items_snapshot = items_snapshot
        confirmed.discounts_snapshot = discounts_snapshot
        confirmed.withdrawal_date = student_withdrawal_date
        confirmed.brand_withdrawal_dates = brand_withdrawal_dates
        confirmed.suspension_date = student_suspension_date
        confirmed.return_date = student_return_date
        if user:
            confirmed.confirmed_by = user
        confirmed.save()

        # ステータス更新
        if confirmed.paid_amount > 0:
            confirmed.update_payment_status()

        return confirmed, created

    @classmethod
    def create_from_student_items(cls, tenant_id, student, guardian, year, month, user=None):
        """StudentItem（生徒商品）から請求確定データを作成

        インポート済みのStudentItemデータから明細を生成
        """
        from apps.contracts.models import StudentItem, StudentDiscount

        # billing_month形式: "2025-01" または "202501" の両方に対応
        billing_month_hyphen = f"{year}-{str(month).zfill(2)}"  # YYYY-MM形式
        billing_month_compact = f"{year}{str(month).zfill(2)}"  # YYYYMM形式

        # 既存の確定データがあれば取得（更新用）
        confirmed, created = cls.objects.get_or_create(
            tenant_id=tenant_id,
            student=student,
            year=year,
            month=month,
            defaults={'guardian': guardian}
        )

        if not created and confirmed.status == cls.Status.PAID:
            # 既に入金済みの場合は更新しない
            return confirmed, False

        # 該当月のStudentItemを取得（両形式に対応）
        student_items = StudentItem.objects.filter(
            tenant_id=tenant_id,
            student=student,
            deleted_at__isnull=True
        ).filter(
            models.Q(billing_month=billing_month_hyphen) | models.Q(billing_month=billing_month_compact)
        ).select_related('product', 'brand', 'school', 'course', 'contract')

        # 明細スナップショットを作成
        items_snapshot = []
        subtotal = Decimal('0')

        for item in student_items:
            product = item.product
            unit_price = item.unit_price or Decimal('0')
            quantity = item.quantity or 1
            discount_amount = item.discount_amount or Decimal('0')
            final_price = item.final_price or (unit_price * quantity - discount_amount)

            item_data = {
                'student_item_id': str(item.id),
                'old_id': item.old_id or '',
                'contract_id': str(item.contract.id) if item.contract else None,
                'contract_no': item.contract.contract_no if item.contract else None,
                'course_id': str(item.course.id) if item.course else None,
                'course_name': item.course.course_name if item.course else None,
                'product_id': str(product.id) if product else None,
                'product_name': product.product_name if product else '',
                'product_code': product.product_code if product else '',
                'brand_id': str(item.brand.id) if item.brand else None,
                'brand_name': item.brand.brand_name if item.brand else None,
                'school_name': item.school.school_name if item.school else None,
                'item_type': product.item_type if product else 'other',
                'item_type_display': product.get_item_type_display() if product else '',
                'quantity': quantity,
                'unit_price': str(unit_price),
                'discount_amount': str(discount_amount),
                'final_price': str(final_price),
                'notes': item.notes or '',
            }
            items_snapshot.append(item_data)
            subtotal += final_price

        # 講習申込（SeminarEnrollment）を追加
        from apps.contracts.models import SeminarEnrollment
        seminar_enrollments = SeminarEnrollment.objects.filter(
            tenant_id=tenant_id,
            student=student,
            status__in=[SeminarEnrollment.Status.APPLIED, SeminarEnrollment.Status.CONFIRMED],
            deleted_at__isnull=True
        ).filter(
            models.Q(billing_month=billing_month_hyphen) | models.Q(billing_month=billing_month_compact)
        ).select_related('seminar', 'seminar__brand')

        for enrollment in seminar_enrollments:
            seminar = enrollment.seminar
            unit_price = enrollment.unit_price or Decimal('0')
            discount_amount = enrollment.discount_amount or Decimal('0')
            final_price = enrollment.final_price or (unit_price - discount_amount)

            # 講習会タイプに基づくitem_type
            seminar_type_map = {
                'spring': 'seminar_spring',
                'summer': 'seminar_summer',
                'winter': 'seminar_winter',
                'autumn': 'seminar_autumn',
                'special': 'seminar_special',
                'other': 'seminar',
            }
            item_type = seminar_type_map.get(seminar.seminar_type, 'seminar') if seminar else 'seminar'

            item_data = {
                'seminar_enrollment_id': str(enrollment.id),
                'old_id': seminar.old_id if seminar else '',
                'seminar_id': str(seminar.id) if seminar else None,
                'seminar_code': seminar.seminar_code if seminar else '',
                'product_name': seminar.seminar_name if seminar else '',
                'product_code': seminar.seminar_code if seminar else '',
                'brand_id': str(seminar.brand.id) if seminar and seminar.brand else None,
                'brand_name': seminar.brand.brand_name if seminar and seminar.brand else None,
                'item_type': item_type,
                'item_type_display': '講習会',
                'is_required': enrollment.is_required,
                'quantity': 1,
                'unit_price': str(unit_price),
                'discount_amount': str(discount_amount),
                'final_price': str(final_price),
                'notes': enrollment.notes or '',
            }
            items_snapshot.append(item_data)
            subtotal += final_price

        # 割引を取得（生徒レベル + 保護者レベル）
        billing_date = f"{year}-{str(month).zfill(2)}-01"
        discounts = StudentDiscount.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            deleted_at__isnull=True
        ).filter(
            # 生徒に紐づく割引 OR 保護者に紐づく割引（生徒未指定）
            models.Q(student=student) | models.Q(guardian=guardian, student__isnull=True)
        ).filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=billing_date),
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=billing_date)
        )

        # 教材費があるかチェック（コロナ割等のカテゴリ限定割引用）
        from apps.contracts.models import Product
        has_material_fee = any(
            item.get('item_type') in [Product.ItemType.TEXTBOOK, Product.ItemType.ENROLLMENT_TEXTBOOK, 'textbook', 'enrollment_textbook']
            for item in items_snapshot
        )

        discounts_snapshot = []
        discount_total = Decimal('0')

        # 社割用：各授業料アイテムの割引Maxを考慮した割引額を計算
        tuition_types = ['tuition', 'TUITION']

        # 社割対象の授業料アイテムと割引額を計算
        shawari_items = []
        for item in items_snapshot:
            if item.get('item_type') not in tuition_types:
                continue
            product_name = item.get('product_name', '') or ''
            if '社割' in product_name:
                continue
            item_amount = Decimal(str(item.get('final_price', 0) or item.get('unit_price', 0)))
            if item_amount <= 0:
                continue
            product_code = item.get('product_code', '') or item.get('old_id', '')
            discount_max_rate = Decimal('50')
            if product_code:
                product_obj = Product.objects.filter(product_code=product_code).first()
                if product_obj and product_obj.discount_max is not None:
                    # discount_max=0の場合は割引なし
                    discount_max_rate = min(Decimal('50'), Decimal(str(product_obj.discount_max)))
            if discount_max_rate > 0:
                shawari_items.append({
                    'product_name': product_name,
                    'item_amount': item_amount,
                    'discount_rate': discount_max_rate,
                    'discount_amount': item_amount * discount_max_rate / Decimal('100'),
                    'item_id': item.get('id', ''),
                })

        # 社割が既に適用されたかチェック（複数の社割レコードがあっても1回のみ適用）
        shawari_applied = False

        for discount in discounts:
            # コロナ割（教材費のみ）のチェック：教材費がない場合はスキップ
            if 'コロナ' in (discount.discount_name or '') and not has_material_fee:
                continue  # 教材費がない場合はコロナ割を適用しない

            # 社割は各授業料ごとに割引を適用（複数あっても1回のみ）
            if '社割' in (discount.discount_name or ''):
                if shawari_applied:
                    continue  # 既に社割が適用されている場合はスキップ
                if shawari_items:
                    shawari_applied = True
                    # 授業料1本ごとに社割を追加
                    for idx, shawari_item in enumerate(shawari_items):
                        discount_data = {
                            'id': f"{discount.id}_item{idx}" if discount.id else f"shawari_item{idx}",
                            'old_id': discount.old_id or '',
                            'discount_name': f"社割（{shawari_item['product_name']}）",
                            'amount': str(shawari_item['discount_amount']),
                            'discount_unit': 'yen',
                            'discount_rate': str(shawari_item['discount_rate']),
                            'target_item_id': shawari_item['item_id'],
                            'is_shawari': True,
                        }
                        discounts_snapshot.append(discount_data)
                        discount_total += shawari_item['discount_amount']
                continue
            elif discount.discount_unit == 'percent':
                amount = subtotal * discount.amount / 100
            else:
                amount = discount.amount
            discount_data = {
                'id': str(discount.id),
                'old_id': discount.old_id or '',  # 旧システムID
                'discount_name': discount.discount_name,
                'amount': str(amount),
                'discount_unit': discount.discount_unit,
            }
            discounts_snapshot.append(discount_data)
            discount_total += amount

        # FS割引（友達紹介割引）を取得
        from apps.students.models import FSDiscount
        from datetime import date as date_class
        billing_date_obj = date_class(year, month, 1)
        fs_discounts = FSDiscount.objects.filter(
            tenant_id=tenant_id,
            guardian=guardian,
            status=FSDiscount.Status.ACTIVE,
            valid_from__lte=billing_date_obj,
            valid_until__gte=billing_date_obj
        )
        for fs in fs_discounts:
            if fs.discount_type == FSDiscount.DiscountType.PERCENTAGE:
                amount = subtotal * fs.discount_value / 100
            else:
                amount = fs.discount_value
            discount_data = {
                'id': str(fs.id),
                'old_id': '',
                'discount_name': 'FS割引（友達紹介）',
                'amount': str(amount),
                'discount_unit': 'percent' if fs.discount_type == FSDiscount.DiscountType.PERCENTAGE else 'yen',
            }
            discounts_snapshot.append(discount_data)
            discount_total += amount

        # マイル割引（家族割）を取得
        from apps.pricing.calculations import calculate_mile_discount
        mile_discount_amount, total_miles, mile_discount_name = calculate_mile_discount(guardian)
        if mile_discount_amount > 0:
            discount_data = {
                'id': '',
                'old_id': '',
                'discount_name': mile_discount_name or f'家族割（{total_miles}マイル）',
                'amount': str(mile_discount_amount),
                'discount_unit': 'yen',
            }
            discounts_snapshot.append(discount_data)
            discount_total += mile_discount_amount

        # 前月からの繰越額を取得
        carry_over = cls.get_previous_month_balance(tenant_id, student, year, month)

        # 退会日情報を取得
        from apps.students.models import StudentEnrollment, SuspensionRequest

        # 全退会日（生徒の退会日）
        student_withdrawal_date = student.withdrawal_date if hasattr(student, 'withdrawal_date') else None

        # ブランド退会日（各ブランドの終了日）
        brand_withdrawal_dates = {}
        enrollments = StudentEnrollment.objects.filter(
            tenant_id=tenant_id,
            student=student,
            end_date__isnull=False,
            deleted_at__isnull=True
        ).select_related('brand')
        for enrollment in enrollments:
            if enrollment.brand_id and enrollment.end_date:
                brand_withdrawal_dates[str(enrollment.brand_id)] = enrollment.end_date.isoformat()

        # 休会日・復会日を取得
        student_suspension_date = student.suspended_date if hasattr(student, 'suspended_date') else None
        student_return_date = None
        # 最新の復会日を取得
        latest_suspension = SuspensionRequest.objects.filter(
            tenant_id=tenant_id,
            student=student,
            resumed_at__isnull=False,
            deleted_at__isnull=True
        ).order_by('-resumed_at').first()
        if latest_suspension:
            student_return_date = latest_suspension.resumed_at

        # 確定データを更新
        confirmed.guardian = guardian
        confirmed.subtotal = subtotal
        confirmed.discount_total = discount_total
        confirmed.total_amount = subtotal - discount_total
        confirmed.carry_over_amount = carry_over
        # 残高 = 今月請求 + 繰越 - 入金済
        confirmed.balance = confirmed.total_amount + carry_over - confirmed.paid_amount
        confirmed.items_snapshot = items_snapshot
        confirmed.discounts_snapshot = discounts_snapshot
        confirmed.withdrawal_date = student_withdrawal_date
        confirmed.brand_withdrawal_dates = brand_withdrawal_dates
        confirmed.suspension_date = student_suspension_date
        confirmed.return_date = student_return_date
        if user:
            confirmed.confirmed_by = user
        confirmed.save()

        # ステータス更新
        if confirmed.paid_amount > 0:
            confirmed.update_payment_status()

        return confirmed, created

    @classmethod
    def get_previous_month_balance(cls, tenant_id, student, year, month):
        """前月の残高（繰越額）を取得

        Returns:
            Decimal: 前月の残高
                プラス = 前月に未払いがあった（今月への繰越請求）
                マイナス = 前月に過払いがあった（今月への繰越クレジット）
                0 = 前月は精算済み or データなし
        """
        # 前月を計算
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1

        # 前月のConfirmedBillingを取得
        prev_billing = cls.objects.filter(
            tenant_id=tenant_id,
            student=student,
            year=prev_year,
            month=prev_month
        ).first()

        if not prev_billing:
            return Decimal('0')

        # 残高 = 請求額 + 前月繰越 - 入金額
        # プラス = 未払い（次月に請求）、マイナス = 過払い（次月にクレジット）
        return prev_billing.balance

    @classmethod
    def apply_carry_over(cls, tenant_id, student, year, month):
        """前月の残高を今月の繰越額として適用"""
        confirmed = cls.objects.filter(
            tenant_id=tenant_id,
            student=student,
            year=year,
            month=month
        ).first()

        if not confirmed:
            return None

        # 前月の残高を取得
        carry_over = cls.get_previous_month_balance(tenant_id, student, year, month)

        # 繰越額を更新
        confirmed.carry_over_amount = carry_over
        # 残高を再計算（今月請求 + 繰越 - 入金）
        confirmed.balance = confirmed.total_amount + carry_over - confirmed.paid_amount
        confirmed.save()

        # ステータス更新
        if confirmed.balance <= 0 and confirmed.total_amount > 0:
            confirmed.status = cls.Status.PAID
            if not confirmed.paid_at:
                confirmed.paid_at = timezone.now()
            confirmed.save()

        return confirmed

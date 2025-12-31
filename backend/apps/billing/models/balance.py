"""
Balance Models - 預り金・相殺ログ
"""
import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TenantModel


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
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='offset_logs',
        verbose_name='請求書'
    )
    payment = models.ForeignKey(
        'billing.Payment',
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

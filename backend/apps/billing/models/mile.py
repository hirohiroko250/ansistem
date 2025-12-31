"""
Mile Models - マイル取引
"""
import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TenantModel


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
        'billing.Invoice',
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

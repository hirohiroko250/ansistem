"""
Provider Models - 決済代行会社・請求期間
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


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

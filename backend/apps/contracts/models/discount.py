"""
Discount Models - 割引マスタ
T07: 割引マスタ (Discount)
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class Discount(TenantModel):
    """T07: 割引マスタ

    割引の種類:
    - 社割: 社員であれば自動適用
    - 兄弟割引: 兄弟がいる場合に適用
    - 複数科目割引: 複数科目受講時に適用
    - キャンペーン: 期間限定キャンペーン
    - その他: その他の割引

    ※FS割と家族割（マイル）は別テーブルで管理
    """

    class DiscountType(models.TextChoices):
        EMPLOYEE = 'employee', '社割'
        SIBLING = 'sibling', '兄弟割引'
        MULTI_SUBJECT = 'multi_subject', '複数科目割引'
        CAMPAIGN = 'campaign', 'キャンペーン'
        EARLY_ENROLLMENT = 'early_enrollment', '早期入会割引'
        REFERRAL = 'referral', '紹介割引'
        OTHER = 'other', 'その他'

    class CalculationType(models.TextChoices):
        PERCENTAGE = 'percentage', '割合'
        FIXED = 'fixed', '固定金額'

    class ApplicableCategory(models.TextChoices):
        """適用カテゴリ"""
        TUITION = 'tuition', '授業料'
        MATERIAL = 'material', '教材費'
        ENROLLMENT = 'enrollment', '入会金'
        MONTHLY_FEE = 'monthly_fee', '月会費'
        ALL = 'all', '全て'

    class EndCondition(models.TextChoices):
        """終了条件"""
        ONCE = 'once', '1回だけ'
        MONTHLY = 'monthly', '毎月'
        UNTIL_END_DATE = 'until_end_date', '終了日まで'
        ON_CONTRACT_DECREASE = 'on_contract_decrease', '契約数が減った時'
        ON_BRAND_WITHDRAWAL = 'on_brand_withdrawal', 'ブランド退会時'
        ON_CONTRACT_END = 'on_contract_end', '契約終了時'
        ON_WITHDRAWAL = 'on_withdrawal', '退会時'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discount_code = models.CharField('割引コード', max_length=20)
    discount_name = models.CharField('割引名', max_length=100)
    discount_type = models.CharField(
        '割引種別',
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.OTHER
    )
    calculation_type = models.CharField(
        '計算種別',
        max_length=20,
        choices=CalculationType.choices,
        default=CalculationType.FIXED
    )
    value = models.DecimalField('値', max_digits=10, decimal_places=2)

    # 社割関連
    is_employee_discount = models.BooleanField(
        '社割（社員自動適用）',
        default=False,
        help_text='社員の場合、自動的に適用される割引'
    )

    # 適用対象
    applicable_brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='discounts',
        verbose_name='適用ブランド',
        help_text='空の場合は全ブランドに適用'
    )
    applicable_category = models.CharField(
        '適用カテゴリ',
        max_length=20,
        choices=ApplicableCategory.choices,
        default=ApplicableCategory.ALL,
        help_text='この割引が適用される請求カテゴリ'
    )

    # 終了条件
    end_condition = models.CharField(
        '終了条件',
        max_length=30,
        choices=EndCondition.choices,
        default=EndCondition.ONCE,
        help_text='割引が終了する条件'
    )
    is_recurring = models.BooleanField(
        '毎月適用',
        default=False,
        help_text='毎月繰り返し適用するか'
    )

    # 有効期間
    valid_from = models.DateField('適用開始日', null=True, blank=True)
    valid_until = models.DateField('適用終了日', null=True, blank=True)
    is_active = models.BooleanField('有効', default=True)

    # 備考
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't07_discounts'
        verbose_name = 'T07_割引マスタ'
        verbose_name_plural = 'T07_割引マスタ'
        ordering = ['discount_code']
        unique_together = ['tenant_id', 'discount_code']

    def __str__(self):
        return f"{self.discount_name} ({self.discount_code})"

    def is_applicable_to_category(self, category: str) -> bool:
        """指定カテゴリに適用可能か判定"""
        if self.applicable_category == self.ApplicableCategory.ALL:
            return True
        return self.applicable_category == category

    def is_applicable_to_brand(self, brand) -> bool:
        """指定ブランドに適用可能か判定"""
        if self.applicable_brand is None:
            return True
        return self.applicable_brand == brand

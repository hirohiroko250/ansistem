"""
Pricing Models - マージン計算

テーブル:
- CostCategory: 原価項目カテゴリ（教材制作費、システム利用料、決済手数料など）
- ProductCost: 商品ごとの原価設定
- MarginRule: 商品ごとのマージン計算ルール
- MarginCalculation: マージン計算結果（トランザクション）
- MarginCalculationLine: マージン計算明細
"""
import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TenantModel


class CostCategory(TenantModel):
    """原価項目カテゴリ

    例: 教材制作費、システム利用料、決済手数料、外注費
    """

    class CostType(models.TextChoices):
        FIXED = 'fixed', '固定金額'
        PERCENTAGE = 'percentage', '売上比率'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField('コード', max_length=50)
    name = models.CharField('原価項目名', max_length=100)
    description = models.TextField('説明', blank=True)

    cost_type = models.CharField(
        '原価タイプ',
        max_length=20,
        choices=CostType.choices,
        default=CostType.FIXED,
        help_text='固定金額 or 売上比率'
    )

    # デフォルト値（商品ごとに上書き可能）
    default_amount = models.DecimalField(
        'デフォルト金額',
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text='固定金額の場合のデフォルト値'
    )
    default_rate = models.DecimalField(
        'デフォルト率',
        max_digits=5,
        decimal_places=4,
        default=Decimal('0'),
        help_text='売上比率の場合のデフォルト値（例: 0.03 = 3%）'
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'pricing_cost_categories'
        verbose_name = '原価項目カテゴリ'
        verbose_name_plural = '原価項目カテゴリ'
        ordering = ['sort_order', 'code']
        unique_together = ['tenant_id', 'code']

    def __str__(self):
        return f"{self.name} ({self.code})"


class ProductCost(TenantModel):
    """商品ごとの原価設定

    商品×原価カテゴリごとに金額または率を設定
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        'contracts.Product',
        on_delete=models.CASCADE,
        related_name='costs',
        verbose_name='商品'
    )
    cost_category = models.ForeignKey(
        CostCategory,
        on_delete=models.CASCADE,
        related_name='product_costs',
        verbose_name='原価項目'
    )

    # 金額または率（カテゴリのデフォルトを上書き）
    amount = models.DecimalField(
        '金額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='設定しない場合はカテゴリのデフォルト値を使用'
    )
    rate = models.DecimalField(
        '率',
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='設定しない場合はカテゴリのデフォルト値を使用'
    )

    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'pricing_product_costs'
        verbose_name = '商品原価'
        verbose_name_plural = '商品原価'
        unique_together = ['product', 'cost_category']

    def __str__(self):
        return f"{self.product.product_name} - {self.cost_category.name}"

    def get_cost_amount(self, sales_amount: Decimal) -> Decimal:
        """原価金額を計算

        Args:
            sales_amount: 売上金額（率計算用）

        Returns:
            原価金額
        """
        if self.cost_category.cost_type == CostCategory.CostType.FIXED:
            # 固定金額
            if self.amount is not None:
                return self.amount
            return self.cost_category.default_amount
        else:
            # 売上比率
            rate = self.rate if self.rate is not None else self.cost_category.default_rate
            return (sales_amount * rate).quantize(Decimal('1'))


class MarginRule(TenantModel):
    """マージン計算ルール

    商品・コース・パック・講師ごとにマージン計算方式を定義
    優先順位: 講師 > 商品 > パック > コース > デフォルト
    """

    class CalculationType(models.TextChoices):
        PERCENTAGE = 'percentage', '割合のみ'
        FIXED = 'fixed', '固定金額のみ'
        MIXED = 'mixed', '混合（固定＋割合）'

    class FixedMarginTarget(models.TextChoices):
        SCHOOL = 'school', '校舎'
        BRAND = 'brand', 'ブランド'

    class RuleTarget(models.TextChoices):
        DEFAULT = 'default', 'デフォルト'
        PRODUCT = 'product', '商品'
        COURSE = 'course', 'コース'
        PACK = 'pack', 'パック'
        INSTRUCTOR = 'instructor', '講師'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ルール対象タイプ
    rule_target = models.CharField(
        'ルール対象',
        max_length=20,
        choices=RuleTarget.choices,
        default=RuleTarget.DEFAULT
    )

    # 商品へのリンク
    product = models.OneToOneField(
        'contracts.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='margin_rule',
        verbose_name='商品'
    )

    # コースへのリンク
    course = models.OneToOneField(
        'contracts.Course',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='margin_rule',
        verbose_name='コース'
    )

    # パックへのリンク
    pack = models.OneToOneField(
        'contracts.Pack',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='margin_rule',
        verbose_name='パック'
    )

    # 講師へのリンク（スタッフユーザー）
    instructor = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='margin_rules',
        verbose_name='講師',
        limit_choices_to={'role__in': ['staff', 'instructor', 'admin']}
    )

    name = models.CharField(
        'ルール名',
        max_length=100,
        blank=True,
        help_text='識別用（例: 授業料マージン、教材費マージン）'
    )

    # マージン計算方式
    calculation_type = models.CharField(
        '計算方式',
        max_length=20,
        choices=CalculationType.choices,
        default=CalculationType.PERCENTAGE
    )

    # マージン率（純利益からマージン原資を算出）
    margin_rate = models.DecimalField(
        'マージン率',
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.30'),
        help_text='純利益のうちマージン原資とする割合（例: 0.30 = 30%）'
    )

    # 固定マージン（混合方式の場合に使用）
    fixed_margin_amount = models.DecimalField(
        '固定マージン額',
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text='固定金額マージン（混合方式で使用）'
    )
    fixed_margin_target = models.CharField(
        '固定マージン対象',
        max_length=20,
        choices=FixedMarginTarget.choices,
        default=FixedMarginTarget.BRAND,
        help_text='固定マージンの配分先'
    )

    # 配分率（校舎＋ブランド=100%）
    school_distribution_rate = models.DecimalField(
        '校舎配分率',
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.60'),
        help_text='マージン原資のうち校舎への配分率（例: 0.60 = 60%）'
    )
    brand_distribution_rate = models.DecimalField(
        'ブランド配分率',
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.40'),
        help_text='マージン原資のうちブランドへの配分率（例: 0.40 = 40%）'
    )

    # デフォルトルールかどうか
    is_default = models.BooleanField(
        'デフォルトルール',
        default=False,
        help_text='対象が設定されていない場合のデフォルトとして使用'
    )

    # 優先順位（数字が大きいほど優先）
    priority = models.IntegerField(
        '優先順位',
        default=0,
        help_text='同じ対象タイプ内での優先順位（大きいほど優先）'
    )

    description = models.TextField('説明', blank=True)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'pricing_margin_rules'
        verbose_name = 'マージン計算ルール'
        verbose_name_plural = 'マージン計算ルール'
        ordering = ['-priority', 'rule_target']

    def __str__(self):
        if self.instructor:
            return f"{self.instructor.name} マージンルール"
        if self.product:
            return f"{self.product.product_name} マージンルール"
        if self.course:
            return f"{self.course.name} マージンルール"
        if self.pack:
            return f"{self.pack.name} マージンルール"
        return self.name or 'デフォルトマージンルール'

    def clean(self):
        from django.core.exceptions import ValidationError
        # 配分率の合計が100%かチェック
        total_rate = self.school_distribution_rate + self.brand_distribution_rate
        if abs(total_rate - Decimal('1')) > Decimal('0.0001'):
            raise ValidationError({
                'school_distribution_rate': '校舎配分率とブランド配分率の合計は100%である必要があります',
                'brand_distribution_rate': '校舎配分率とブランド配分率の合計は100%である必要があります',
            })

        # rule_targetと実際のリンクの整合性チェック
        if self.rule_target == self.RuleTarget.PRODUCT and not self.product:
            raise ValidationError({'product': '商品を選択してください'})
        if self.rule_target == self.RuleTarget.COURSE and not self.course:
            raise ValidationError({'course': 'コースを選択してください'})
        if self.rule_target == self.RuleTarget.PACK and not self.pack:
            raise ValidationError({'pack': 'パックを選択してください'})
        if self.rule_target == self.RuleTarget.INSTRUCTOR and not self.instructor:
            raise ValidationError({'instructor': '講師を選択してください'})

    def calculate_margin(
        self,
        sales_amount: Decimal,
        total_cost: Decimal
    ) -> dict:
        """マージンを計算

        Args:
            sales_amount: 売上金額
            total_cost: 原価合計

        Returns:
            計算結果の辞書
        """
        # STEP 1: 純利益を計算
        net_profit = sales_amount - total_cost

        if net_profit <= 0:
            return {
                'sales_amount': sales_amount,
                'total_cost': total_cost,
                'net_profit': net_profit,
                'margin_pool': Decimal('0'),
                'school_margin': Decimal('0'),
                'brand_margin': Decimal('0'),
                'fixed_margin': Decimal('0'),
            }

        # STEP 2: マージン原資を計算
        if self.calculation_type == self.CalculationType.FIXED:
            # 固定金額のみ
            margin_pool = min(self.fixed_margin_amount, net_profit)
            fixed_margin = margin_pool
            distributable = Decimal('0')
        elif self.calculation_type == self.CalculationType.MIXED:
            # 混合: 固定金額を先に引いて、残りに率を掛ける
            fixed_margin = min(self.fixed_margin_amount, net_profit)
            remaining_profit = net_profit - fixed_margin
            distributable = (remaining_profit * self.margin_rate).quantize(Decimal('1'))
            margin_pool = fixed_margin + distributable
        else:
            # 割合のみ
            margin_pool = (net_profit * self.margin_rate).quantize(Decimal('1'))
            fixed_margin = Decimal('0')
            distributable = margin_pool

        # STEP 3: 配分計算
        if self.calculation_type == self.CalculationType.FIXED:
            # 固定の場合は対象に全額
            if self.fixed_margin_target == self.FixedMarginTarget.SCHOOL:
                school_margin = margin_pool
                brand_margin = Decimal('0')
            else:
                school_margin = Decimal('0')
                brand_margin = margin_pool
        elif self.calculation_type == self.CalculationType.MIXED:
            # 混合: 固定分は対象に、残りは配分率で
            school_margin = (distributable * self.school_distribution_rate).quantize(Decimal('1'))
            brand_margin = (distributable * self.brand_distribution_rate).quantize(Decimal('1'))
            if self.fixed_margin_target == self.FixedMarginTarget.SCHOOL:
                school_margin += fixed_margin
            else:
                brand_margin += fixed_margin
        else:
            # 割合のみ
            school_margin = (margin_pool * self.school_distribution_rate).quantize(Decimal('1'))
            brand_margin = (margin_pool * self.brand_distribution_rate).quantize(Decimal('1'))

        return {
            'sales_amount': sales_amount,
            'total_cost': total_cost,
            'net_profit': net_profit,
            'margin_pool': margin_pool,
            'school_margin': school_margin,
            'brand_margin': brand_margin,
            'fixed_margin': fixed_margin,
        }


class MarginCalculation(TenantModel):
    """マージン計算結果

    請求明細ごとのマージン計算結果を保存
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', '下書き'
        CONFIRMED = 'confirmed', '確定'
        PAID = 'paid', '支払済'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 関連
    invoice_line = models.OneToOneField(
        'billing.InvoiceLine',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='margin_calculation',
        verbose_name='請求明細'
    )
    product = models.ForeignKey(
        'contracts.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='margin_calculations',
        verbose_name='商品'
    )
    course = models.ForeignKey(
        'contracts.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='margin_calculations',
        verbose_name='コース'
    )
    pack = models.ForeignKey(
        'contracts.Pack',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='margin_calculations',
        verbose_name='パック'
    )
    instructor = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='margin_calculations',
        verbose_name='講師'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='margin_calculations',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='margin_calculations',
        verbose_name='ブランド'
    )
    margin_rule = models.ForeignKey(
        MarginRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calculations',
        verbose_name='使用ルール'
    )

    # 計算対象期間
    calculation_year = models.IntegerField('計算年')
    calculation_month = models.IntegerField('計算月')

    # 金額
    sales_amount = models.DecimalField('売上', max_digits=12, decimal_places=0)
    total_cost = models.DecimalField('原価合計', max_digits=12, decimal_places=0)
    net_profit = models.DecimalField('純利益', max_digits=12, decimal_places=0)
    margin_pool = models.DecimalField('マージン原資', max_digits=12, decimal_places=0)

    # マージン配分
    school_margin = models.DecimalField('校舎マージン', max_digits=12, decimal_places=0)
    brand_margin = models.DecimalField('ブランドマージン', max_digits=12, decimal_places=0)
    fixed_margin = models.DecimalField(
        '固定マージン',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='固定マージン部分（混合方式の場合）'
    )

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    confirmed_at = models.DateTimeField('確定日時', null=True, blank=True)
    confirmed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_margin_calculations',
        verbose_name='確定者'
    )

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'pricing_margin_calculations'
        verbose_name = 'マージン計算結果'
        verbose_name_plural = 'マージン計算結果'
        ordering = ['-calculation_year', '-calculation_month', '-created_at']
        indexes = [
            models.Index(fields=['calculation_year', 'calculation_month']),
            models.Index(fields=['school', 'calculation_year', 'calculation_month']),
            models.Index(fields=['brand', 'calculation_year', 'calculation_month']),
        ]

    def __str__(self):
        product_name = self.product.product_name if self.product else '不明'
        return f"{self.calculation_year}/{self.calculation_month} - {product_name}"


class MarginCalculationCostLine(TenantModel):
    """マージン計算の原価明細

    どの原価項目がいくらだったかを記録
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    margin_calculation = models.ForeignKey(
        MarginCalculation,
        on_delete=models.CASCADE,
        related_name='cost_lines',
        verbose_name='マージン計算'
    )
    cost_category = models.ForeignKey(
        CostCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calculation_lines',
        verbose_name='原価項目'
    )

    cost_name = models.CharField('原価項目名', max_length=100)
    cost_amount = models.DecimalField('原価金額', max_digits=12, decimal_places=0)

    class Meta:
        db_table = 'pricing_margin_calculation_cost_lines'
        verbose_name = 'マージン計算原価明細'
        verbose_name_plural = 'マージン計算原価明細'

    def __str__(self):
        return f"{self.cost_name}: {self.cost_amount:,}円"


class MonthlyMarginSummary(TenantModel):
    """月次マージン集計

    校舎×ブランド×月ごとの集計
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='monthly_margin_summaries',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='monthly_margin_summaries',
        verbose_name='ブランド'
    )

    # 集計期間
    year = models.IntegerField('年')
    month = models.IntegerField('月')

    # 集計値
    total_sales = models.DecimalField('売上合計', max_digits=14, decimal_places=0, default=0)
    total_cost = models.DecimalField('原価合計', max_digits=14, decimal_places=0, default=0)
    total_net_profit = models.DecimalField('純利益合計', max_digits=14, decimal_places=0, default=0)
    total_margin_pool = models.DecimalField('マージン原資合計', max_digits=14, decimal_places=0, default=0)
    total_school_margin = models.DecimalField('校舎マージン合計', max_digits=14, decimal_places=0, default=0)
    total_brand_margin = models.DecimalField('ブランドマージン合計', max_digits=14, decimal_places=0, default=0)

    # 件数
    calculation_count = models.IntegerField('計算件数', default=0)

    # 集計日時
    aggregated_at = models.DateTimeField('集計日時', auto_now=True)

    class Meta:
        db_table = 'pricing_monthly_margin_summaries'
        verbose_name = '月次マージン集計'
        verbose_name_plural = '月次マージン集計'
        unique_together = ['tenant_id', 'school', 'brand', 'year', 'month']
        ordering = ['-year', '-month']

    def __str__(self):
        brand_name = self.brand.name if self.brand else '全ブランド'
        return f"{self.year}/{self.month} - {self.school.name} ({brand_name})"


def get_margin_rule(
    tenant_id,
    product=None,
    course=None,
    pack=None,
    instructor=None
) -> MarginRule | None:
    """適用するマージンルールを取得

    優先順位: 講師 > 商品 > パック > コース > デフォルト

    Args:
        tenant_id: テナントID
        product: 商品（Product）
        course: コース（Course）
        pack: パック（Pack）
        instructor: 講師（Staff）

    Returns:
        適用するMarginRule、見つからない場合はNone
    """
    base_qs = MarginRule.objects.filter(
        tenant_id=tenant_id,
        is_active=True,
        deleted_at__isnull=True
    )

    # 1. 講師ルールをチェック
    if instructor:
        rule = base_qs.filter(
            rule_target=MarginRule.RuleTarget.INSTRUCTOR,
            instructor=instructor
        ).order_by('-priority').first()
        if rule:
            return rule

    # 2. 商品ルールをチェック
    if product:
        rule = base_qs.filter(
            rule_target=MarginRule.RuleTarget.PRODUCT,
            product=product
        ).first()
        if rule:
            return rule

    # 3. パックルールをチェック
    if pack:
        rule = base_qs.filter(
            rule_target=MarginRule.RuleTarget.PACK,
            pack=pack
        ).first()
        if rule:
            return rule

    # 4. コースルールをチェック
    if course:
        rule = base_qs.filter(
            rule_target=MarginRule.RuleTarget.COURSE,
            course=course
        ).first()
        if rule:
            return rule

    # 5. デフォルトルールをチェック
    return base_qs.filter(
        rule_target=MarginRule.RuleTarget.DEFAULT,
        is_default=True
    ).order_by('-priority').first()

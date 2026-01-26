"""
Pricing Admin - マージン計算管理画面
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CostCategory,
    ProductCost,
    MarginRule,
    MarginCalculation,
    MarginCalculationCostLine,
    MonthlyMarginSummary,
)


@admin.register(CostCategory)
class CostCategoryAdmin(admin.ModelAdmin):
    """原価項目カテゴリ管理"""

    list_display = [
        'code',
        'name',
        'cost_type',
        'default_amount_display',
        'default_rate_display',
        'sort_order',
        'is_active',
    ]
    list_filter = ['cost_type', 'is_active', 'tenant_ref']
    search_fields = ['code', 'name']
    ordering = ['sort_order', 'code']

    fieldsets = (
        (None, {
            'fields': ('tenant_ref', 'code', 'name', 'description')
        }),
        ('原価設定', {
            'fields': ('cost_type', 'default_amount', 'default_rate')
        }),
        ('表示設定', {
            'fields': ('sort_order', 'is_active')
        }),
    )

    def default_amount_display(self, obj):
        if obj.cost_type == CostCategory.CostType.FIXED:
            return f"¥{obj.default_amount:,.0f}"
        return "-"
    default_amount_display.short_description = 'デフォルト金額'

    def default_rate_display(self, obj):
        if obj.cost_type == CostCategory.CostType.PERCENTAGE:
            return f"{obj.default_rate * 100:.2f}%"
        return "-"
    default_rate_display.short_description = 'デフォルト率'


@admin.register(ProductCost)
class ProductCostAdmin(admin.ModelAdmin):
    """商品原価管理"""

    list_display = [
        'product',
        'cost_category',
        'amount_display',
        'rate_display',
        'is_active',
    ]
    list_filter = ['cost_category', 'is_active', 'tenant_ref']
    search_fields = ['product__product_name', 'cost_category__name']
    raw_id_fields = ['product', 'cost_category']

    def amount_display(self, obj):
        if obj.amount is not None:
            return f"¥{obj.amount:,.0f}"
        return "(デフォルト)"
    amount_display.short_description = '金額'

    def rate_display(self, obj):
        if obj.rate is not None:
            return f"{obj.rate * 100:.2f}%"
        return "(デフォルト)"
    rate_display.short_description = '率'


@admin.register(MarginRule)
class MarginRuleAdmin(admin.ModelAdmin):
    """マージン計算ルール管理"""

    list_display = [
        '__str__',
        'rule_target',
        'calculation_type',
        'margin_rate_display',
        'school_rate_display',
        'brand_rate_display',
        'fixed_margin_display',
        'priority',
        'is_default',
        'is_active',
    ]
    list_filter = [
        'rule_target',
        'calculation_type',
        'is_default',
        'is_active',
        'tenant_ref',
    ]
    search_fields = [
        'name',
        'product__product_name',
        'course__name',
        'pack__name',
        'instructor__name',
    ]
    raw_id_fields = ['product', 'course', 'pack', 'instructor']
    ordering = ['-priority', 'rule_target']

    fieldsets = (
        (None, {
            'fields': ('tenant_ref', 'name', 'rule_target')
        }),
        ('対象設定', {
            'fields': ('product', 'course', 'pack', 'instructor'),
            'description': 'ルール対象に応じて1つだけ選択してください'
        }),
        ('マージン計算設定', {
            'fields': (
                'calculation_type',
                'margin_rate',
                'fixed_margin_amount',
                'fixed_margin_target',
            )
        }),
        ('配分設定', {
            'fields': ('school_distribution_rate', 'brand_distribution_rate')
        }),
        ('その他', {
            'fields': ('priority', 'is_default', 'description', 'is_active')
        }),
    )

    def margin_rate_display(self, obj):
        return f"{obj.margin_rate * 100:.1f}%"
    margin_rate_display.short_description = 'マージン率'

    def school_rate_display(self, obj):
        return f"{obj.school_distribution_rate * 100:.0f}%"
    school_rate_display.short_description = '校舎'

    def brand_rate_display(self, obj):
        return f"{obj.brand_distribution_rate * 100:.0f}%"
    brand_rate_display.short_description = 'ブランド'

    def fixed_margin_display(self, obj):
        if obj.calculation_type in ['fixed', 'mixed']:
            target = '校舎' if obj.fixed_margin_target == 'school' else 'ブランド'
            return f"¥{obj.fixed_margin_amount:,.0f} ({target})"
        return "-"
    fixed_margin_display.short_description = '固定マージン'


class MarginCalculationCostLineInline(admin.TabularInline):
    """マージン計算原価明細インライン"""

    model = MarginCalculationCostLine
    extra = 0
    readonly_fields = ['cost_category', 'cost_name', 'cost_amount']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MarginCalculation)
class MarginCalculationAdmin(admin.ModelAdmin):
    """マージン計算結果管理"""

    list_display = [
        'calculation_period',
        'product',
        'school',
        'sales_display',
        'cost_display',
        'profit_display',
        'school_margin_display',
        'brand_margin_display',
        'status',
    ]
    list_filter = [
        'status',
        'calculation_year',
        'calculation_month',
        'school',
        'brand',
        'tenant_ref',
    ]
    search_fields = [
        'product__product_name',
        'school__name',
        'brand__name',
    ]
    readonly_fields = [
        'sales_amount',
        'total_cost',
        'net_profit',
        'margin_pool',
        'school_margin',
        'brand_margin',
        'fixed_margin',
        'confirmed_at',
        'confirmed_by',
    ]
    inlines = [MarginCalculationCostLineInline]
    date_hierarchy = 'created_at'
    ordering = ['-calculation_year', '-calculation_month', '-created_at']

    fieldsets = (
        ('基本情報', {
            'fields': (
                'tenant_ref',
                ('calculation_year', 'calculation_month'),
                'invoice_line',
            )
        }),
        ('対象', {
            'fields': ('product', 'course', 'pack', 'instructor', 'school', 'brand')
        }),
        ('計算結果', {
            'fields': (
                'margin_rule',
                ('sales_amount', 'total_cost'),
                ('net_profit', 'margin_pool'),
                ('school_margin', 'brand_margin', 'fixed_margin'),
            )
        }),
        ('ステータス', {
            'fields': ('status', 'confirmed_at', 'confirmed_by', 'notes')
        }),
    )

    def calculation_period(self, obj):
        return f"{obj.calculation_year}/{obj.calculation_month:02d}"
    calculation_period.short_description = '期間'

    def sales_display(self, obj):
        return f"¥{obj.sales_amount:,.0f}"
    sales_display.short_description = '売上'

    def cost_display(self, obj):
        return f"¥{obj.total_cost:,.0f}"
    cost_display.short_description = '原価'

    def profit_display(self, obj):
        color = 'green' if obj.net_profit > 0 else 'red'
        return format_html(
            '<span style="color: {}">{}</span>',
            color,
            f"¥{obj.net_profit:,.0f}"
        )
    profit_display.short_description = '純利益'

    def school_margin_display(self, obj):
        return f"¥{obj.school_margin:,.0f}"
    school_margin_display.short_description = '校舎マージン'

    def brand_margin_display(self, obj):
        return f"¥{obj.brand_margin:,.0f}"
    brand_margin_display.short_description = 'ブランドマージン'


@admin.register(MonthlyMarginSummary)
class MonthlyMarginSummaryAdmin(admin.ModelAdmin):
    """月次マージン集計管理"""

    list_display = [
        'period',
        'school',
        'brand',
        'total_sales_display',
        'total_cost_display',
        'total_profit_display',
        'total_school_margin_display',
        'total_brand_margin_display',
        'calculation_count',
        'aggregated_at',
    ]
    list_filter = ['year', 'month', 'school', 'brand', 'tenant_ref']
    search_fields = ['school__name', 'brand__name']
    ordering = ['-year', '-month', 'school__name']

    readonly_fields = [
        'total_sales',
        'total_cost',
        'total_net_profit',
        'total_margin_pool',
        'total_school_margin',
        'total_brand_margin',
        'calculation_count',
        'aggregated_at',
    ]

    def period(self, obj):
        return f"{obj.year}/{obj.month:02d}"
    period.short_description = '期間'

    def total_sales_display(self, obj):
        return f"¥{obj.total_sales:,.0f}"
    total_sales_display.short_description = '売上合計'

    def total_cost_display(self, obj):
        return f"¥{obj.total_cost:,.0f}"
    total_cost_display.short_description = '原価合計'

    def total_profit_display(self, obj):
        return f"¥{obj.total_net_profit:,.0f}"
    total_profit_display.short_description = '純利益合計'

    def total_school_margin_display(self, obj):
        return f"¥{obj.total_school_margin:,.0f}"
    total_school_margin_display.short_description = '校舎マージン'

    def total_brand_margin_display(self, obj):
        return f"¥{obj.total_brand_margin:,.0f}"
    total_brand_margin_display.short_description = 'ブランドマージン'

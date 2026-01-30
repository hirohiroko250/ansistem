"""
Product Admin - 商品マスタ管理
ProductAdmin, ProductPriceAdmin, ProductPriceInline
"""
from datetime import datetime
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import Product, ProductPrice


# =============================================================================
# T05: 商品価格マスタ（インライン用）
# =============================================================================
class ProductPriceInline(admin.StackedInline):
    """商品詳細画面で月毎料金を編集するためのインライン"""
    model = ProductPrice
    extra = 1  # 料金設定がない場合に1件分の入力フォームを表示
    max_num = 1
    can_delete = True
    verbose_name = '月別料金設定'
    verbose_name_plural = '月別料金設定'

    fieldsets = (
        ('【初月料金】入会月別料金（〜月入会者）', {
            'fields': (
                ('enrollment_price_apr', 'enrollment_price_may', 'enrollment_price_jun'),
                ('enrollment_price_jul', 'enrollment_price_aug', 'enrollment_price_sep'),
                ('enrollment_price_oct', 'enrollment_price_nov', 'enrollment_price_dec'),
                ('enrollment_price_jan', 'enrollment_price_feb', 'enrollment_price_mar'),
            ),
            'description': '★入会した月（初月）に請求される金額。例：4月入会者は「4月入会者料金」が初月に適用されます。',
        }),
        ('【2ヶ月目以降】請求月別料金（〜月）', {
            'fields': (
                ('billing_price_apr', 'billing_price_may', 'billing_price_jun'),
                ('billing_price_jul', 'billing_price_aug', 'billing_price_sep'),
                ('billing_price_oct', 'billing_price_nov', 'billing_price_dec'),
                ('billing_price_jan', 'billing_price_feb', 'billing_price_mar'),
            ),
            'description': '★2ヶ月目以降に請求される金額。例：4月入会者の5月請求には「5月請求料金」が適用されます。',
        }),
    )

    def get_extra(self, request, obj=None, **kwargs):
        """既存の料金設定がある場合はextra=0、ない場合はextra=1"""
        if obj and obj.prices.exists():
            return 0
        return 1


# =============================================================================
# T03: 商品マスタ
# =============================================================================
@admin.register(Product)
class ProductAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'product_code', 'product_name', 'item_type', 'base_price',
        'enrollment_price_display', 'billing_price_display',
        'is_one_time', 'is_enrollment_tuition', 'has_monthly_prices', 'is_active', 'tenant_ref'
    ]
    list_filter = [
        'tenant_ref', 'item_type', 'is_one_time', 'is_enrollment_tuition',
        'is_first_year_free', 'is_first_fiscal_year_free', 'is_active', 'brand', 'grade'
    ]
    search_fields = ['product_code', 'product_name']
    ordering = ['sort_order', 'product_code']
    raw_id_fields = ['brand', 'grade', 'tenant_ref']

    fieldsets = (
        ('基本情報', {
            'fields': ('product_code', 'product_name', 'product_name_short', 'item_type')
        }),
        ('関連', {
            'fields': ('brand', 'grade')
        }),
        ('価格設定', {
            'fields': ('base_price', 'tax_rate', 'tax_type', 'mile', 'discount_max')
        }),
        ('料金特性', {
            'fields': ('is_one_time', 'is_first_year_free', 'is_first_fiscal_year_free', 'is_enrollment_tuition', 'per_ticket_price'),
            'description': '1年目無料: 契約から12ヶ月間無料。初年度無料: 入会年度末(3月)まで無料。'
        }),
        ('【初月料金】入会月別料金（〜月入会者）', {
            'fields': (
                ('enrollment_price_apr', 'enrollment_price_may', 'enrollment_price_jun'),
                ('enrollment_price_jul', 'enrollment_price_aug', 'enrollment_price_sep'),
                ('enrollment_price_oct', 'enrollment_price_nov', 'enrollment_price_dec'),
                ('enrollment_price_jan', 'enrollment_price_feb', 'enrollment_price_mar'),
            ),
            'description': '★入会した月（初月）に請求される金額。例：4月入会者は「4月入会者料金」が初月に適用されます。',
        }),
        ('【2ヶ月目以降】請求月別料金（〜月）', {
            'fields': (
                ('billing_price_apr', 'billing_price_may', 'billing_price_jun'),
                ('billing_price_jul', 'billing_price_aug', 'billing_price_sep'),
                ('billing_price_oct', 'billing_price_nov', 'billing_price_dec'),
                ('billing_price_jan', 'billing_price_feb', 'billing_price_mar'),
            ),
            'description': '★2ヶ月目以降に請求される金額。例：4月入会者の5月請求には「5月請求料金」が適用されます。',
        }),
        ('その他', {
            'fields': ('description', 'sort_order', 'is_active', 'tenant_ref')
        }),
    )

    @admin.display(boolean=True, description='月別料金')
    def has_monthly_prices(self, obj):
        """月別料金が設定されているかどうか（Product直接参照）"""
        return any([
            obj.enrollment_price_jan, obj.enrollment_price_feb, obj.enrollment_price_mar,
            obj.enrollment_price_apr, obj.enrollment_price_may, obj.enrollment_price_jun,
            obj.enrollment_price_jul, obj.enrollment_price_aug, obj.enrollment_price_sep,
            obj.enrollment_price_oct, obj.enrollment_price_nov, obj.enrollment_price_dec,
            obj.billing_price_jan, obj.billing_price_feb, obj.billing_price_mar,
            obj.billing_price_apr, obj.billing_price_may, obj.billing_price_jun,
            obj.billing_price_jul, obj.billing_price_aug, obj.billing_price_sep,
            obj.billing_price_oct, obj.billing_price_nov, obj.billing_price_dec,
        ])

    @admin.display(description='初月料金(今月)')
    def enrollment_price_display(self, obj):
        """今月の初月料金を表示（Product直接参照）"""
        month_map = {
            1: obj.enrollment_price_jan,
            2: obj.enrollment_price_feb,
            3: obj.enrollment_price_mar,
            4: obj.enrollment_price_apr,
            5: obj.enrollment_price_may,
            6: obj.enrollment_price_jun,
            7: obj.enrollment_price_jul,
            8: obj.enrollment_price_aug,
            9: obj.enrollment_price_sep,
            10: obj.enrollment_price_oct,
            11: obj.enrollment_price_nov,
            12: obj.enrollment_price_dec,
        }
        current_month = datetime.now().month
        value = month_map.get(current_month)
        if value is not None:
            return f'¥{value:,.0f}'
        return '-'

    @admin.display(description='2ヶ月目以降(今月)')
    def billing_price_display(self, obj):
        """今月の2ヶ月目以降料金を表示（Product直接参照）"""
        month_map = {
            1: obj.billing_price_jan,
            2: obj.billing_price_feb,
            3: obj.billing_price_mar,
            4: obj.billing_price_apr,
            5: obj.billing_price_may,
            6: obj.billing_price_jun,
            7: obj.billing_price_jul,
            8: obj.billing_price_aug,
            9: obj.billing_price_sep,
            10: obj.billing_price_oct,
            11: obj.billing_price_nov,
            12: obj.billing_price_dec,
        }
        current_month = datetime.now().month
        value = month_map.get(current_month)
        if value is not None:
            return f'¥{value:,.0f}'
        return '-'

    def save_formset(self, request, form, formset, change):
        """インラインフォームセット保存時にtenant_refを自動設定"""
        instances = formset.save(commit=False)
        for instance in instances:
            # ProductPriceの場合、親Productのtenant_refを継承
            if hasattr(instance, 'tenant_ref_id') and not instance.tenant_ref_id:
                if hasattr(form.instance, 'tenant_ref_id'):
                    instance.tenant_ref_id = form.instance.tenant_ref_id
            instance.save()
        formset.save_m2m()

    csv_import_fields = {
        '請求ID': 'product_code',
        '明細表記': 'product_name',
        '契約名': 'product_name_short',
        '請求カテゴリ': 'item_type',
        '契約ブランドコード': 'brand__brand_code',
        '教室コード': 'school__school_code',
        '学年コード': 'grade__grade_code',
        '保護者表示用金額': 'base_price',
        '税率': 'tax_rate',
        '税区分': 'tax_type',
        '一回きり': 'is_one_time',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['請求ID', '明細表記']
    csv_unique_fields = ['product_code']
    csv_export_fields = [
        'product_code', 'product_name', 'product_name_short', 'item_type',
        'brand.brand_name', 'school.school_name', 'grade.grade_name',
        'base_price', 'tax_rate', 'tax_type', 'is_one_time',
        'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'product_code': '請求ID',
        'product_name': '明細表記',
        'product_name_short': '契約名',
        'item_type': '請求カテゴリ',
        'brand.brand_name': '契約ブランド名',
        'school.school_name': '校舎名',
        'grade.grade_name': '学年名',
        'base_price': '保護者表示用金額',
        'tax_rate': '税率',
        'tax_type': '税区分',
        'is_one_time': '一回きり',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T05: 商品価格マスタ（月別料金設定）
# =============================================================================
@admin.register(ProductPrice)
class ProductPriceAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'product', 'get_product_code',
        'enrollment_price_apr', 'billing_price_apr', 'is_active'
    ]
    list_filter = ['is_active', 'product__brand', 'product__item_type']
    search_fields = ['product__product_code', 'product__product_name']
    ordering = ['product__product_code']
    raw_id_fields = ['product', 'tenant_ref']

    fieldsets = (
        ('商品情報', {
            'fields': ('product', 'is_active')
        }),
        ('【初月料金】入会月別料金（〜月入会者）', {
            'fields': (
                ('enrollment_price_apr', 'enrollment_price_may', 'enrollment_price_jun'),
                ('enrollment_price_jul', 'enrollment_price_aug', 'enrollment_price_sep'),
                ('enrollment_price_oct', 'enrollment_price_nov', 'enrollment_price_dec'),
                ('enrollment_price_jan', 'enrollment_price_feb', 'enrollment_price_mar'),
            ),
            'description': '★入会した月（初月）に請求される金額。例：4月入会者は「4月入会者料金」が初月に適用されます。'
        }),
        ('【2ヶ月目以降】請求月別料金（〜月）', {
            'fields': (
                ('billing_price_apr', 'billing_price_may', 'billing_price_jun'),
                ('billing_price_jul', 'billing_price_aug', 'billing_price_sep'),
                ('billing_price_oct', 'billing_price_nov', 'billing_price_dec'),
                ('billing_price_jan', 'billing_price_feb', 'billing_price_mar'),
            ),
            'description': '★2ヶ月目以降に請求される金額。例：4月入会者の5月請求には「5月請求料金」が適用されます。'
        }),
    )

    def get_product_code(self, obj):
        return obj.product.product_code
    get_product_code.short_description = '商品コード'
    get_product_code.admin_order_field = 'product__product_code'

    csv_import_fields = {
        '商品コード': 'product__product_code',
        # 入会月別料金（〜月入会者 = 当月分）
        '1月入会者': 'enrollment_price_jan',
        '2月入会者': 'enrollment_price_feb',
        '3月入会者': 'enrollment_price_mar',
        '4月入会者': 'enrollment_price_apr',
        '5月入会者': 'enrollment_price_may',
        '6月入会者': 'enrollment_price_jun',
        '7月入会者': 'enrollment_price_jul',
        '8月入会者': 'enrollment_price_aug',
        '9月入会者': 'enrollment_price_sep',
        '10月入会者': 'enrollment_price_oct',
        '11月入会者': 'enrollment_price_nov',
        '12月入会者': 'enrollment_price_dec',
        # 請求月別料金（〜月 = 次月以降）
        '1月': 'billing_price_jan',
        '2月': 'billing_price_feb',
        '3月': 'billing_price_mar',
        '4月': 'billing_price_apr',
        '5月': 'billing_price_may',
        '6月': 'billing_price_jun',
        '7月': 'billing_price_jul',
        '8月': 'billing_price_aug',
        '9月': 'billing_price_sep',
        '10月': 'billing_price_oct',
        '11月': 'billing_price_nov',
        '12月': 'billing_price_dec',
        '有効': 'is_active',
    }
    csv_required_fields = ['商品コード']
    csv_unique_fields = ['product__product_code']
    csv_export_fields = [
        'product.product_code', 'product.product_name',
        'enrollment_price_apr', 'enrollment_price_may', 'enrollment_price_jun',
        'enrollment_price_jul', 'enrollment_price_aug', 'enrollment_price_sep',
        'enrollment_price_oct', 'enrollment_price_nov', 'enrollment_price_dec',
        'enrollment_price_jan', 'enrollment_price_feb', 'enrollment_price_mar',
        'billing_price_apr', 'billing_price_may', 'billing_price_jun',
        'billing_price_jul', 'billing_price_aug', 'billing_price_sep',
        'billing_price_oct', 'billing_price_nov', 'billing_price_dec',
        'billing_price_jan', 'billing_price_feb', 'billing_price_mar',
        'is_active',
    ]
    csv_export_headers = {
        'product.product_code': '商品コード',
        'product.product_name': '商品名',
        'enrollment_price_apr': '4月入会者', 'enrollment_price_may': '5月入会者',
        'enrollment_price_jun': '6月入会者', 'enrollment_price_jul': '7月入会者',
        'enrollment_price_aug': '8月入会者', 'enrollment_price_sep': '9月入会者',
        'enrollment_price_oct': '10月入会者', 'enrollment_price_nov': '11月入会者',
        'enrollment_price_dec': '12月入会者', 'enrollment_price_jan': '1月入会者',
        'enrollment_price_feb': '2月入会者', 'enrollment_price_mar': '3月入会者',
        'billing_price_apr': '4月', 'billing_price_may': '5月',
        'billing_price_jun': '6月', 'billing_price_jul': '7月',
        'billing_price_aug': '8月', 'billing_price_sep': '9月',
        'billing_price_oct': '10月', 'billing_price_nov': '11月',
        'billing_price_dec': '12月', 'billing_price_jan': '1月',
        'billing_price_feb': '2月', 'billing_price_mar': '3月',
        'is_active': '有効',
    }

from datetime import datetime
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from apps.core.admin_csv import CSVImportExportMixin
from .models import (
    Product, ProductPrice, ProductSet, ProductSetItem,
    Discount, Course, CourseItem,
    Pack, PackCourse, PackItem,
    Seminar, Certification, CourseRequiredSeminar,
    Contract, StudentItem, StudentDiscount, SeminarEnrollment, CertificationEnrollment,
    Ticket, CourseTicket, PackTicket,
    ContractHistory, SystemAuditLog,
    AdditionalTicket, AdditionalTicketDate,
)


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
        '税込': 'is_tax_included',
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
        'base_price', 'tax_rate', 'is_tax_included', 'is_one_time',
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
        'is_tax_included': '税込',
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


# =============================================================================
# T06: 商品セット
# =============================================================================
class ProductSetItemInline(admin.TabularInline):
    model = ProductSetItem
    extra = 1
    raw_id_fields = ['product']
    fields = ['product', 'quantity', 'price_override', 'sort_order', 'is_active']
    verbose_name = '商品（T03_契約全部から選択）'
    verbose_name_plural = '含まれる商品一覧'


@admin.register(ProductSet)
class ProductSetAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'set_code', 'set_name', 'brand', 'get_items_display', 'get_total_price', 'is_active'
    ]
    list_filter = ['brand', 'is_active']
    search_fields = ['set_code', 'set_name']
    raw_id_fields = ['brand', 'tenant_ref']
    inlines = [ProductSetItemInline]
    fieldsets = (
        (None, {
            'fields': ('tenant_ref', 'set_code', 'set_name', 'brand', 'description', 'sort_order', 'is_active')
        }),
    )

    def get_items_display(self, obj):
        return obj.get_items_display()
    get_items_display.short_description = '商品内容'

    def get_total_price(self, obj):
        return f"¥{obj.get_total_price():,.0f}"
    get_total_price.short_description = '合計金額'

    def save_formset(self, request, form, formset, change):
        """インラインのtenant情報を親から引き継ぐ"""
        instances = formset.save(commit=False)
        # 削除対象を処理（物理削除）
        for obj in formset.deleted_objects:
            obj.hard_delete()
        for instance in instances:
            if form.instance.tenant_id:
                instance.tenant_id = form.instance.tenant_id
                instance.tenant_ref = form.instance.tenant_ref
            instance.save()
        formset.save_m2m()

    csv_import_fields = {
        '会社コード': 'tenant_ref__tenant_code',
        'セットコード': 'set_code',
        'セット名': 'set_name',
        'ブランドコード': 'brand__brand_code',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['会社コード', 'セットコード', 'セット名']
    csv_unique_fields = ['set_code']
    csv_export_fields = [
        'tenant_ref.tenant_code', 'set_code', 'set_name', 'brand.brand_code', 'brand.brand_name',
        'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'tenant_ref.tenant_code': '会社コード',
        'set_code': 'セットコード',
        'set_name': 'セット名',
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }


@admin.register(ProductSetItem)
class ProductSetItemAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['product_set', 'product', 'quantity', 'price_override', 'is_active']
    list_filter = ['is_active', 'product_set']
    search_fields = ['product_set__set_name', 'product__product_name']
    raw_id_fields = ['product_set', 'product']

    csv_import_fields = {
        '会社コード': 'product_set__tenant_ref__tenant_code',
        'セットコード': 'product_set__set_code',
        '請求ID': 'product__product_code',
        '数量': 'quantity',
        '単価上書き': 'price_override',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['セットコード', '請求ID']
    csv_unique_fields = []
    csv_export_fields = [
        'product_set.tenant_ref.tenant_code', 'product_set.set_code', 'product_set.set_name',
        'product.product_code', 'product.product_name',
        'quantity', 'price_override', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'product_set.tenant_ref.tenant_code': '会社コード',
        'product_set.set_code': 'セットコード',
        'product_set.set_name': 'セット名',
        'product.product_code': '請求ID',
        'product.product_name': '明細表記',
        'quantity': '数量',
        'price_override': '単価上書き',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T07: 割引マスタ
# =============================================================================
@admin.register(Discount)
class DiscountAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'discount_code', 'discount_name', 'discount_type',
        'calculation_type', 'get_value_display', 'valid_from', 'valid_until', 'is_active', 'tenant_ref'
    ]
    list_filter = ['tenant_ref', 'discount_type', 'calculation_type', 'is_active']
    search_fields = ['discount_code', 'discount_name']
    ordering = ['discount_code']
    raw_id_fields = ['tenant_ref']

    fieldsets = (
        ('基本情報', {
            'fields': ('discount_code', 'discount_name', 'discount_type')
        }),
        ('割引設定', {
            'fields': ('calculation_type', 'value'),
            'description': '割合の場合は%、固定金額の場合は円で入力'
        }),
        ('適用期間', {
            'fields': ('valid_from', 'valid_until'),
            'description': '空欄の場合は常に適用'
        }),
        ('ステータス', {
            'fields': ('is_active', 'tenant_ref')
        }),
    )

    actions = ['create_task_for_discount']

    @admin.display(description='値')
    def get_value_display(self, obj):
        if obj.calculation_type == 'percentage':
            return f"{obj.value}%"
        else:
            return f"¥{obj.value:,.0f}"

    @admin.action(description='選択した割引の確認タスクを作成')
    def create_task_for_discount(self, request, queryset):
        from apps.tasks.models import Task
        created_count = 0
        for discount in queryset:
            Task.objects.create(
                tenant_id=discount.tenant_id,
                task_type='request',
                title=f'割引確認: {discount.discount_name}',
                description=f'割引コード: {discount.discount_code}\n'
                           f'割引種別: {discount.get_discount_type_display()}\n'
                           f'計算種別: {discount.get_calculation_type_display()}\n'
                           f'値: {discount.value}\n'
                           f'適用期間: {discount.valid_from or "なし"} 〜 {discount.valid_until or "なし"}',
                status='new',
                priority='normal',
                source_type='discount',
                source_id=discount.id,
                source_url=f'/admin/contracts/discount/{discount.id}/change/',
            )
            created_count += 1
        self.message_user(request, f'{created_count}件の確認タスクを作成しました。')

    csv_import_fields = {
        '割引コード': 'discount_code',
        '割引名': 'discount_name',
        '割引種別': 'discount_type',
        '計算種別': 'calculation_type',
        '値': 'value',
        '適用開始日': 'valid_from',
        '適用終了日': 'valid_until',
        '有効': 'is_active',
    }
    csv_required_fields = ['割引コード', '割引名', '値']
    csv_unique_fields = ['discount_code']
    csv_export_fields = [
        'discount_code', 'discount_name', 'discount_type', 'calculation_type',
        'value', 'valid_from', 'valid_until', 'is_active'
    ]
    csv_export_headers = {
        'discount_code': '割引コード',
        'discount_name': '割引名',
        'discount_type': '割引種別',
        'calculation_type': '計算種別',
        'value': '値',
        'valid_from': '適用開始日',
        'valid_until': '適用終了日',
        'is_active': '有効',
    }


# =============================================================================
# T08: コース
# =============================================================================
class CourseItemInline(admin.TabularInline):
    model = CourseItem
    extra = 1
    can_delete = True
    raw_id_fields = ['product']
    fields = ['product', 'quantity', 'price_override', 'sort_order', 'is_active']
    verbose_name = '商品（T03_契約全部から選択）'
    verbose_name_plural = 'T52_コース商品構成'


# CourseTicketInline will be defined after Ticket model admin


@admin.register(Course)
class CourseAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'course_code', 'course_name', 'brand', 'grade',
        'get_ticket_codes', 'product_set', 'course_price', 'is_visible', 'is_active'
    ]
    list_filter = ['brand', 'grade', 'is_visible', 'product_set', 'is_active']
    search_fields = ['course_code', 'course_name']
    raw_id_fields = ['brand', 'school', 'grade', 'product_set']
    list_editable = ['is_visible']  # 一覧から直接編集可能
    inlines = [CourseItemInline]  # CourseTicketInline added dynamically below
    ordering = ['brand', 'grade', 'course_code']
    actions = ['make_visible', 'make_invisible', 'apply_product_set']
    change_form_template = 'admin/contracts/course/change_form.html'

    def get_queryset(self, request):
        """チケット情報を効率的に取得"""
        return super().get_queryset(request).prefetch_related('course_tickets__ticket')

    @admin.display(description='チケットID')
    def get_ticket_codes(self, obj):
        """紐づくチケットIDを表示"""
        tickets = obj.course_tickets.filter(is_active=True).select_related('ticket')
        if tickets:
            return ', '.join([ct.ticket.ticket_code for ct in tickets if ct.ticket])
        return '-'

    @admin.action(description='選択したコースを表示する')
    def make_visible(self, request, queryset):
        updated = queryset.update(is_visible=True)
        self.message_user(request, f'{updated}件のコースを表示に設定しました。')

    @admin.action(description='選択したコースを非表示にする')
    def make_invisible(self, request, queryset):
        updated = queryset.update(is_visible=False)
        self.message_user(request, f'{updated}件のコースを非表示に設定しました。')

    @admin.action(description='商品セットを適用（CourseItemにコピー）')
    def apply_product_set(self, request, queryset):
        """選択したコースに紐づく商品セットの内容をCourseItemにコピー"""
        total_created = 0
        total_skipped = 0
        for course in queryset:
            if not course.product_set:
                continue
            for set_item in course.product_set.items.filter(is_active=True):
                # 既に同じ商品がCourseItemにあればスキップ
                existing = CourseItem.objects.filter(
                    course=course,
                    product=set_item.product
                ).exists()
                if existing:
                    total_skipped += 1
                    continue
                # CourseItemを作成
                CourseItem.objects.create(
                    course=course,
                    product=set_item.product,
                    quantity=set_item.quantity,
                    price_override=set_item.price_override,
                    sort_order=set_item.sort_order,
                    is_active=True,
                    tenant_id=course.tenant_id,
                    tenant_ref=course.tenant_ref,
                )
                total_created += 1
        self.message_user(
            request,
            f'{total_created}件の商品をコースに追加しました。（{total_skipped}件はスキップ）'
        )

    def response_change(self, request, obj):
        """詳細画面で「商品セット適用」ボタンが押された場合の処理"""
        if "_apply_product_set" in request.POST:
            if obj.product_set:
                created = 0
                skipped = 0
                for set_item in obj.product_set.items.filter(is_active=True):
                    existing = CourseItem.objects.filter(
                        course=obj,
                        product=set_item.product
                    ).exists()
                    if existing:
                        skipped += 1
                        continue
                    CourseItem.objects.create(
                        course=obj,
                        product=set_item.product,
                        quantity=set_item.quantity,
                        price_override=set_item.price_override,
                        sort_order=set_item.sort_order,
                        is_active=True,
                        tenant_id=obj.tenant_id,
                        tenant_ref=obj.tenant_ref,
                    )
                    created += 1
                self.message_user(
                    request,
                    f'商品セット「{obj.product_set.set_name}」から{created}件の商品を追加しました。（{skipped}件はスキップ）'
                )
            else:
                self.message_user(request, '商品セットが設定されていません。', level='warning')
            return HttpResponseRedirect(request.path)
        return super().response_change(request, obj)

    def save_formset(self, request, form, formset, change):
        """インラインのtenant情報を親から引き継ぐ"""
        instances = formset.save(commit=False)
        # 削除対象を処理（物理削除）
        for obj in formset.deleted_objects:
            obj.hard_delete()
        # 新規・更新対象を処理
        for instance in instances:
            if form.instance.tenant_id:
                instance.tenant_id = form.instance.tenant_id
                instance.tenant_ref = form.instance.tenant_ref
            instance.save()
        formset.save_m2m()

    csv_import_fields = {
        'コースコード': 'course_code',
        'コース名': 'course_name',
        'ブランドコード': 'brand__brand_code',
        '教室コード': 'school__school_code',
        '学年コード': 'grade__grade_code',
        'コース料金': 'course_price',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['コースコード', 'コース名']
    csv_unique_fields = ['course_code']
    csv_export_fields = [
        'course_code', 'course_name', 'brand.brand_name', 'school.school_name',
        'grade.grade_name', 'product_set.set_name', 'course_price',
        'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'course_code': 'コースコード',
        'course_name': 'コース名',
        'brand.brand_name': 'ブランド名',
        'school.school_name': '校舎名',
        'grade.grade_name': '学年名',
        'product_set.set_name': '商品セット',
        'course_price': 'コース料金',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T52: コース商品構成
# =============================================================================
@admin.register(CourseItem)
class CourseItemAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['course', 'product', 'quantity', 'price_override', 'is_active']
    list_filter = ['is_active', 'course']
    search_fields = ['course__course_name', 'product__product_name']
    raw_id_fields = ['course', 'product']

    csv_import_fields = {
        'コースコード': 'course__course_code',
        '商品コード': 'product__product_code',
        '数量': 'quantity',
        '単価上書き': 'price_override',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['コースコード', '商品コード']
    csv_unique_fields = []
    csv_export_fields = [
        'course.course_code', 'course.course_name',
        'product.product_code', 'product.product_name',
        'quantity', 'price_override', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'product.product_code': '商品コード',
        'product.product_name': '商品名',
        'quantity': '数量',
        'price_override': '単価上書き',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T09: パック
# =============================================================================
class PackCourseInline(admin.TabularInline):
    model = PackCourse
    extra = 1
    raw_id_fields = ['course']
    verbose_name = 'コース'
    verbose_name_plural = 'T53_パックコース構成'


class PackItemInline(admin.TabularInline):
    """T52_パック商品構成（諸経費・教材費など）"""
    model = PackItem
    extra = 1
    raw_id_fields = ['product']
    verbose_name = '商品（諸経費・教材費等）'
    verbose_name_plural = 'T52_パック商品構成（諸経費・教材費等）'

    def get_queryset(self, request):
        """商品種別を表示してわかりやすくする"""
        return super().get_queryset(request).select_related('product')


@admin.register(Pack)
class PackAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'pack_code', 'pack_name', 'brand', 'school', 'grade',
        'product_set', 'pack_price', 'discount_type', 'discount_value', 'is_active'
    ]
    list_filter = ['brand', 'school', 'grade', 'product_set', 'discount_type', 'is_active']
    search_fields = ['pack_code', 'pack_name']
    raw_id_fields = ['brand', 'school', 'grade', 'product_set']
    inlines = [PackCourseInline, PackItemInline]

    csv_import_fields = {
        'パックコード': 'pack_code',
        'パック名': 'pack_name',
        'ブランドコード': 'brand__brand_code',
        'パック料金': 'pack_price',
        '割引種別': 'discount_type',
        '割引値': 'discount_value',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['パックコード', 'パック名']
    csv_unique_fields = ['pack_code']
    csv_export_fields = [
        'pack_code', 'pack_name', 'brand.brand_name', 'school.school_name',
        'grade.grade_name', 'product_set.set_name', 'pack_price',
        'discount_type', 'discount_value', 'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'pack_code': 'パックコード',
        'pack_name': 'パック名',
        'brand.brand_name': 'ブランド名',
        'school.school_name': '校舎名',
        'grade.grade_name': '学年名',
        'product_set.set_name': '商品セット',
        'pack_price': 'パック料金',
        'discount_type': '割引種別',
        'discount_value': '割引値',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T53: パックコース構成
# =============================================================================
@admin.register(PackCourse)
class PackCourseAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['pack', 'course', 'sort_order', 'is_active']
    list_filter = ['is_active', 'pack']
    search_fields = ['pack__pack_name', 'course__course_name']
    raw_id_fields = ['pack', 'course']

    csv_import_fields = {
        'パックコード': 'pack__pack_code',
        'コースコード': 'course__course_code',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['パックコード', 'コースコード']
    csv_unique_fields = []
    csv_export_fields = [
        'pack.pack_code', 'pack.pack_name',
        'course.course_code', 'course.course_name',
        'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'pack.pack_code': 'パックコード',
        'pack.pack_name': 'パック名',
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'sort_order': '並び順',
        'is_active': '有効',
    }


# =============================================================================
# T11: 講習マスタ
# =============================================================================
@admin.register(Seminar)
class SeminarAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'seminar_code', 'seminar_name', 'seminar_type', 'year',
        'base_price', 'is_active'
    ]
    list_filter = ['seminar_type', 'year', 'brand', 'is_active']
    search_fields = ['seminar_code', 'seminar_name']
    raw_id_fields = ['brand', 'grade']

    csv_import_fields = {
        '講習コード': 'seminar_code',
        '講習名': 'seminar_name',
        '講習種別': 'seminar_type',
        'ブランドコード': 'brand__brand_code',
        '学年コード': 'grade__grade_code',
        '年度': 'year',
        '開始日': 'start_date',
        '終了日': 'end_date',
        '価格': 'base_price',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['講習コード', '講習名', '年度']
    csv_unique_fields = ['seminar_code']
    csv_export_fields = [
        'seminar_code', 'seminar_name', 'seminar_type',
        'brand.brand_name', 'grade.grade_name',
        'year', 'start_date', 'end_date', 'base_price',
        'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'seminar_code': '講習コード',
        'seminar_name': '講習名',
        'seminar_type': '講習種別',
        'brand.brand_name': 'ブランド名',
        'grade.grade_name': '学年名',
        'year': '年度',
        'start_date': '開始日',
        'end_date': '終了日',
        'base_price': '価格',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T12: 検定マスタ
# =============================================================================
@admin.register(Certification)
class CertificationAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'certification_code', 'certification_name', 'certification_type',
        'level', 'year', 'exam_fee', 'is_active'
    ]
    list_filter = ['certification_type', 'year', 'is_active']
    search_fields = ['certification_code', 'certification_name', 'level']
    raw_id_fields = ['brand']

    csv_import_fields = {
        '検定コード': 'certification_code',
        '検定名': 'certification_name',
        '検定種別': 'certification_type',
        '級・レベル': 'level',
        'ブランドコード': 'brand__brand_code',
        '年度': 'year',
        '試験日': 'exam_date',
        '検定料': 'exam_fee',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['検定コード', '検定名', '年度']
    csv_unique_fields = ['certification_code']
    csv_export_fields = [
        'certification_code', 'certification_name', 'certification_type',
        'level', 'brand.brand_name', 'year', 'exam_date', 'exam_fee',
        'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'certification_code': '検定コード',
        'certification_name': '検定名',
        'certification_type': '検定種別',
        'level': '級・レベル',
        'brand.brand_name': 'ブランド名',
        'year': '年度',
        'exam_date': '試験日',
        'exam_fee': '検定料',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T07: チケットマスタ
# =============================================================================
@admin.register(Ticket)
class TicketAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'ticket_code', 'ticket_name', 'ticket_type', 'ticket_category',
        'annual_weekly', 'total_tickets', 'brand', 'is_active'
    ]
    list_filter = ['ticket_type', 'ticket_category', 'brand', 'year_carryover', 'is_active']
    search_fields = ['ticket_code', 'ticket_name', 'transfer_group']
    raw_id_fields = ['brand', 'tenant_ref']
    ordering = ['ticket_code']

    fieldsets = (
        ('基本情報', {
            'fields': ('ticket_code', 'ticket_name', 'ticket_type', 'ticket_category', 'brand')
        }),
        ('チケット枚数', {
            'fields': ('annual_weekly', 'max_per_lesson', 'total_tickets'),
            'description': '年間/週: 年間授業回数、Max値: 1回あたり消費枚数、チケット枚数: 年間合計'
        }),
        ('振替設定', {
            'fields': ('transfer_day', 'transfer_group', 'consumption_symbol'),
        }),
        ('有効期限・フラグ', {
            'fields': ('calendar_flag', 'year_carryover', 'expiry_date'),
        }),
        ('その他', {
            'fields': ('description', 'sort_order', 'is_active', 'tenant_ref'),
        }),
    )

    csv_import_fields = {
        'チケットコード': 'ticket_code',
        'チケット名': 'ticket_name',
        'チケット種類': 'ticket_type',
        'チケット区別': 'ticket_category',
        '振替曜日': 'transfer_day',
        '振替グループ': 'transfer_group',
        '消化記号': 'consumption_symbol',
        '年間週': 'annual_weekly',
        'Max値': 'max_per_lesson',
        'チケット枚数': 'total_tickets',
        'カレンダーフラグ': 'calendar_flag',
        '年マタギ': 'year_carryover',
        '有効期限': 'expiry_date',
        'ブランドコード': 'brand__brand_code',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['チケットコード', 'チケット名']
    csv_unique_fields = ['ticket_code']
    csv_export_fields = [
        'ticket_code', 'ticket_name', 'ticket_type', 'ticket_category',
        'transfer_day', 'transfer_group', 'consumption_symbol',
        'annual_weekly', 'max_per_lesson', 'total_tickets',
        'calendar_flag', 'year_carryover', 'expiry_date',
        'brand.brand_name', 'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'ticket_code': 'チケットコード',
        'ticket_name': 'チケット名',
        'ticket_type': 'チケット種類',
        'ticket_category': 'チケット区別',
        'transfer_day': '振替曜日',
        'transfer_group': '振替グループ',
        'consumption_symbol': '消化記号',
        'annual_weekly': '年間週',
        'max_per_lesson': 'Max値',
        'total_tickets': 'チケット枚数',
        'calendar_flag': 'カレンダーフラグ',
        'year_carryover': '年マタギ',
        'expiry_date': '有効期限',
        'brand.brand_name': 'ブランド名',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T08b: コースチケット構成
# =============================================================================
class CourseTicketInline(admin.TabularInline):
    model = CourseTicket
    extra = 1
    can_delete = True
    raw_id_fields = ['ticket']
    fields = ['ticket', 'quantity', 'per_week', 'is_active']
    verbose_name = 'チケット'
    verbose_name_plural = 'T08b_コースチケット構成'


@admin.register(CourseTicket)
class CourseTicketAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['course', 'ticket', 'quantity', 'per_week', 'is_active']
    list_filter = ['is_active', 'course__brand']
    search_fields = ['course__course_name', 'ticket__ticket_name']
    raw_id_fields = ['course', 'ticket', 'tenant_ref']

    csv_import_fields = {
        'コースコード': 'course__course_code',
        'チケットコード': 'ticket__ticket_code',
        '付与枚数': 'quantity',
        '週あたり': 'per_week',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['コースコード', 'チケットコード']
    csv_unique_fields = []
    csv_export_fields = [
        'course.course_code', 'course.course_name',
        'ticket.ticket_code', 'ticket.ticket_name',
        'quantity', 'per_week', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'ticket.ticket_code': 'チケットコード',
        'ticket.ticket_name': 'チケット名',
        'quantity': '付与枚数',
        'per_week': '週あたり',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T09b: パックチケット構成
# =============================================================================
class PackTicketInline(admin.TabularInline):
    model = PackTicket
    extra = 1
    raw_id_fields = ['ticket']
    verbose_name = 'チケット'
    verbose_name_plural = 'T09b_パックチケット構成'


@admin.register(PackTicket)
class PackTicketAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['pack', 'ticket', 'quantity', 'per_week', 'is_active']
    list_filter = ['is_active', 'pack__brand']
    search_fields = ['pack__pack_name', 'ticket__ticket_name']
    raw_id_fields = ['pack', 'ticket', 'tenant_ref']

    csv_import_fields = {
        'パックコード': 'pack__pack_code',
        'チケットコード': 'ticket__ticket_code',
        '付与枚数': 'quantity',
        '週あたり': 'per_week',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['パックコード', 'チケットコード']
    csv_unique_fields = []
    csv_export_fields = [
        'pack.pack_code', 'pack.pack_name',
        'ticket.ticket_code', 'ticket.ticket_name',
        'quantity', 'per_week', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'pack.pack_code': 'パックコード',
        'pack.pack_name': 'パック名',
        'ticket.ticket_code': 'チケットコード',
        'ticket.ticket_name': 'チケット名',
        'quantity': '付与枚数',
        'per_week': '週あたり',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T54: コース必須講習
# =============================================================================
@admin.register(CourseRequiredSeminar)
class CourseRequiredSeminarAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['course', 'seminar', 'auto_enroll', 'is_active']
    list_filter = ['auto_enroll', 'is_active']
    search_fields = ['course__course_name', 'seminar__seminar_name']
    raw_id_fields = ['course', 'seminar']

    csv_import_fields = {
        'コースコード': 'course__course_code',
        '講習コード': 'seminar__seminar_code',
        '自動登録': 'auto_enroll',
        '有効': 'is_active',
    }
    csv_required_fields = ['コースコード', '講習コード']
    csv_unique_fields = []
    csv_export_fields = [
        'course.course_code', 'course.course_name',
        'seminar.seminar_code', 'seminar.seminar_name',
        'auto_enroll', 'is_active'
    ]
    csv_export_headers = {
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'seminar.seminar_code': '講習コード',
        'seminar.seminar_name': '講習名',
        'auto_enroll': '自動登録',
        'is_active': '有効',
    }


# =============================================================================
# 契約
# =============================================================================
class StudentItemInline(admin.TabularInline):
    model = StudentItem
    extra = 0
    raw_id_fields = ['product']
    readonly_fields = ['billing_month', 'product', 'quantity', 'unit_price', 'discount_amount', 'final_price']


@admin.register(Contract)
class ContractAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'contract_no', 'student', 'school', 'brand',
        'course', 'status', 'contract_date', 'monthly_total', 'tenant_ref'
    ]
    list_filter = ['tenant_ref', 'status', 'school', 'brand']
    search_fields = ['contract_no', 'student__last_name', 'student__first_name']
    raw_id_fields = ['student', 'guardian', 'school', 'brand', 'course', 'tenant_ref']
    inlines = [StudentItemInline]

    csv_import_fields = {
        '契約番号': 'contract_no',
        '生徒番号': 'student__student_no',
        '保護者番号': 'guardian__guardian_no',
        '教室コード': 'school__school_code',
        'ブランドコード': 'brand__brand_code',
        'コースコード': 'course__course_code',
        '契約日': 'contract_date',
        '開始日': 'start_date',
        '終了日': 'end_date',
        'ステータス': 'status',
        '月額合計': 'monthly_total',
        '備考': 'notes',
    }
    csv_required_fields = ['契約番号', '生徒番号', '教室コード', 'ブランドコード', '契約日', '開始日']
    csv_unique_fields = ['contract_no']
    csv_export_fields = [
        'contract_no', 'student.student_no', 'student.last_name', 'student.first_name',
        'guardian.guardian_no', 'school.school_name', 'brand.brand_name',
        'course.course_name', 'status', 'contract_date', 'start_date', 'end_date',
        'monthly_total', 'notes'
    ]
    csv_export_headers = {
        'contract_no': '契約番号',
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'guardian.guardian_no': '保護者番号',
        'school.school_name': '校舎名',
        'brand.brand_name': 'ブランド名',
        'course.course_name': 'コース名',
        'status': 'ステータス',
        'contract_date': '契約日',
        'start_date': '開始日',
        'end_date': '終了日',
        'monthly_total': '月額合計',
        'notes': '備考',
    }


# =============================================================================
# T04: 生徒商品（請求）
# =============================================================================
@admin.register(StudentItem)
class StudentItemAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'student', 'product', 'billing_month', 'quantity',
        'unit_price', 'discount_amount', 'final_price'
    ]
    list_filter = ['billing_month', 'product__item_type']
    search_fields = ['student__last_name', 'student__first_name', 'product__product_name']
    raw_id_fields = ['student', 'contract', 'product']

    csv_import_fields = {
        '旧システムID': 'old_id',
        '生徒番号': 'student__student_no',
        '契約番号': 'contract__contract_no',
        '商品コード': 'product__product_code',
        'ブランドコード': 'brand__brand_code',
        '校舎コード': 'school__school_code',
        'コースコード': 'course__course_code',
        '開始日': 'start_date',
        '曜日': 'day_of_week',
        '開始時間': 'start_time',
        '終了時間': 'end_time',
        '請求月': 'billing_month',
        '数量': 'quantity',
        '単価': 'unit_price',
        '割引額': 'discount_amount',
        '確定金額': 'final_price',
        '備考': 'notes',
    }
    csv_required_fields = ['生徒番号', '商品コード', '請求月', '単価', '確定金額']
    csv_unique_fields = []
    csv_export_fields = [
        'old_id',
        'student.student_no', 'student.last_name', 'student.first_name',
        'contract.contract_no',
        'product.product_code', 'product.product_name',
        'brand.brand_code', 'brand.brand_name',
        'school.school_code', 'school.school_name',
        'course.course_code', 'course.course_name',
        'start_date', 'day_of_week', 'start_time', 'end_time',
        'billing_month', 'quantity', 'unit_price', 'discount_amount', 'final_price', 'notes'
    ]
    csv_export_headers = {
        'old_id': '旧システムID',
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'contract.contract_no': '契約番号',
        'product.product_code': '商品コード',
        'product.product_name': '商品名',
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'start_date': '開始日',
        'day_of_week': '曜日',
        'start_time': '開始時間',
        'end_time': '終了時間',
        'billing_month': '請求月',
        'quantity': '数量',
        'unit_price': '単価',
        'discount_amount': '割引額',
        'final_price': '確定金額',
        'notes': '備考',
    }


# =============================================================================
# T06: 生徒割引
# =============================================================================
@admin.register(StudentDiscount)
class StudentDiscountAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'student', 'guardian', 'discount_name', 'amount', 'discount_unit',
        'start_date', 'end_date', 'is_recurring', 'is_active'
    ]
    list_filter = ['discount_unit', 'is_recurring', 'is_auto', 'is_active', 'end_condition']
    search_fields = [
        'discount_name', 'student__last_name', 'student__first_name',
        'guardian__last_name', 'guardian__first_name'
    ]
    raw_id_fields = ['student', 'guardian', 'contract', 'student_item', 'brand']
    date_hierarchy = 'start_date'


# =============================================================================
# T55: 講習申込
# =============================================================================
@admin.register(SeminarEnrollment)
class SeminarEnrollmentAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'student', 'seminar', 'status', 'is_required',
        'unit_price', 'discount_amount', 'final_price', 'applied_at'
    ]
    list_filter = ['status', 'is_required', 'seminar__seminar_type', 'seminar__year']
    search_fields = ['student__last_name', 'student__first_name', 'seminar__seminar_name']
    raw_id_fields = ['student', 'seminar']

    csv_import_fields = {
        '生徒番号': 'student__student_no',
        '講習コード': 'seminar__seminar_code',
        'ステータス': 'status',
        '必須': 'is_required',
        '単価': 'unit_price',
        '割引額': 'discount_amount',
        '確定金額': 'final_price',
    }
    csv_required_fields = ['生徒番号', '講習コード']
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'seminar.seminar_code', 'seminar.seminar_name',
        'status', 'is_required', 'unit_price', 'discount_amount', 'final_price', 'applied_at'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'seminar.seminar_code': '講習コード',
        'seminar.seminar_name': '講習名',
        'status': 'ステータス',
        'is_required': '必須',
        'unit_price': '単価',
        'discount_amount': '割引額',
        'final_price': '確定金額',
        'applied_at': '申込日時',
    }


# =============================================================================
# T56: 検定申込
# =============================================================================
@admin.register(CertificationEnrollment)
class CertificationEnrollmentAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'student', 'certification', 'status',
        'exam_fee', 'final_price', 'score', 'applied_at'
    ]
    list_filter = ['status', 'certification__certification_type', 'certification__year']
    search_fields = ['student__last_name', 'student__first_name', 'certification__certification_name']
    raw_id_fields = ['student', 'certification']

    csv_import_fields = {
        '生徒番号': 'student__student_no',
        '検定コード': 'certification__certification_code',
        'ステータス': 'status',
        '検定料': 'exam_fee',
        '確定金額': 'final_price',
        '得点': 'score',
        '合否': 'result',
    }
    csv_required_fields = ['生徒番号', '検定コード']
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'certification.certification_code', 'certification.certification_name',
        'status', 'exam_fee', 'final_price', 'score', 'result', 'applied_at'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'certification.certification_code': '検定コード',
        'certification.certification_name': '検定名',
        'status': 'ステータス',
        'exam_fee': '検定料',
        'final_price': '確定金額',
        'score': '得点',
        'result': '合否',
        'applied_at': '申込日時',
    }


# =============================================================================
# 契約履歴（インライン）
# =============================================================================
class ContractHistoryInline(admin.TabularInline):
    model = ContractHistory
    extra = 0
    readonly_fields = [
        'action_type', 'change_summary', 'amount_before', 'amount_after',
        'discount_amount', 'mile_used', 'mile_discount', 'changed_by_name',
        'is_system_change', 'created_at'
    ]
    ordering = ['-created_at']
    max_num = 10
    can_delete = False
    verbose_name = '変更履歴'
    verbose_name_plural = '変更履歴'

    def has_add_permission(self, request, obj=None):
        return False


# =============================================================================
# 契約履歴（単体）
# =============================================================================
@admin.register(ContractHistory)
class ContractHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'contract', 'action_type', 'change_summary',
        'amount_before', 'amount_after', 'changed_by_name',
        'is_system_change', 'created_at'
    ]
    list_filter = ['action_type', 'is_system_change', 'created_at']
    search_fields = ['contract__contract_no', 'change_summary', 'changed_by_name']
    readonly_fields = [
        'contract', 'action_type', 'before_data', 'after_data',
        'change_summary', 'change_detail', 'amount_before', 'amount_after',
        'discount_amount', 'mile_used', 'mile_discount', 'effective_date',
        'changed_by', 'changed_by_name', 'is_system_change', 'ip_address',
        'created_at', 'updated_at'
    ]
    raw_id_fields = ['contract', 'changed_by']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('契約情報', {
            'fields': ('contract',)
        }),
        ('変更内容', {
            'fields': ('action_type', 'change_summary', 'change_detail', 'effective_date')
        }),
        ('金額', {
            'fields': ('amount_before', 'amount_after', 'discount_amount', 'mile_used', 'mile_discount')
        }),
        ('変更データ', {
            'fields': ('before_data', 'after_data'),
            'classes': ('collapse',)
        }),
        ('変更者情報', {
            'fields': ('changed_by', 'changed_by_name', 'is_system_change', 'ip_address')
        }),
        ('日時', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# システム監査ログ
# =============================================================================
@admin.register(SystemAuditLog)
class SystemAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'entity_type', 'action_type', 'action_detail',
        'user_name', 'is_system_action', 'is_success'
    ]
    list_filter = ['entity_type', 'action_type', 'is_system_action', 'is_success', 'created_at']
    search_fields = ['entity_name', 'action_detail', 'user_name', 'user_email', 'entity_id']
    readonly_fields = [
        'entity_type', 'entity_id', 'entity_name', 'action_type', 'action_detail',
        'before_data', 'after_data', 'changed_fields',
        'student', 'guardian', 'contract',
        'user', 'user_name', 'user_email',
        'is_system_action', 'ip_address', 'user_agent', 'request_path', 'request_method',
        'is_success', 'error_message', 'notes', 'created_at', 'updated_at'
    ]
    raw_id_fields = ['student', 'guardian', 'contract', 'user']
    date_hierarchy = 'created_at'
    list_per_page = 50

    fieldsets = (
        ('エンティティ情報', {
            'fields': ('entity_type', 'entity_id', 'entity_name')
        }),
        ('操作内容', {
            'fields': ('action_type', 'action_detail', 'is_success', 'error_message')
        }),
        ('変更データ', {
            'fields': ('before_data', 'after_data', 'changed_fields'),
            'classes': ('collapse',)
        }),
        ('関連エンティティ', {
            'fields': ('student', 'guardian', 'contract')
        }),
        ('操作者情報', {
            'fields': ('user', 'user_name', 'user_email', 'is_system_action')
        }),
        ('リクエスト情報', {
            'fields': ('ip_address', 'user_agent', 'request_path', 'request_method'),
            'classes': ('collapse',)
        }),
        ('日時', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# T10a: 当月分商品（追加チケット）
# =============================================================================
class AdditionalTicketDateInline(admin.TabularInline):
    model = AdditionalTicketDate
    extra = 0
    fields = ['target_date', 'is_used', 'used_at', 'attendance']
    readonly_fields = ['used_at']


@admin.register(AdditionalTicket)
class AdditionalTicketAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'student', 'course', 'item_type', 'quantity', 'unit_price',
        'total_price', 'status', 'valid_until', 'tenant_ref'
    ]
    list_filter = ['item_type', 'status', 'tenant_ref']
    search_fields = ['student__student_name', 'course__course_name']
    raw_id_fields = ['student', 'course', 'class_schedule', 'student_item', 'tenant_ref']
    inlines = [AdditionalTicketDateInline]
    ordering = ['-created_at']

    fieldsets = (
        ('基本情報', {
            'fields': ('tenant_ref', 'student', 'course', 'class_schedule', 'item_type')
        }),
        ('購入情報', {
            'fields': ('purchase_date', 'quantity', 'unit_price', 'total_price')
        }),
        ('状態', {
            'fields': ('status', 'used_count', 'valid_until')
        }),
        ('関連', {
            'fields': ('student_item', 'notes')
        }),
    )

    csv_import_fields = {
        '会社コード': 'tenant_ref__tenant_code',
        '生徒コード': 'student__student_code',
        'コースコード': 'course__course_code',
        '種別': 'item_type',
        '購入日': 'purchase_date',
        '数量': 'quantity',
        '単価': 'unit_price',
        '合計金額': 'total_price',
        'ステータス': 'status',
        '有効期限': 'valid_until',
        '備考': 'notes',
    }
    csv_required_fields = ['生徒コード', '種別', '数量']
    csv_export_fields = [
        'tenant_ref.tenant_code', 'student.student_code', 'student.student_name',
        'course.course_code', 'course.course_name', 'item_type',
        'purchase_date', 'quantity', 'unit_price', 'total_price',
        'used_count', 'status', 'valid_until', 'notes'
    ]
    csv_export_headers = {
        'tenant_ref.tenant_code': '会社コード',
        'student.student_code': '生徒コード',
        'student.student_name': '生徒名',
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'item_type': '種別',
        'purchase_date': '購入日',
        'quantity': '数量',
        'unit_price': '単価',
        'total_price': '合計金額',
        'used_count': '使用済み数',
        'status': 'ステータス',
        'valid_until': '有効期限',
        'notes': '備考',
    }


# =============================================================================
# 動的にinlinesを追加（モデル定義順序の問題を回避）
# =============================================================================
# CourseAdminにCourseTicketInlineを追加
CourseAdmin.inlines = [CourseItemInline, CourseTicketInline]

# PackAdminにPackTicketInlineを追加
PackAdmin.inlines = [PackCourseInline, PackItemInline, PackTicketInline]

# ContractAdminにContractHistoryInlineを追加
ContractAdmin.inlines = [StudentItemInline, ContractHistoryInline]

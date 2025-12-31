"""
ProductSet Admin - 商品セット管理
ProductSetAdmin, ProductSetItemAdmin, ProductSetItemInline
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import ProductSet, ProductSetItem


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

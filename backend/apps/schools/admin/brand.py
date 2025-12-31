"""
Brand Admin - ブランド関連Admin
BrandCategoryAdmin, BrandAdmin, BrandSchoolAdmin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import Brand, BrandCategory, BrandSchool


class BrandSchoolInline(admin.TabularInline):
    """ブランド開講校舎のインライン編集"""
    model = BrandSchool
    extra = 1
    autocomplete_fields = ['school']
    fields = ['school', 'is_main', 'sort_order', 'is_active']

    def save_new_objects(self, commit=True):
        """新規オブジェクト保存時にtenant_idを親から継承"""
        saved_instances = super().save_new_objects(commit=False)
        for instance in saved_instances:
            if hasattr(self, 'parent_instance') and self.parent_instance:
                instance.tenant_id = self.parent_instance.tenant_id
                instance.tenant_ref_id = self.parent_instance.tenant_ref_id
            if commit:
                instance.save()
        return saved_instances


class BrandInline(admin.TabularInline):
    """ブランドカテゴリに属するブランドのインライン編集"""
    model = Brand
    extra = 0
    fields = ['brand_code', 'brand_name', 'brand_type', 'is_active']
    show_change_link = True


@admin.register(BrandCategory)
class BrandCategoryAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """ブランドカテゴリマスタAdmin（T12c_ブランドカテゴリ）"""
    list_display = ['category_code', 'category_name', 'get_brand_count', 'sort_order', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active']
    search_fields = ['category_code', 'category_name']
    ordering = ['sort_order', 'category_code']
    raw_id_fields = ['tenant_ref']
    inlines = [BrandInline]

    fieldsets = (
        ('基本情報', {
            'fields': ('category_code', 'category_name', 'category_name_short', 'description')
        }),
        ('表示設定', {
            'fields': ('logo_url', 'color_primary', 'color_secondary', 'sort_order')
        }),
        ('ステータス', {
            'fields': ('is_active', 'tenant_ref')
        }),
    )

    # CSV Import設定
    csv_import_fields = {
        'カテゴリコード': 'category_code',
        'カテゴリ名': 'category_name',
        'カテゴリ略称': 'category_name_short',
        '説明': 'description',
        'ロゴURL': 'logo_url',
        'メインカラー': 'color_primary',
        'サブカラー': 'color_secondary',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['カテゴリコード', 'カテゴリ名']
    csv_unique_fields = ['category_code']
    csv_export_fields = [
        'category_code', 'category_name', 'category_name_short', 'description',
        'logo_url', 'color_primary', 'color_secondary', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'category_code': 'カテゴリコード',
        'category_name': 'カテゴリ名',
        'category_name_short': 'カテゴリ略称',
        'description': '説明',
        'logo_url': 'ロゴURL',
        'color_primary': 'メインカラー',
        'color_secondary': 'サブカラー',
        'sort_order': '並び順',
        'is_active': '有効',
    }

    @admin.display(description='ブランド数')
    def get_brand_count(self, obj):
        return obj.brands.filter(is_active=True).count()


@admin.register(Brand)
class BrandAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """ブランドマスタAdmin（T12_ブランド情報対応）"""
    list_display = ['brand_code', 'brand_name', 'category', 'brand_type', 'get_school_count', 'is_active', 'sort_order', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active', 'category', 'brand_type']
    search_fields = ['brand_code', 'brand_name']
    ordering = ['sort_order', 'brand_code']
    raw_id_fields = ['tenant_ref']
    autocomplete_fields = ['category']
    inlines = [BrandSchoolInline]

    @admin.display(description='開講校舎数')
    def get_school_count(self, obj):
        return obj.brand_schools.filter(is_active=True).count()

    def save_formset(self, request, form, formset, change):
        """インラインフォームセット保存時にtenant_idを親から継承"""
        instances = formset.save(commit=False)
        for instance in instances:
            # 親オブジェクト（Brand）からtenant_idを継承
            if hasattr(instance, 'tenant_id') and form.instance.tenant_id:
                instance.tenant_id = form.instance.tenant_id
            if hasattr(instance, 'tenant_ref_id') and form.instance.tenant_ref_id:
                instance.tenant_ref_id = form.instance.tenant_ref_id
            instance.save()
        formset.save_m2m()

    # CSV Import設定
    csv_import_fields = {
        'ブランドコード': 'brand_code',
        'ブランド名': 'brand_name',
        'ブランド略称': 'brand_short_name',
        'ブランドタイプ': 'brand_type',
        '説明': 'description',
        'ロゴURL': 'logo_url',
        'テーマカラー': 'theme_color',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['ブランドコード', 'ブランド名']
    csv_unique_fields = ['brand_code']
    csv_export_fields = [
        'brand_code', 'brand_name', 'brand_short_name', 'brand_type',
        'description', 'logo_url', 'theme_color', 'is_active', 'sort_order'
    ]
    csv_export_headers = {
        'brand_code': 'ブランドコード',
        'brand_name': 'ブランド名',
        'brand_short_name': 'ブランド略称',
        'brand_type': 'ブランドタイプ',
        'description': '説明',
        'logo_url': 'ロゴURL',
        'theme_color': 'テーマカラー',
        'is_active': '有効',
        'sort_order': '並び順',
    }


@admin.register(BrandSchool)
class BrandSchoolAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """ブランド開講校舎Admin（T12a_ブランド開講校舎）"""
    list_display = ['brand', 'school', 'get_school_location', 'is_main', 'sort_order', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active', 'brand', 'is_main']
    search_fields = ['brand__brand_name', 'school__school_name']
    ordering = ['brand', 'sort_order']
    autocomplete_fields = ['brand', 'school']
    raw_id_fields = ['tenant_ref']

    # CSV Import設定
    csv_import_fields = {
        'ブランドコード': 'brand__brand_code',
        '校舎コード': 'school__school_code',
        'メイン校舎': 'is_main',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['ブランドコード', '校舎コード']
    csv_unique_fields = []
    csv_export_fields = [
        'brand.brand_code', 'brand.brand_name', 'school.school_code', 'school.school_name',
        'is_main', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'is_main': 'メイン校舎',
        'sort_order': '並び順',
        'is_active': '有効',
    }

    @admin.display(description='位置情報')
    def get_school_location(self, obj):
        if obj.school.latitude and obj.school.longitude:
            return f"({obj.school.latitude}, {obj.school.longitude})"
        return "未設定"

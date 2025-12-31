"""
Pack Admin - パック管理
PackAdmin, PackCourseAdmin, PackCourseInline, PackItemInline
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import Pack, PackCourse, PackItem


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
    inlines = [PackCourseInline, PackItemInline]  # PackTicketInline added dynamically in __init__.py

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

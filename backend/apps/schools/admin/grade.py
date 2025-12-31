"""
Grade Admin - 学年・教科管理Admin
SchoolYearAdmin, GradeAdmin, SubjectAdmin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import SchoolYear, Grade, GradeSchoolYear, Subject


class GradeSchoolYearInline(admin.TabularInline):
    """対象学年定義のインライン編集"""
    model = GradeSchoolYear
    extra = 1
    autocomplete_fields = ['school_year']


@admin.register(SchoolYear)
class SchoolYearAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """単一学年マスタAdmin（T17a_単一学年）"""
    list_display = ['year_code', 'year_name', 'category', 'sort_order', 'is_active']
    list_filter = ['is_active', 'category']
    search_fields = ['year_code', 'year_name']
    ordering = ['sort_order', 'year_code']

    # CSV Import設定
    csv_import_fields = {
        '学年コード': 'year_code',
        '学年名': 'year_name',
        'カテゴリ': 'category',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['学年コード', '学年名']
    csv_unique_fields = ['year_code']
    csv_export_fields = ['year_code', 'year_name', 'category', 'is_active', 'sort_order']
    csv_export_headers = {
        'year_code': '学年コード',
        'year_name': '学年名',
        'category': 'カテゴリ',
        'is_active': '有効',
        'sort_order': '並び順',
    }


@admin.register(Grade)
class GradeAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """対象学年定義Admin（T17_対象学年定義）"""
    list_display = ['grade_code', 'grade_name', 'get_school_years_display', 'category', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active', 'category']
    search_fields = ['grade_code', 'grade_name']
    ordering = ['sort_order', 'grade_code']
    inlines = [GradeSchoolYearInline]
    filter_horizontal = ['school_years']
    raw_id_fields = ['tenant_ref']

    @admin.display(description='対象学年')
    def get_school_years_display(self, obj):
        years = obj.school_years.all().order_by('sort_order')[:5]
        names = [y.year_name for y in years]
        total = obj.school_years.count()
        if total > 5:
            return f"{', '.join(names)}... (+{total - 5})"
        return ', '.join(names) if names else '-'

    # CSV Import設定
    csv_import_fields = {
        '学年コード': 'grade_code',
        '学年名': 'grade_name',
        '学年略称': 'grade_name_short',
        'カテゴリ': 'category',
        '説明': 'description',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['学年コード', '学年名']
    csv_unique_fields = ['grade_code']
    csv_export_fields = [
        'grade_code', 'grade_name', 'grade_name_short', 'category',
        'description', 'is_active', 'sort_order'
    ]
    csv_export_headers = {
        'grade_code': '学年コード',
        'grade_name': '学年名',
        'grade_name_short': '学年略称',
        'category': 'カテゴリ',
        'description': '説明',
        'is_active': '有効',
        'sort_order': '並び順',
    }


@admin.register(Subject)
class SubjectAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """教科マスタAdmin"""
    list_display = ['subject_code', 'subject_name', 'brand', 'category', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active', 'category', 'brand']
    search_fields = ['subject_code', 'subject_name']
    ordering = ['sort_order', 'subject_code']
    raw_id_fields = ['tenant_ref', 'brand']
    autocomplete_fields = ['brand']

    # CSV Import設定
    csv_import_fields = {
        '教科コード': 'subject_code',
        '教科名': 'subject_name',
        '教科略称': 'subject_short_name',
        'カテゴリ': 'category',
        '説明': 'description',
        'アイコン': 'icon',
        'カラー': 'color',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['教科コード', '教科名']
    csv_unique_fields = ['subject_code']
    csv_export_fields = [
        'subject_code', 'subject_name', 'subject_short_name', 'category',
        'description', 'icon', 'color', 'is_active', 'sort_order'
    ]
    csv_export_headers = {
        'subject_code': '教科コード',
        'subject_name': '教科名',
        'subject_short_name': '教科略称',
        'category': 'カテゴリ',
        'description': '説明',
        'icon': 'アイコン',
        'color': 'カラー',
        'is_active': '有効',
        'sort_order': '並び順',
    }

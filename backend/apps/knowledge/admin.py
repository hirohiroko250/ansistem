from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from .models import ManualCategory, Manual, TemplateCategory, ChatTemplate


@admin.register(ManualCategory)
class ManualCategoryAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['name', 'parent', 'sort_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']

    csv_import_fields = {
        'カテゴリ名': 'name',
        'スラッグ': 'slug',
        '説明': 'description',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['カテゴリ名']
    csv_unique_fields = ['slug']
    csv_export_fields = ['name', 'slug', 'description', 'parent.name', 'sort_order', 'is_active', 'created_at']
    csv_export_headers = {
        'name': 'カテゴリ名',
        'slug': 'スラッグ',
        'description': '説明',
        'parent.name': '親カテゴリ',
        'sort_order': '並び順',
        'is_active': '有効',
        'created_at': '作成日時',
    }


@admin.register(Manual)
class ManualAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['title', 'tenant_ref', 'category', 'is_published', 'is_pinned', 'view_count', 'updated_at']
    list_filter = ['is_published', 'is_pinned', 'category', 'tenant_ref']
    search_fields = ['title', 'content', 'summary']
    readonly_fields = ['view_count']

    def get_queryset(self, request):
        """全てのマニュアルを表示（テナントフィルタなし）"""
        # deleted_at=Nullのものだけを取得（論理削除されていないもの）
        qs = super().get_queryset(request).model.objects.filter(deleted_at__isnull=True)
        print(f"[ManualAdmin] get_queryset called, count: {qs.count()}")
        return qs

    csv_import_fields = {
        'タイトル': 'title',
        'スラッグ': 'slug',
        '要約': 'summary',
        '内容': 'content',
        '公開': 'is_published',
        '固定': 'is_pinned',
    }
    csv_required_fields = ['タイトル']
    csv_unique_fields = ['slug']
    csv_export_fields = [
        'title', 'slug', 'category.name', 'summary', 'content',
        'author.last_name', 'view_count', 'is_published', 'is_pinned',
        'published_at', 'created_at', 'updated_at',
    ]
    csv_export_headers = {
        'title': 'タイトル',
        'slug': 'スラッグ',
        'category.name': 'カテゴリ',
        'summary': '要約',
        'content': '内容',
        'author.last_name': '著者',
        'view_count': '閲覧数',
        'is_published': '公開',
        'is_pinned': '固定',
        'published_at': '公開日時',
        'created_at': '作成日時',
        'updated_at': '更新日時',
    }


@admin.register(TemplateCategory)
class TemplateCategoryAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']

    csv_import_fields = {
        'カテゴリ名': 'name',
        'スラッグ': 'slug',
        '説明': 'description',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['カテゴリ名']
    csv_unique_fields = ['slug']
    csv_export_fields = ['name', 'slug', 'description', 'sort_order', 'is_active', 'created_at']
    csv_export_headers = {
        'name': 'カテゴリ名',
        'slug': 'スラッグ',
        'description': '説明',
        'sort_order': '並び順',
        'is_active': '有効',
        'created_at': '作成日時',
    }


@admin.register(ChatTemplate)
class ChatTemplateAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['title', 'template_type', 'category', 'scene', 'is_active', 'use_count']
    list_filter = ['template_type', 'is_active', 'category']
    search_fields = ['title', 'content', 'scene']
    readonly_fields = ['use_count']

    csv_import_fields = {
        'タイトル': 'title',
        'テンプレート種別': 'template_type',
        'シーン': 'scene',
        '件名': 'subject',
        '内容': 'content',
        '有効': 'is_active',
    }
    csv_required_fields = ['タイトル', '内容']
    csv_unique_fields = []
    csv_export_fields = [
        'title', 'template_type', 'category.name', 'scene', 'subject',
        'content', 'use_count', 'is_active', 'created_at',
    ]
    csv_export_headers = {
        'title': 'タイトル',
        'template_type': 'テンプレート種別',
        'category.name': 'カテゴリ',
        'scene': 'シーン',
        'subject': '件名',
        'content': '内容',
        'use_count': '使用回数',
        'is_active': '有効',
        'created_at': '作成日時',
    }

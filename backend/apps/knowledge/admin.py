from django.contrib import admin
from .models import ManualCategory, Manual, TemplateCategory, ChatTemplate


@admin.register(ManualCategory)
class ManualCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'sort_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Manual)
class ManualAdmin(admin.ModelAdmin):
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


@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(ChatTemplate)
class ChatTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'template_type', 'category', 'scene', 'is_active', 'use_count']
    list_filter = ['template_type', 'is_active', 'category']
    search_fields = ['title', 'content', 'scene']
    readonly_fields = ['use_count']

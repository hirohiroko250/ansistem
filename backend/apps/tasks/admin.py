from django.contrib import admin
from django.utils.html import format_html
from apps.core.admin_csv import CSVImportExportMixin
from .models import Task, TaskCategory, TaskComment


class TaskCommentInline(admin.TabularInline):
    """作業コメント（対応履歴）インライン"""
    model = TaskComment
    extra = 1
    fields = ['comment', 'commented_by_id', 'is_internal', 'created_at']
    readonly_fields = ['created_at']


@admin.register(TaskCategory)
class TaskCategoryAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """作業カテゴリAdmin"""
    list_display = ['category_code', 'category_name', 'color_display', 'sort_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['category_code', 'category_name']
    ordering = ['sort_order']

    csv_import_fields = {
        'カテゴリコード': 'category_code',
        'カテゴリ名': 'category_name',
        'アイコン': 'icon',
        'カラー': 'color',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['カテゴリコード', 'カテゴリ名']
    csv_unique_fields = ['category_code']
    csv_export_fields = ['category_code', 'category_name', 'icon', 'color', 'sort_order', 'is_active']
    csv_export_headers = {
        'category_code': 'カテゴリコード',
        'category_name': 'カテゴリ名',
        'icon': 'アイコン',
        'color': 'カラー',
        'sort_order': '並び順',
        'is_active': '有効',
    }

    def color_display(self, obj):
        if obj.color:
            return format_html(
                '<span style="background-color: {}; padding: 2px 10px; border-radius: 3px;">{}</span>',
                obj.color, obj.color
            )
        return '-'
    color_display.short_description = 'カラー'


@admin.register(Task)
class TaskAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """作業一覧Admin"""
    list_display = [
        'status_badge', 'priority_badge', 'task_type_display', 'title',
        'school', 'student_display', 'due_date', 'created_at'
    ]

    csv_import_fields = {
        '種別': 'task_type',
        'タイトル': 'title',
        '説明': 'description',
        'ステータス': 'status',
        '優先度': 'priority',
        '期限日': 'due_date',
        '参照元種別': 'source_type',
        '参照元URL': 'source_url',
    }
    csv_required_fields = ['タイトル']
    csv_unique_fields = []
    csv_export_fields = [
        'task_type', 'title', 'description', 'status', 'priority',
        'school.school_name', 'brand.brand_name', 'student.student_no',
        'due_date', 'completed_at', 'source_type', 'source_url', 'created_at'
    ]
    csv_export_headers = {
        'task_type': '種別',
        'title': 'タイトル',
        'description': '説明',
        'status': 'ステータス',
        'priority': '優先度',
        'school.school_name': '校舎',
        'brand.brand_name': 'ブランド',
        'student.student_no': '生徒番号',
        'due_date': '期限日',
        'completed_at': '完了日時',
        'source_type': '参照元種別',
        'source_url': '参照元URL',
        'created_at': '作成日時',
    }
    list_filter = [
        'status', 'task_type', 'priority', 'school', 'brand',
        'created_at', 'due_date'
    ]
    search_fields = ['title', 'description', 'student__last_name', 'student__first_name', 'guardian__last_name']
    date_hierarchy = 'created_at'
    raw_id_fields = ['school', 'brand', 'student', 'guardian', 'category', 'tenant_ref']
    inlines = [TaskCommentInline]
    list_per_page = 50
    save_on_top = True

    fieldsets = (
        ('基本情報', {
            'fields': ('task_type', 'category', 'title', 'description', 'status', 'priority')
        }),
        ('関連情報', {
            'fields': ('school', 'brand', 'student', 'guardian')
        }),
        ('担当・期限', {
            'fields': ('assigned_to_id', 'created_by_id', 'due_date', 'completed_at')
        }),
        ('参照元', {
            'fields': ('source_type', 'source_id', 'source_url'),
            'classes': ('collapse',)
        }),
        ('追加情報', {
            'fields': ('metadata', 'tenant_ref'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'new': '#28a745',
            'in_progress': '#17a2b8',
            'waiting': '#ffc107',
            'completed': '#6c757d',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'
    status_badge.admin_order_field = 'status'

    def priority_badge(self, obj):
        colors = {
            'low': '#6c757d',
            'normal': '#17a2b8',
            'high': '#fd7e14',
            'urgent': '#dc3545',
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = '優先度'
    priority_badge.admin_order_field = 'priority'

    def task_type_display(self, obj):
        return obj.get_task_type_display()
    task_type_display.short_description = '種別'
    task_type_display.admin_order_field = 'task_type'

    def student_display(self, obj):
        if obj.student:
            return f"{obj.student.last_name} {obj.student.first_name}"
        elif obj.guardian:
            return f"(保護者) {obj.guardian.last_name}"
        return '-'
    student_display.short_description = '対象者'

    actions = ['mark_in_progress', 'mark_completed', 'mark_cancelled']

    @admin.action(description='選択した作業を「対応中」にする')
    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated}件の作業を「対応中」に変更しました。')

    @admin.action(description='選択した作業を「完了」にする')
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{updated}件の作業を「完了」に変更しました。')

    @admin.action(description='選択した作業を「キャンセル」にする')
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated}件の作業を「キャンセル」に変更しました。')


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    """作業コメントAdmin"""
    list_display = ['task', 'comment_preview', 'commented_by_id', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['task__title', 'comment']
    raw_id_fields = ['task']

    def comment_preview(self, obj):
        if len(obj.comment) > 50:
            return obj.comment[:50] + '...'
        return obj.comment
    comment_preview.short_description = 'コメント'

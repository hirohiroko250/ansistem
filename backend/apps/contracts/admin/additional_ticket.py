"""
AdditionalTicket Admin - 追加チケット管理
AdditionalTicketAdmin, AdditionalTicketDateInline
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import AdditionalTicket, AdditionalTicketDate


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

"""
Attendance Admin - 出席管理Admin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from apps.lessons.models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """出席・欠席管理Admin"""
    list_display = ['get_student_name', 'get_student_no', 'schedule', 'status', 'check_in_time', 'check_out_time', 'absence_notified_at', 'tenant_ref']
    list_display_links = ['get_student_name']
    list_filter = ['tenant_ref', 'status', 'schedule__school', 'schedule__subject']
    search_fields = ['student__student_no', 'student__last_name', 'student__first_name', 'notes']
    ordering = ['-created_at']
    raw_id_fields = ['tenant_ref', 'schedule', 'student']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本情報', {
            'fields': ('tenant_ref', 'schedule', 'student')
        }),
        ('出席状況', {
            'fields': ('status', 'check_in_time', 'check_out_time')
        }),
        ('欠席情報', {
            'fields': ('absence_reason', 'absence_notified_at'),
            'classes': ('collapse',)
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.last_name} {obj.student.first_name}"
        return "-"
    get_student_name.short_description = '生徒名'
    get_student_name.admin_order_field = 'student__last_name'

    def get_student_no(self, obj):
        if obj.student:
            return obj.student.student_no
        return "-"
    get_student_no.short_description = '生徒番号'
    get_student_no.admin_order_field = 'student__student_no'

    # CSV Import設定
    csv_import_fields = {
        '生徒番号': 'student__student_no',
        '出席状況': 'status',
        '入室時間': 'check_in_time',
        '退室時間': 'check_out_time',
        '欠席理由': 'absence_reason',
        '欠席連絡日時': 'absence_notified_at',
        '備考': 'notes',
    }
    csv_required_fields = ['生徒番号', '出席状況']
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'schedule.id', 'status', 'check_in_time', 'check_out_time',
        'absence_reason', 'absence_notified_at', 'notes'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'schedule.id': 'スケジュールID',
        'status': '出席状況',
        'check_in_time': '入室時間',
        'check_out_time': '退室時間',
        'absence_reason': '欠席理由',
        'absence_notified_at': '欠席連絡日時',
        'notes': '備考',
    }

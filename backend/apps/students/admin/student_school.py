"""
StudentSchool Admin - 生徒校舎関連Admin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import StudentSchool


@admin.register(StudentSchool)
class StudentSchoolAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['student', 'school', 'brand', 'get_day_of_week_display', 'start_time', 'enrollment_status', 'start_date', 'is_primary']
    list_filter = ['enrollment_status', 'school', 'brand', 'is_primary', 'day_of_week']
    raw_id_fields = ['student', 'school', 'brand', 'class_schedule']
    search_fields = ['student__student_no', 'student__last_name', 'student__first_name', 'school__school_name', 'brand__brand_name']
    ordering = ['student__student_no', 'brand', 'day_of_week', 'start_time']

    fieldsets = (
        ('基本情報', {
            'fields': ('student', 'school', 'brand', 'enrollment_status', 'is_primary')
        }),
        ('スケジュール', {
            'fields': ('class_schedule', 'day_of_week', 'start_time', 'end_time')
        }),
        ('期間', {
            'fields': ('start_date', 'end_date')
        }),
        ('その他', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='曜日')
    def get_day_of_week_display(self, obj):
        days = {1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'}
        return days.get(obj.day_of_week, '-')

    # CSV Import設定
    csv_import_fields = {
        '生徒番号': 'student__student_no',
        '校舎コード': 'school__school_code',
        'ブランドコード': 'brand__brand_code',
        '入塾ステータス': 'enrollment_status',
        '入塾日': 'start_date',
        '退塾日': 'end_date',
        '主所属': 'is_primary',
        '曜日': 'day_of_week',
        '開始時間': 'start_time',
        '終了時間': 'end_time',
    }
    csv_required_fields = ['生徒番号', '校舎コード']
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'school.school_code', 'school.school_name',
        'brand.brand_code', 'brand.brand_name',
        'enrollment_status', 'start_date', 'end_date', 'is_primary',
        'day_of_week', 'start_time', 'end_time'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'enrollment_status': '入塾ステータス',
        'start_date': '入塾日',
        'end_date': '退塾日',
        'is_primary': '主所属',
        'day_of_week': '曜日',
        'start_time': '開始時間',
        'end_time': '終了時間',
    }

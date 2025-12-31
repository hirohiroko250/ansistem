"""
Enrollment Admin - 生徒受講履歴・振替チケット管理Admin
"""
from django.contrib import admin
from django.db.models import Case, When
from ..models import StudentEnrollment, AbsenceTicket


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    """生徒受講履歴Admin"""
    list_display = [
        'get_student_name',
        'get_student_no',
        'school',
        'brand',
        'get_day_of_week_display',
        'start_time',
        'status',
        'change_type',
        'effective_date',
        'end_date',
    ]
    list_display_links = ['get_student_name']
    list_filter = ['status', 'change_type', 'school', 'brand', 'day_of_week', 'effective_date']
    search_fields = [
        'student__student_no',
        'student__last_name',
        'student__first_name',
        'school__school_name',
        'brand__brand_name',
        'notes',
    ]
    ordering = ['-effective_date', '-created_at']
    raw_id_fields = ['student', 'school', 'brand', 'class_schedule', 'ticket', 'student_item', 'previous_enrollment']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'effective_date'

    fieldsets = (
        ('基本情報', {
            'fields': ('student', 'school', 'brand')
        }),
        ('スケジュール情報', {
            'fields': ('class_schedule', 'day_of_week', 'start_time', 'end_time')
        }),
        ('チケット・購入情報', {
            'fields': ('ticket', 'student_item'),
            'classes': ('collapse',)
        }),
        ('ステータス', {
            'fields': ('status', 'change_type', 'effective_date', 'end_date')
        }),
        ('変更履歴', {
            'fields': ('previous_enrollment',),
            'classes': ('collapse',)
        }),
        ('その他', {
            'fields': ('notes', 'metadata', 'created_at', 'updated_at'),
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

    def get_day_of_week_display(self, obj):
        if obj.day_of_week is not None:
            days = ['月', '火', '水', '木', '金', '土', '日']
            if 0 <= obj.day_of_week < 7:
                return days[obj.day_of_week]
        return "-"
    get_day_of_week_display.short_description = '曜日'

    def get_queryset(self, request):
        """現在有効な記録を優先して表示"""
        qs = super().get_queryset(request).select_related(
            'student', 'school', 'brand', 'class_schedule'
        )
        return qs.order_by(
            Case(
                When(end_date__isnull=True, then=0),
                default=1,
            ),
            '-effective_date'
        )


@admin.register(AbsenceTicket)
class AbsenceTicketAdmin(admin.ModelAdmin):
    """欠席・振替チケット管理"""
    list_display = [
        'get_student_name',
        'get_student_no',
        'absence_date',
        'consumption_symbol',
        'status',
        'valid_until',
        'used_date',
    ]
    list_display_links = ['get_student_name']
    list_filter = ['status', 'consumption_symbol', 'absence_date']
    search_fields = [
        'student__student_no',
        'student__last_name',
        'student__first_name',
        'consumption_symbol',
        'notes',
    ]
    ordering = ['-absence_date']
    raw_id_fields = ['student', 'original_ticket', 'class_schedule', 'used_class_schedule']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'absence_date'

    fieldsets = (
        ('基本情報', {
            'fields': ('student', 'absence_date', 'class_schedule')
        }),
        ('チケット情報', {
            'fields': ('original_ticket', 'consumption_symbol', 'status', 'valid_until')
        }),
        ('振替使用', {
            'fields': ('used_date', 'used_class_schedule'),
            'description': '振替で使用した場合の情報'
        }),
        ('その他', {
            'fields': ('notes', 'created_at', 'updated_at'),
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

    def get_queryset(self, request):
        """発行済を優先して表示"""
        qs = super().get_queryset(request).select_related('student', 'class_schedule', 'original_ticket')
        return qs.order_by(
            Case(
                When(status='issued', then=0),
                default=1,
            ),
            '-absence_date'
        )

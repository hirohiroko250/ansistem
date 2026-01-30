"""
Suspension Admin - 休会申請管理Admin
"""
from django.contrib import admin
from django.db.models import Case, When
from apps.core.admin_csv import CSVImportExportMixin
from ..models import SuspensionRequest


@admin.register(SuspensionRequest)
class SuspensionRequestAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """休会申請Admin"""
    list_display = [
        'get_student_name',
        'get_student_no',
        'school',
        'brand',
        'suspend_from',
        'suspend_until',
        'status',
        'keep_seat',
        'requested_at',
    ]
    list_display_links = ['get_student_name']
    list_filter = ['status', 'reason', 'keep_seat', 'school', 'brand', 'suspend_from']
    search_fields = [
        'student__student_no',
        'student__last_name',
        'student__first_name',
        'reason_detail',
        'process_notes',
    ]
    ordering = ['-requested_at']
    raw_id_fields = ['student', 'school', 'brand', 'requested_by', 'processed_by', 'resumed_by']
    readonly_fields = ['requested_at', 'processed_at', 'created_at', 'updated_at']
    date_hierarchy = 'requested_at'

    fieldsets = (
        ('申請情報', {
            'fields': ('student', 'school', 'brand', 'status')
        }),
        ('休会期間', {
            'fields': ('suspend_from', 'suspend_until', 'keep_seat', 'monthly_fee_during_suspension')
        }),
        ('理由', {
            'fields': ('reason', 'reason_detail'),
        }),
        ('申請者', {
            'fields': ('requested_by', 'requested_at'),
            'classes': ('collapse',)
        }),
        ('処理情報', {
            'fields': ('processed_by', 'processed_at', 'process_notes'),
            'classes': ('collapse',)
        }),
        ('復会情報', {
            'fields': ('resumed_at', 'resumed_by'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_requests', 'reject_requests']

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
        """申請中を優先して表示"""
        qs = super().get_queryset(request).select_related('student', 'school', 'brand')
        return qs.order_by(
            Case(
                When(status='pending', then=0),
                default=1,
            ),
            '-requested_at'
        )

    def approve_requests(self, request, queryset):
        """選択した申請を承認"""
        count = 0
        for obj in queryset.filter(status='pending'):
            obj.approve(request.user)
            count += 1
        self.message_user(request, f'{count}件の休会申請を承認しました。')
    approve_requests.short_description = '選択した申請を承認'

    def reject_requests(self, request, queryset):
        """選択した申請を却下"""
        count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'{count}件の休会申請を却下しました。')
    reject_requests.short_description = '選択した申請を却下'

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'school.school_name', 'brand.brand_name',
        'suspend_from', 'suspend_until', 'status', 'keep_seat',
        'monthly_fee_during_suspension', 'reason', 'reason_detail',
        'requested_at', 'processed_at', 'resumed_at',
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'school.school_name': '校舎名',
        'brand.brand_name': 'ブランド名',
        'suspend_from': '休会開始日',
        'suspend_until': '休会終了日',
        'status': 'ステータス',
        'keep_seat': '席保持',
        'monthly_fee_during_suspension': '休会中月額',
        'reason': '理由',
        'reason_detail': '理由詳細',
        'requested_at': '申請日時',
        'processed_at': '処理日時',
        'resumed_at': '復会日時',
    }

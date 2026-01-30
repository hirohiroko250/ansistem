"""
Calendar Admin - カレンダー・時間割管理Admin
CalendarMasterAdmin, LessonCalendarAdmin, ClassScheduleAdmin, CalendarOperationLogAdmin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import CalendarMaster, LessonCalendar, ClassSchedule, CalendarOperationLog
from .importer import LessonCalendarCSVImporter


@admin.register(CalendarMaster)
class CalendarMasterAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """カレンダーマスター管理"""
    list_display = ['code', 'name', 'brand', 'lesson_type', 'is_active', 'sort_order', 'tenant_ref']
    list_filter = ['brand', 'lesson_type', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['sort_order', 'code']
    list_editable = ['sort_order', 'is_active']

    fieldsets = (
        ('基本情報', {
            'fields': ('code', 'name', 'brand', 'lesson_type')
        }),
        ('設定', {
            'fields': ('description', 'sort_order', 'is_active')
        }),
        ('システム', {
            'fields': ('tenant_ref',),
            'classes': ('collapse',)
        }),
    )

    # CSV設定
    csv_import_fields = ['code', 'name', 'brand.brand_code', 'lesson_type', 'description', 'sort_order', 'is_active']
    csv_export_fields = ['code', 'name', 'brand.brand_code', 'lesson_type', 'description', 'sort_order', 'is_active']
    csv_field_labels = {
        'code': 'カレンダーコード',
        'name': 'カレンダー名',
        'brand.brand_code': 'ブランドコード',
        'lesson_type': '授業タイプ',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }


@admin.register(LessonCalendar)
class LessonCalendarAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """開講カレンダーAdmin"""
    list_display = ['calendar_code', 'brand', 'school', 'lesson_date', 'day_of_week', 'is_open', 'display_label', 'ticket_type', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_open', 'lesson_type', 'brand', 'school', 'is_makeup_allowed']
    search_fields = ['calendar_code', 'display_label', 'notice_message', 'holiday_name']
    raw_id_fields = ['brand', 'school', 'tenant_ref']
    date_hierarchy = 'lesson_date'
    ordering = ['lesson_date']

    # カスタムインポーター使用
    csv_importer_class = LessonCalendarCSVImporter

    # CSV Import設定（Excel T13_開講カレンダー準拠）
    csv_import_fields = {
        'カレンダーID': 'calendar_code',
        '日付': 'lesson_date',
        '曜日': 'day_of_week',
        '保護者カレンダー表示': 'display_label',
        '開講日': 'is_open',
        '振替拒否': 'is_makeup_allowed',
        '消化・発行チケット券種': 'ticket_type',
        '権利発券数': 'ticket_issue_count',
        'チケット券種No': 'ticket_sequence',
        '有効期限': 'valid_days',
        'お知らせ': 'notice_message',
        '自動お知らせ送信': 'auto_send_notice',
        '拒否理由': 'rejection_reason',
        '祝日名': 'holiday_name',
    }
    csv_required_fields = ['カレンダーID', '日付']
    csv_unique_fields = ['calendar_code', 'lesson_date']
    csv_export_fields = [
        'calendar_code', 'brand.brand_code', 'school.school_code',
        'lesson_date', 'day_of_week', 'display_label', 'is_open',
        'is_makeup_allowed', 'ticket_type', 'ticket_issue_count', 'ticket_sequence',
        'valid_days', 'notice_message', 'auto_send_notice', 'rejection_reason', 'holiday_name'
    ]
    csv_export_headers = {
        'calendar_code': 'カレンダーID',
        'brand.brand_code': 'ブランドコード',
        'school.school_code': '校舎コード',
        'lesson_date': '日付',
        'day_of_week': '曜日',
        'display_label': '保護者カレンダー表示',
        'is_open': '開講日',
        'is_makeup_allowed': '振替拒否',
        'ticket_type': '消化・発行チケット券種',
        'ticket_issue_count': '権利発券数',
        'ticket_sequence': 'チケット券種No',
        'valid_days': '有効期限',
        'notice_message': 'お知らせ',
        'auto_send_notice': '自動お知らせ送信',
        'rejection_reason': '拒否理由',
        'holiday_name': '祝日名',
    }


@admin.register(ClassSchedule)
class ClassScheduleAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """開講時間割Admin（T14c_開講時間割）"""
    list_display = [
        'schedule_code', 'school', 'brand_category', 'brand', 'grade',
        'get_day_of_week_display', 'period', 'start_time', 'class_name',
        'capacity', 'reserved_seats', 'is_active'
    ]
    list_filter = [
        'is_active', 'brand_category', 'brand', 'school', 'grade',
        'day_of_week', 'approval_type'
    ]
    search_fields = [
        'schedule_code', 'class_name', 'class_type',
        'ticket_name', 'transfer_group', 'calendar_pattern'
    ]
    ordering = ['school', 'brand_category', 'brand', 'day_of_week', 'period']
    autocomplete_fields = ['brand', 'brand_category', 'school', 'room', 'grade']
    date_hierarchy = 'class_start_date'

    fieldsets = (
        ('基本情報', {
            'fields': (
                'schedule_code',
                ('school', 'room', 'room_name'),
                ('brand_category', 'brand'),
                'grade',
            )
        }),
        ('曜日・時間', {
            'fields': (
                ('day_of_week', 'period'),
                ('start_time', 'end_time', 'duration_minutes'),
                'break_time',
            )
        }),
        ('クラス情報', {
            'fields': (
                'class_name', 'class_type',
                'display_course_name', 'display_pair_name',
                'display_description',
            )
        }),
        ('チケット・振替', {
            'fields': (
                ('ticket_name', 'ticket_id'),
                ('transfer_group', 'schedule_group'),
                'calendar_pattern',
            )
        }),
        ('定員・承認', {
            'fields': (
                ('capacity', 'trial_capacity', 'reserved_seats'),
                ('pause_seat_fee', 'approval_type'),
            )
        }),
        ('期間', {
            'fields': (
                'display_start_date',
                ('class_start_date', 'class_end_date'),
            )
        }),
        ('ステータス', {
            'fields': ('is_active', 'tenant_id')
        }),
    )

    @admin.display(description='曜日')
    def get_day_of_week_display(self, obj):
        return obj.get_day_of_week_display()

    # CSV Import設定（Excel T14_開講時間割準拠）
    csv_import_fields = {
        '時間割コード': 'schedule_code',
        '校舎名': 'school__school_name',
        'ブランド名': 'brand__brand_name',
        '学年コード': 'grade__grade_code',
        '曜日': 'day_of_week',
        '時限': 'period',
        '開始時間': 'start_time',
        '授業時間': 'duration_minutes',
        '終了時間': 'end_time',
        'クラス名': 'class_name',
        'クラス種名': 'class_type',
        '保護者用コース名': 'display_course_name',
        '保護者用ペア名': 'display_pair_name',
        '保護者用説明': 'display_description',
        'チケット名': 'ticket_name',
        'チケットID': 'ticket_id',
        '振替グループ': 'transfer_group',
        '時間割グループ': 'schedule_group',
        '定員': 'capacity',
        '体験人数': 'trial_capacity',
        '休会時座席料金': 'pause_seat_fee',
        'カレンダーパターン': 'calendar_pattern',
        '承認種別': 'approval_type',
        '教室名': 'room_name',
        '保護者表示開始日': 'display_start_date',
        'クラス開始日': 'class_start_date',
        'クラス終了日': 'class_end_date',
        '有効': 'is_active',
    }
    csv_required_fields = ['時間割コード', 'クラス名']
    csv_unique_fields = ['schedule_code']
    csv_export_fields = [
        'schedule_code', 'school.school_name', 'brand.brand_name',
        'grade.grade_code', 'grade.grade_name',
        'day_of_week', 'period', 'start_time', 'duration_minutes', 'end_time',
        'class_name', 'class_type', 'display_course_name', 'display_pair_name',
        'ticket_name', 'ticket_id', 'transfer_group', 'schedule_group',
        'capacity', 'trial_capacity', 'pause_seat_fee', 'calendar_pattern',
        'approval_type', 'room_name', 'display_start_date', 'class_start_date',
        'class_end_date', 'is_active'
    ]
    csv_export_headers = {
        'schedule_code': '時間割コード',
        'school.school_name': '校舎名',
        'brand.brand_name': 'ブランド名',
        'grade.grade_code': '学年コード',
        'grade.grade_name': '学年名',
        'day_of_week': '曜日',
        'period': '時限',
        'start_time': '開始時間',
        'duration_minutes': '授業時間',
        'end_time': '終了時間',
        'class_name': 'クラス名',
        'class_type': 'クラス種名',
        'display_course_name': '保護者用コース名',
        'display_pair_name': '保護者用ペア名',
        'ticket_name': 'チケット名',
        'ticket_id': 'チケットID',
        'transfer_group': '振替グループ',
        'schedule_group': '時間割グループ',
        'capacity': '定員',
        'trial_capacity': '体験人数',
        'pause_seat_fee': '休会時座席料金',
        'calendar_pattern': 'カレンダーパターン',
        'approval_type': '承認種別',
        'room_name': '教室名',
        'display_start_date': '保護者表示開始日',
        'class_start_date': 'クラス開始日',
        'class_end_date': 'クラス終了日',
        'is_active': '有効',
    }


@admin.register(CalendarOperationLog)
class CalendarOperationLogAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """カレンダー操作ログ管理"""
    list_display = [
        'operation_type', 'operation_date', 'school', 'brand',
        'old_value', 'new_value', 'operated_by', 'operated_at'
    ]
    list_filter = ['operation_type', 'school', 'brand', 'operated_at']
    search_fields = ['reason', 'notes', 'old_value', 'new_value']
    date_hierarchy = 'operated_at'
    readonly_fields = [
        'id', 'operation_type', 'school', 'brand', 'schedule', 'lesson_calendar',
        'operation_date', 'operated_at', 'operated_by', 'old_value', 'new_value',
        'reason', 'notes', 'metadata', 'tenant_id'
    ]
    ordering = ['-operated_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = [
        'operation_type', 'operation_date',
        'school.school_name', 'brand.brand_name',
        'old_value', 'new_value', 'reason', 'notes',
        'operated_by.email', 'operated_at',
    ]
    csv_export_headers = {
        'operation_type': '操作種別',
        'operation_date': '操作対象日',
        'school.school_name': '校舎名',
        'brand.brand_name': 'ブランド名',
        'old_value': '変更前',
        'new_value': '変更後',
        'reason': '理由',
        'notes': '備考',
        'operated_by.email': '操作者',
        'operated_at': '操作日時',
    }

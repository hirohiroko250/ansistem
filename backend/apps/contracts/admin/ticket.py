"""
Ticket Admin - チケット管理
TicketAdmin, CourseTicketAdmin, CourseTicketInline, PackTicketAdmin, PackTicketInline
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import Ticket, CourseTicket, PackTicket


# =============================================================================
# T07: チケットマスタ
# =============================================================================
@admin.register(Ticket)
class TicketAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'ticket_code', 'ticket_name', 'ticket_type', 'ticket_category',
        'annual_weekly', 'total_tickets', 'brand', 'is_active'
    ]
    list_filter = ['ticket_type', 'ticket_category', 'brand', 'year_carryover', 'is_active']
    search_fields = ['ticket_code', 'ticket_name', 'transfer_group']
    raw_id_fields = ['brand', 'tenant_ref']
    ordering = ['ticket_code']

    fieldsets = (
        ('基本情報', {
            'fields': ('ticket_code', 'ticket_name', 'ticket_type', 'ticket_category', 'brand')
        }),
        ('チケット枚数', {
            'fields': ('annual_weekly', 'max_per_lesson', 'total_tickets'),
            'description': '年間/週: 年間授業回数、Max値: 1回あたり消費枚数、チケット枚数: 年間合計'
        }),
        ('振替設定', {
            'fields': ('transfer_day', 'transfer_group', 'consumption_symbol'),
        }),
        ('有効期限・フラグ', {
            'fields': ('calendar_flag', 'year_carryover', 'expiry_date'),
        }),
        ('その他', {
            'fields': ('description', 'sort_order', 'is_active', 'tenant_ref'),
        }),
    )

    csv_import_fields = {
        'チケットコード': 'ticket_code',
        'チケット名': 'ticket_name',
        'チケット種類': 'ticket_type',
        'チケット区別': 'ticket_category',
        '振替曜日': 'transfer_day',
        '振替グループ': 'transfer_group',
        '消化記号': 'consumption_symbol',
        '年間週': 'annual_weekly',
        'Max値': 'max_per_lesson',
        'チケット枚数': 'total_tickets',
        'カレンダーフラグ': 'calendar_flag',
        '年マタギ': 'year_carryover',
        '有効期限': 'expiry_date',
        'ブランドコード': 'brand__brand_code',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['チケットコード', 'チケット名']
    csv_unique_fields = ['ticket_code']
    csv_export_fields = [
        'ticket_code', 'ticket_name', 'ticket_type', 'ticket_category',
        'transfer_day', 'transfer_group', 'consumption_symbol',
        'annual_weekly', 'max_per_lesson', 'total_tickets',
        'calendar_flag', 'year_carryover', 'expiry_date',
        'brand.brand_name', 'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'ticket_code': 'チケットコード',
        'ticket_name': 'チケット名',
        'ticket_type': 'チケット種類',
        'ticket_category': 'チケット区別',
        'transfer_day': '振替曜日',
        'transfer_group': '振替グループ',
        'consumption_symbol': '消化記号',
        'annual_weekly': '年間週',
        'max_per_lesson': 'Max値',
        'total_tickets': 'チケット枚数',
        'calendar_flag': 'カレンダーフラグ',
        'year_carryover': '年マタギ',
        'expiry_date': '有効期限',
        'brand.brand_name': 'ブランド名',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T08b: コースチケット構成
# =============================================================================
class CourseTicketInline(admin.TabularInline):
    model = CourseTicket
    extra = 1
    can_delete = True
    raw_id_fields = ['ticket']
    fields = ['ticket', 'quantity', 'per_week', 'is_active']
    verbose_name = 'チケット'
    verbose_name_plural = 'T08b_コースチケット構成'


@admin.register(CourseTicket)
class CourseTicketAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['course', 'ticket', 'quantity', 'per_week', 'is_active']
    list_filter = ['is_active', 'course__brand']
    search_fields = ['course__course_name', 'ticket__ticket_name']
    raw_id_fields = ['course', 'ticket', 'tenant_ref']

    csv_import_fields = {
        'コースコード': 'course__course_code',
        'チケットコード': 'ticket__ticket_code',
        '付与枚数': 'quantity',
        '週あたり': 'per_week',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['コースコード', 'チケットコード']
    csv_unique_fields = []
    csv_export_fields = [
        'course.course_code', 'course.course_name',
        'ticket.ticket_code', 'ticket.ticket_name',
        'quantity', 'per_week', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'ticket.ticket_code': 'チケットコード',
        'ticket.ticket_name': 'チケット名',
        'quantity': '付与枚数',
        'per_week': '週あたり',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T09b: パックチケット構成
# =============================================================================
class PackTicketInline(admin.TabularInline):
    model = PackTicket
    extra = 1
    raw_id_fields = ['ticket']
    verbose_name = 'チケット'
    verbose_name_plural = 'T09b_パックチケット構成'


@admin.register(PackTicket)
class PackTicketAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['pack', 'ticket', 'quantity', 'per_week', 'is_active']
    list_filter = ['is_active', 'pack__brand']
    search_fields = ['pack__pack_name', 'ticket__ticket_name']
    raw_id_fields = ['pack', 'ticket', 'tenant_ref']

    csv_import_fields = {
        'パックコード': 'pack__pack_code',
        'チケットコード': 'ticket__ticket_code',
        '付与枚数': 'quantity',
        '週あたり': 'per_week',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['パックコード', 'チケットコード']
    csv_unique_fields = []
    csv_export_fields = [
        'pack.pack_code', 'pack.pack_name',
        'ticket.ticket_code', 'ticket.ticket_name',
        'quantity', 'per_week', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'pack.pack_code': 'パックコード',
        'pack.pack_name': 'パック名',
        'ticket.ticket_code': 'チケットコード',
        'ticket.ticket_name': 'チケット名',
        'quantity': '付与枚数',
        'per_week': '週あたり',
        'sort_order': '表示順',
        'is_active': '有効',
    }

"""
Transfer Admin - 引落結果・現金・振込入金管理
"""
from django.contrib import admin
from django.utils.html import format_html
from apps.core.admin_csv import CSVImportExportMixin

from ..models import DirectDebitResult, CashManagement, BankTransfer


@admin.register(DirectDebitResult)
class DirectDebitResultAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """引落結果管理"""
    list_display = [
        'guardian', 'debit_date', 'amount_display',
        'status_badge', 'failure_reason_display', 'notice_flag',
    ]
    list_filter = ['result_status', 'failure_reason', 'debit_date', 'notice_flag']
    search_fields = ['guardian__full_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'debit_date'

    fieldsets = (
        ('基本情報', {
            'fields': ('guardian', 'invoice', 'debit_date', 'amount')
        }),
        ('結果', {
            'fields': ('result_status', 'failure_reason', 'failure_detail')
        }),
        ('通知', {
            'fields': ('notice_flag', 'notice_date')
        }),
        ('再引落', {
            'fields': ('retry_count', 'next_retry_date'),
            'classes': ('collapse',)
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def amount_display(self, obj):
        return f"¥{obj.amount:,.0f}"
    amount_display.short_description = '引落金額'

    def status_badge(self, obj):
        colors = {
            'success': 'green',
            'failed': 'red',
            'pending': 'orange',
            'cancelled': 'gray',
        }
        color = colors.get(obj.result_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_result_status_display()
        )
    status_badge.short_description = 'ステータス'

    def failure_reason_display(self, obj):
        if obj.failure_reason:
            return obj.get_failure_reason_display()
        return '-'
    failure_reason_display.short_description = '失敗理由'

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = [
        'guardian.guardian_no', 'guardian.last_name', 'guardian.first_name',
        'invoice.invoice_no', 'debit_date', 'amount',
        'result_status', 'failure_reason', 'failure_detail',
        'notice_flag', 'notice_date', 'retry_count', 'next_retry_date',
        'notes', 'created_at',
    ]
    csv_export_headers = {
        'guardian.guardian_no': '保護者番号',
        'guardian.last_name': '保護者姓',
        'guardian.first_name': '保護者名',
        'invoice.invoice_no': '請求書番号',
        'debit_date': '引落日',
        'amount': '引落金額',
        'result_status': '結果ステータス',
        'failure_reason': '失敗理由',
        'failure_detail': '失敗詳細',
        'notice_flag': '通知済',
        'notice_date': '通知日',
        'retry_count': 'リトライ回数',
        'next_retry_date': '次回リトライ日',
        'notes': '備考',
        'created_at': '作成日時',
    }


@admin.register(CashManagement)
class CashManagementAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """現金管理"""
    list_display = [
        'guardian', 'transaction_date', 'transaction_type_display',
        'amount_display', 'status_badge', 'receipt_no', 'receipt_issued',
    ]
    list_filter = ['transaction_type', 'status', 'transaction_date', 'receipt_issued']
    search_fields = ['guardian__full_name', 'receipt_no']
    readonly_fields = ['received_by', 'received_at', 'created_at', 'updated_at']
    date_hierarchy = 'transaction_date'

    fieldsets = (
        ('基本情報', {
            'fields': ('guardian', 'invoice', 'transaction_date')
        }),
        ('取引内容', {
            'fields': ('amount', 'transaction_type', 'status')
        }),
        ('受領情報', {
            'fields': ('received_by', 'received_at')
        }),
        ('領収書', {
            'fields': ('receipt_no', 'receipt_issued')
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def transaction_type_display(self, obj):
        return obj.get_transaction_type_display()
    transaction_type_display.short_description = '取引種別'

    def amount_display(self, obj):
        if obj.transaction_type == 'refund':
            return format_html('<span style="color: red;">-¥{:,.0f}</span>', obj.amount)
        return format_html('<span style="color: green;">¥{:,.0f}</span>', obj.amount)
    amount_display.short_description = '金額'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'completed': 'green',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = [
        'guardian.guardian_no', 'guardian.last_name', 'guardian.first_name',
        'invoice.invoice_no', 'transaction_date', 'amount',
        'transaction_type', 'status', 'receipt_no', 'receipt_issued',
        'notes', 'created_at',
    ]
    csv_export_headers = {
        'guardian.guardian_no': '保護者番号',
        'guardian.last_name': '保護者姓',
        'guardian.first_name': '保護者名',
        'invoice.invoice_no': '請求書番号',
        'transaction_date': '取引日',
        'amount': '金額',
        'transaction_type': '取引種別',
        'status': 'ステータス',
        'receipt_no': '領収書番号',
        'receipt_issued': '領収書発行済',
        'notes': '備考',
        'created_at': '作成日時',
    }


@admin.register(BankTransfer)
class BankTransferAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """振込入金管理"""
    list_display = [
        'payer_name', 'transfer_date', 'amount_display',
        'guardian', 'status_badge', 'matched_at',
    ]
    list_filter = ['status', 'transfer_date']
    search_fields = ['payer_name', 'payer_name_kana', 'guardian__full_name']
    readonly_fields = ['matched_by', 'matched_at', 'created_at', 'updated_at']
    date_hierarchy = 'transfer_date'

    fieldsets = (
        ('振込情報', {
            'fields': ('transfer_date', 'amount', 'payer_name', 'payer_name_kana')
        }),
        ('振込元', {
            'fields': ('source_bank_name', 'source_branch_name'),
            'classes': ('collapse',)
        }),
        ('照合', {
            'fields': ('guardian', 'invoice', 'status')
        }),
        ('照合情報', {
            'fields': ('matched_by', 'matched_at'),
            'classes': ('collapse',)
        }),
        ('インポート', {
            'fields': ('import_batch_id', 'import_row_no'),
            'classes': ('collapse',)
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def amount_display(self, obj):
        return f"¥{obj.amount:,.0f}"
    amount_display.short_description = '振込金額'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'matched': 'blue',
            'applied': 'green',
            'unmatched': 'red',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = [
        'payer_name', 'payer_name_kana', 'transfer_date', 'amount',
        'source_bank_name', 'source_branch_name',
        'guardian.guardian_no', 'guardian.last_name', 'guardian.first_name',
        'invoice.invoice_no', 'status', 'matched_at',
        'import_batch_id', 'import_row_no', 'notes', 'created_at',
    ]
    csv_export_headers = {
        'payer_name': '振込人名',
        'payer_name_kana': '振込人名カナ',
        'transfer_date': '振込日',
        'amount': '振込金額',
        'source_bank_name': '振込元銀行',
        'source_branch_name': '振込元支店',
        'guardian.guardian_no': '保護者番号',
        'guardian.last_name': '保護者姓',
        'guardian.first_name': '保護者名',
        'invoice.invoice_no': '請求書番号',
        'status': 'ステータス',
        'matched_at': '照合日時',
        'import_batch_id': 'インポートバッチID',
        'import_row_no': 'インポート行番号',
        'notes': '備考',
        'created_at': '作成日時',
    }

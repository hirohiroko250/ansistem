"""
History Admin - 契約履歴・監査ログ管理
ContractHistoryAdmin, ContractHistoryInline, SystemAuditLogAdmin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import ContractHistory, SystemAuditLog


# =============================================================================
# 契約履歴（インライン）
# =============================================================================
class ContractHistoryInline(admin.TabularInline):
    model = ContractHistory
    extra = 0
    readonly_fields = [
        'action_type', 'change_summary', 'amount_before', 'amount_after',
        'discount_amount', 'mile_used', 'mile_discount', 'changed_by_name',
        'is_system_change', 'created_at'
    ]
    ordering = ['-created_at']
    max_num = 10
    can_delete = False
    verbose_name = '変更履歴'
    verbose_name_plural = '変更履歴'

    def has_add_permission(self, request, obj=None):
        return False


# =============================================================================
# 契約履歴（単体）
# =============================================================================
@admin.register(ContractHistory)
class ContractHistoryAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'contract', 'action_type', 'change_summary',
        'amount_before', 'amount_after', 'changed_by_name',
        'is_system_change', 'created_at'
    ]
    list_filter = ['action_type', 'is_system_change', 'created_at']
    search_fields = ['contract__contract_no', 'change_summary', 'changed_by_name']
    readonly_fields = [
        'contract', 'action_type', 'before_data', 'after_data',
        'change_summary', 'change_detail', 'amount_before', 'amount_after',
        'discount_amount', 'mile_used', 'mile_discount', 'effective_date',
        'changed_by', 'changed_by_name', 'is_system_change', 'ip_address',
        'created_at', 'updated_at'
    ]
    raw_id_fields = ['contract', 'changed_by']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('契約情報', {
            'fields': ('contract',)
        }),
        ('変更内容', {
            'fields': ('action_type', 'change_summary', 'change_detail', 'effective_date')
        }),
        ('金額', {
            'fields': ('amount_before', 'amount_after', 'discount_amount', 'mile_used', 'mile_discount')
        }),
        ('変更データ', {
            'fields': ('before_data', 'after_data'),
            'classes': ('collapse',)
        }),
        ('変更者情報', {
            'fields': ('changed_by', 'changed_by_name', 'is_system_change', 'ip_address')
        }),
        ('日時', {
            'fields': ('created_at', 'updated_at')
        }),
    )

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
        'contract.contract_no', 'action_type', 'change_summary',
        'amount_before', 'amount_after', 'discount_amount',
        'mile_used', 'mile_discount', 'effective_date',
        'changed_by_name', 'is_system_change', 'created_at',
    ]
    csv_export_headers = {
        'contract.contract_no': '契約番号',
        'action_type': '操作種別',
        'change_summary': '変更概要',
        'amount_before': '変更前金額',
        'amount_after': '変更後金額',
        'discount_amount': '割引額',
        'mile_used': '使用マイル',
        'mile_discount': 'マイル割引',
        'effective_date': '有効日',
        'changed_by_name': '変更者',
        'is_system_change': 'システム変更',
        'created_at': '作成日時',
    }


# =============================================================================
# システム監査ログ
# =============================================================================
@admin.register(SystemAuditLog)
class SystemAuditLogAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'created_at', 'entity_type', 'action_type', 'action_detail',
        'user_name', 'is_system_action', 'is_success'
    ]
    list_filter = ['entity_type', 'action_type', 'is_system_action', 'is_success', 'created_at']
    search_fields = ['entity_name', 'action_detail', 'user_name', 'user_email', 'entity_id']
    readonly_fields = [
        'entity_type', 'entity_id', 'entity_name', 'action_type', 'action_detail',
        'before_data', 'after_data', 'changed_fields',
        'student', 'guardian', 'contract',
        'user', 'user_name', 'user_email',
        'is_system_action', 'ip_address', 'user_agent', 'request_path', 'request_method',
        'is_success', 'error_message', 'notes', 'created_at', 'updated_at'
    ]
    raw_id_fields = ['student', 'guardian', 'contract', 'user']
    date_hierarchy = 'created_at'
    list_per_page = 50

    fieldsets = (
        ('エンティティ情報', {
            'fields': ('entity_type', 'entity_id', 'entity_name')
        }),
        ('操作内容', {
            'fields': ('action_type', 'action_detail', 'is_success', 'error_message')
        }),
        ('変更データ', {
            'fields': ('before_data', 'after_data', 'changed_fields'),
            'classes': ('collapse',)
        }),
        ('関連エンティティ', {
            'fields': ('student', 'guardian', 'contract')
        }),
        ('操作者情報', {
            'fields': ('user', 'user_name', 'user_email', 'is_system_action')
        }),
        ('リクエスト情報', {
            'fields': ('ip_address', 'user_agent', 'request_path', 'request_method'),
            'classes': ('collapse',)
        }),
        ('日時', {
            'fields': ('created_at', 'updated_at')
        }),
    )

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
        'created_at', 'entity_type', 'entity_name', 'action_type', 'action_detail',
        'user_name', 'user_email', 'is_system_action', 'is_success',
        'error_message', 'ip_address', 'request_path', 'request_method',
    ]
    csv_export_headers = {
        'created_at': '日時',
        'entity_type': 'エンティティ種別',
        'entity_name': 'エンティティ名',
        'action_type': '操作種別',
        'action_detail': '操作詳細',
        'user_name': '操作者名',
        'user_email': '操作者メール',
        'is_system_action': 'システム操作',
        'is_success': '成功',
        'error_message': 'エラーメッセージ',
        'ip_address': 'IPアドレス',
        'request_path': 'リクエストパス',
        'request_method': 'リクエストメソッド',
    }

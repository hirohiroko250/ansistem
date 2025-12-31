"""
Balance Admin - 預り金・相殺・返金・マイル管理
"""
from django.contrib import admin
from django.utils.html import format_html
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from apps.students.models import Guardian
from ..models import GuardianBalance, OffsetLog, RefundRequest, MileTransaction


class GuardianBalanceResource(resources.ModelResource):
    """保護者残高インポート/エクスポート用リソース"""
    guardian_no = fields.Field(
        column_name='保護者番号',
        attribute='guardian',
        widget=ForeignKeyWidget(Guardian, 'guardian_no')
    )
    guardian_name = fields.Field(
        column_name='保護者名',
        readonly=True
    )
    balance = fields.Field(
        column_name='残高',
        attribute='balance'
    )
    last_updated = fields.Field(
        column_name='最終更新日',
        attribute='last_updated',
        readonly=True
    )

    class Meta:
        model = GuardianBalance
        fields = ('guardian_no', 'guardian_name', 'balance', 'last_updated')
        export_order = ('guardian_no', 'guardian_name', 'balance', 'last_updated')
        import_id_fields = ['guardian']

    def dehydrate_guardian_name(self, obj):
        """エクスポート時に保護者名を出力"""
        return obj.guardian.full_name if obj.guardian else ''

    def before_import_row(self, row, **kwargs):
        """インポート前処理"""
        guardian_no = row.get('保護者番号')
        if guardian_no:
            try:
                guardian = Guardian.objects.get(guardian_no=guardian_no)
                row['guardian'] = guardian.id
            except Guardian.DoesNotExist:
                pass


@admin.register(GuardianBalance)
class GuardianBalanceAdmin(ImportExportModelAdmin):
    """預り金残高管理"""
    resource_class = GuardianBalanceResource
    list_display = ['guardian', 'guardian_no_display', 'balance_display', 'last_updated']
    search_fields = ['guardian__last_name', 'guardian__first_name', 'guardian__guardian_no']
    list_filter = ['last_updated']
    readonly_fields = ['balance', 'last_updated']

    def guardian_no_display(self, obj):
        return obj.guardian.guardian_no if obj.guardian else '-'
    guardian_no_display.short_description = '保護者番号'

    def balance_display(self, obj):
        balance = float(obj.balance) if obj.balance else 0
        formatted = f"¥{balance:,.0f}"
        if balance > 0:
            return format_html('<span style="color: green;">{}</span>', formatted)
        elif balance < 0:
            return format_html('<span style="color: red;">{}</span>', formatted)
        return formatted
    balance_display.short_description = '残高'


@admin.register(OffsetLog)
class OffsetLogAdmin(admin.ModelAdmin):
    """相殺ログ管理"""
    list_display = [
        'guardian', 'transaction_type', 'amount_display',
        'balance_after_display', 'created_at',
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['guardian__full_name']
    readonly_fields = ['guardian', 'invoice', 'payment', 'transaction_type', 'amount', 'balance_after', 'created_at']
    date_hierarchy = 'created_at'

    def amount_display(self, obj):
        if obj.amount > 0:
            return format_html('<span style="color: green;">+¥{:,.0f}</span>', obj.amount)
        return format_html('<span style="color: red;">¥{:,.0f}</span>', obj.amount)
    amount_display.short_description = '金額'

    def balance_after_display(self, obj):
        return f"¥{obj.balance_after:,.0f}"
    balance_after_display.short_description = '取引後残高'


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    """返金申請管理"""
    list_display = [
        'request_no', 'guardian', 'refund_amount_display',
        'refund_method', 'status_badge', 'requested_at',
    ]
    list_filter = ['status', 'refund_method', 'requested_at']
    search_fields = ['request_no', 'guardian__full_name']
    readonly_fields = [
        'request_no', 'requested_by', 'requested_at',
        'approved_by', 'approved_at', 'processed_at',
    ]
    date_hierarchy = 'requested_at'

    fieldsets = (
        ('基本情報', {
            'fields': ('request_no', 'guardian', 'invoice')
        }),
        ('返金内容', {
            'fields': ('refund_amount', 'refund_method', 'reason')
        }),
        ('ステータス', {
            'fields': ('status',)
        }),
        ('申請情報', {
            'fields': ('requested_by', 'requested_at'),
            'classes': ('collapse',)
        }),
        ('承認情報', {
            'fields': ('approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        ('処理情報', {
            'fields': ('processed_at', 'process_notes'),
            'classes': ('collapse',)
        }),
    )

    def refund_amount_display(self, obj):
        return f"¥{obj.refund_amount:,.0f}"
    refund_amount_display.short_description = '返金額'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'blue',
            'processing': 'purple',
            'completed': 'green',
            'rejected': 'red',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'


@admin.register(MileTransaction)
class MileTransactionAdmin(admin.ModelAdmin):
    """マイル取引管理"""
    list_display = [
        'guardian', 'transaction_type', 'miles_display',
        'balance_after', 'discount_amount_display', 'created_at',
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['guardian__full_name']
    readonly_fields = ['guardian', 'invoice', 'transaction_type', 'miles', 'balance_after', 'discount_amount', 'created_at']
    date_hierarchy = 'created_at'

    def miles_display(self, obj):
        if obj.miles > 0:
            return format_html('<span style="color: green;">+{}pt</span>', obj.miles)
        return format_html('<span style="color: red;">{}pt</span>', obj.miles)
    miles_display.short_description = 'マイル'

    def discount_amount_display(self, obj):
        if obj.discount_amount > 0:
            return f"¥{obj.discount_amount:,.0f}"
        return '-'
    discount_amount_display.short_description = '割引額'

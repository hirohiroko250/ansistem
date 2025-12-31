"""
Invoice Admin - 請求書・入金管理
"""
from django.contrib import admin
from django.utils.html import format_html

from ..models import Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    """請求明細インライン"""
    model = InvoiceLine
    extra = 0
    readonly_fields = ['line_total', 'tax_amount']
    fields = [
        'student', 'item_name', 'item_type',
        'quantity', 'unit_price', 'line_total',
        'tax_category', 'tax_rate', 'tax_amount',
        'discount_amount', 'discount_reason',
    ]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """請求書管理"""
    list_display = [
        'invoice_no', 'guardian', 'billing_period',
        'total_amount_display', 'paid_amount_display', 'balance_due_display',
        'status_badge', 'issue_date',
    ]
    list_filter = ['status', 'billing_year', 'billing_month']
    search_fields = ['invoice_no', 'guardian__full_name']
    readonly_fields = [
        'invoice_no', 'subtotal', 'tax_amount', 'total_amount',
        'paid_amount', 'balance_due', 'confirmed_at', 'confirmed_by',
        'created_at', 'updated_at',
    ]
    inlines = [InvoiceLineInline]

    fieldsets = (
        ('基本情報', {
            'fields': ('invoice_no', 'guardian', 'billing_year', 'billing_month', 'status')
        }),
        ('日付', {
            'fields': ('issue_date', 'due_date')
        }),
        ('金額', {
            'fields': (
                'subtotal', 'tax_amount', 'discount_total',
                'miles_used', 'miles_discount',
                'total_amount', 'paid_amount', 'balance_due',
            )
        }),
        ('確定情報', {
            'fields': ('confirmed_at', 'confirmed_by'),
            'classes': ('collapse',)
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def billing_period(self, obj):
        return f"{obj.billing_year}年{obj.billing_month:02d}月"
    billing_period.short_description = '請求対象月'

    def total_amount_display(self, obj):
        return f"¥{obj.total_amount:,.0f}"
    total_amount_display.short_description = '請求合計'

    def paid_amount_display(self, obj):
        return f"¥{obj.paid_amount:,.0f}"
    paid_amount_display.short_description = '入金済'

    def balance_due_display(self, obj):
        if obj.balance_due > 0:
            return format_html('<span style="color: red;">¥{:,.0f}</span>', obj.balance_due)
        return f"¥{obj.balance_due:,.0f}"
    balance_due_display.short_description = '未払額'

    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'issued': 'blue',
            'paid': 'green',
            'partial': 'orange',
            'overdue': 'red',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """入金管理"""
    list_display = [
        'payment_no', 'guardian', 'payment_date',
        'amount_display', 'method_display', 'status_badge',
    ]
    list_filter = ['status', 'method', 'payment_date']
    search_fields = ['payment_no', 'guardian__full_name', 'payer_name']
    readonly_fields = ['payment_no', 'registered_by', 'created_at', 'updated_at']
    date_hierarchy = 'payment_date'

    fieldsets = (
        ('基本情報', {
            'fields': ('payment_no', 'guardian', 'invoice')
        }),
        ('入金詳細', {
            'fields': ('payment_date', 'amount', 'method', 'status')
        }),
        ('振替結果', {
            'fields': ('debit_result_code', 'debit_result_message'),
            'classes': ('collapse',)
        }),
        ('振込情報', {
            'fields': ('payer_name', 'bank_name'),
            'classes': ('collapse',)
        }),
        ('その他', {
            'fields': ('notes', 'registered_by'),
            'classes': ('collapse',)
        }),
    )

    def amount_display(self, obj):
        return f"¥{obj.amount:,.0f}"
    amount_display.short_description = '金額'

    def method_display(self, obj):
        return obj.get_method_display()
    method_display.short_description = '入金方法'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'success': 'green',
            'failed': 'red',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'

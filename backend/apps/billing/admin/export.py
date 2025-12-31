"""
Export Admin - 決済代行・請求期間・引落エクスポート管理
"""
from django.contrib import admin
from django.utils.html import format_html

from ..models import PaymentProvider, BillingPeriod, DebitExportBatch, DebitExportLine


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    """決済代行会社マスタ管理"""
    list_display = [
        'code', 'name', 'consignor_code',
        'closing_day', 'debit_day', 'is_active_badge',
    ]
    list_filter = ['is_active']
    search_fields = ['code', 'name', 'consignor_code']
    ordering = ['sort_order', 'code']

    fieldsets = (
        ('基本情報', {
            'fields': ('code', 'name', 'is_active', 'sort_order')
        }),
        ('委託者情報', {
            'fields': ('consignor_code', 'default_bank_code')
        }),
        ('ファイル設定', {
            'fields': ('file_encoding',)
        }),
        ('締日・引落日設定', {
            'fields': ('closing_day', 'debit_day')
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    is_active_badge.short_description = '有効'


@admin.register(BillingPeriod)
class BillingPeriodAdmin(admin.ModelAdmin):
    """請求期間/締日管理"""
    list_display = [
        'provider', 'period_display', 'closing_date',
        'is_closed_badge', 'closed_at', 'closed_by',
    ]
    list_filter = ['provider', 'is_closed', 'year']
    search_fields = ['provider__name']
    ordering = ['-year', '-month', 'provider']
    readonly_fields = ['closed_at', 'closed_by', 'created_at', 'updated_at']
    actions = ['close_periods', 'reopen_periods', 'generate_export_batch']

    fieldsets = (
        ('基本情報', {
            'fields': ('provider', 'year', 'month', 'closing_date')
        }),
        ('締めステータス', {
            'fields': ('is_closed', 'closed_at', 'closed_by')
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def period_display(self, obj):
        return f"{obj.year}年{obj.month:02d}月"
    period_display.short_description = '対象期間'

    def is_closed_badge(self, obj):
        if obj.is_closed:
            return format_html('<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px;">締済</span>')
        return format_html('<span style="background-color: orange; color: white; padding: 2px 8px; border-radius: 4px;">未締</span>')
    is_closed_badge.short_description = '締めステータス'

    @admin.action(description='選択した期間を締める')
    def close_periods(self, request, queryset):
        for period in queryset.filter(is_closed=False):
            period.close(request.user)
        self.message_user(request, f'{queryset.count()}件の請求期間を締めました。')

    @admin.action(description='選択した期間の締めを解除')
    def reopen_periods(self, request, queryset):
        for period in queryset.filter(is_closed=True):
            period.reopen()
        self.message_user(request, f'{queryset.count()}件の請求期間の締めを解除しました。')

    @admin.action(description='選択した期間の引落エクスポートバッチを生成')
    def generate_export_batch(self, request, queryset):
        """引落エクスポートバッチを生成"""
        from apps.billing.services.export_service import DirectDebitExportService

        created_count = 0
        for period in queryset:
            tenant_id = period.tenant_id or 0
            service = DirectDebitExportService(tenant_id)
            try:
                batch = service.generate_batch(
                    period.provider,
                    period.year,
                    period.month,
                    request.user
                )
                created_count += 1
                self.message_user(
                    request,
                    f'{period}: バッチ {batch.batch_no} を作成しました（{batch.total_count}件, ¥{batch.total_amount:,.0f}）',
                    level='success'
                )
            except Exception as e:
                self.message_user(
                    request,
                    f'{period}: バッチ作成に失敗しました - {str(e)}',
                    level='error'
                )

        if created_count > 0:
            self.message_user(request, f'合計{created_count}件のバッチを作成しました。')


class DebitExportLineInline(admin.TabularInline):
    """引落エクスポート明細インライン"""
    model = DebitExportLine
    extra = 0
    readonly_fields = [
        'line_no', 'guardian', 'invoice', 'amount',
        'bank_code', 'branch_code', 'account_number',
        'account_holder_kana', 'result_status_badge', 'result_message',
    ]
    fields = [
        'line_no', 'guardian', 'amount',
        'bank_code', 'branch_code', 'account_number',
        'account_holder_kana', 'result_status_badge', 'result_message',
    ]
    can_delete = False

    def result_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'success': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.result_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_result_status_display()
        )
    result_status_badge.short_description = '結果'


@admin.register(DebitExportBatch)
class DebitExportBatchAdmin(admin.ModelAdmin):
    """引落エクスポートバッチ管理"""
    list_display = [
        'batch_no', 'provider', 'billing_period',
        'total_count', 'total_amount_display',
        'success_count', 'failed_count',
        'status_badge', 'export_date',
    ]
    list_filter = ['provider', 'status', 'billing_period__year']
    search_fields = ['batch_no', 'provider__name']
    readonly_fields = [
        'batch_no', 'total_count', 'total_amount',
        'success_count', 'success_amount', 'failed_count', 'failed_amount',
        'export_date', 'exported_by',
        'result_imported_at', 'result_imported_by',
        'created_at', 'updated_at',
    ]
    inlines = [DebitExportLineInline]
    actions = ['export_to_csv_action']
    change_form_template = 'admin/billing/debitexportbatch/change_form.html'

    fieldsets = (
        ('基本情報', {
            'fields': ('batch_no', 'provider', 'billing_period', 'status')
        }),
        ('集計情報', {
            'fields': ('total_count', 'total_amount')
        }),
        ('結果集計', {
            'fields': ('success_count', 'success_amount', 'failed_count', 'failed_amount'),
            'classes': ('collapse',)
        }),
        ('エクスポート情報', {
            'fields': ('export_date', 'exported_by'),
            'classes': ('collapse',)
        }),
        ('結果取込情報', {
            'fields': ('result_imported_at', 'result_imported_by'),
            'classes': ('collapse',)
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def total_amount_display(self, obj):
        return f"¥{obj.total_amount:,.0f}"
    total_amount_display.short_description = '総金額'

    def status_badge(self, obj):
        colors = {
            'draft': 'orange',
            'exported': 'blue',
            'result_imported': 'green',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'

    @admin.action(description='選択したバッチのCSVをエクスポート')
    def export_to_csv_action(self, request, queryset):
        """CSVエクスポートアクション"""
        from django.http import HttpResponse
        from apps.billing.services.export_service import DirectDebitExportService

        if queryset.count() != 1:
            self.message_user(request, 'CSVエクスポートは1件ずつ行ってください。', level='error')
            return

        batch = queryset.first()
        tenant_id = batch.tenant_id or 0

        service = DirectDebitExportService(tenant_id)
        csv_bytes = service.export_to_csv_bytes(batch, request.user)
        filename = service.get_export_filename(batch)

        response = HttpResponse(csv_bytes, content_type='text/csv; charset=shift_jis')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:batch_id>/import-result/',
                self.admin_site.admin_view(self.import_result_view),
                name='billing_debitexportbatch_import_result'
            ),
        ]
        return custom_urls + urls

    def import_result_view(self, request, batch_id):
        """結果インポートビュー"""
        from django.shortcuts import redirect, get_object_or_404
        from django.contrib import messages
        from apps.billing.services.import_service import DirectDebitImportService

        batch = get_object_or_404(DebitExportBatch, pk=batch_id)

        if request.method == 'POST':
            if 'result_file' not in request.FILES:
                messages.error(request, '結果ファイルを選択してください。')
                return redirect('..')

            result_file = request.FILES['result_file']
            file_content = result_file.read()

            tenant_id = batch.tenant_id or 0
            service = DirectDebitImportService(tenant_id)
            result = service.import_result_csv(batch, file_content, request.user)

            messages.success(
                request,
                f'インポート完了: 成功{result["success"]}件, 失敗{result["failed"]}件, 未照合{result["not_found"]}件'
            )
            return redirect('..')

        return redirect('..')


@admin.register(DebitExportLine)
class DebitExportLineAdmin(admin.ModelAdmin):
    """引落エクスポート明細管理"""
    list_display = [
        'batch', 'line_no', 'guardian', 'amount_display',
        'bank_code', 'branch_code', 'account_number',
        'result_status_badge',
    ]
    list_filter = ['batch__provider', 'result_status']
    search_fields = ['guardian__last_name', 'guardian__first_name', 'customer_code']
    readonly_fields = [
        'batch', 'line_no', 'guardian', 'invoice',
        'bank_code', 'branch_code', 'account_type', 'account_number',
        'account_holder_kana', 'amount', 'customer_code',
        'result_code', 'result_status', 'result_message',
        'direct_debit_result', 'payment',
        'created_at', 'updated_at',
    ]

    def amount_display(self, obj):
        return f"¥{obj.amount:,.0f}"
    amount_display.short_description = '金額'

    def result_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'success': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.result_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_result_status_display()
        )
    result_status_badge.short_description = '結果'

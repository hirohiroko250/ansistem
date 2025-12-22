"""
Billing Admin - 請求・入金・預り金・マイル管理

Note: Billing app tables need to be created via migrations.
Admin registration is conditional on tables existing.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db import connection
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

# Check if billing tables exist before registering admin
def billing_tables_exist():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'billing_invoices')")
            return cursor.fetchone()[0]
    except:
        return False


# Always register admin (tables should exist after migration)
if True:  # billing_tables_exist():
    from .models import (
        Invoice, InvoiceLine, Payment, GuardianBalance,
        OffsetLog, RefundRequest, MileTransaction,
        DirectDebitResult, CashManagement, BankTransfer
    )

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


    # GuardianBalance用のリソースクラス（インポート/エクスポート）
    from apps.students.models import Guardian

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
            # 保護者番号から保護者を検索
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


    @admin.register(DirectDebitResult)
    class DirectDebitResultAdmin(admin.ModelAdmin):
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


    @admin.register(CashManagement)
    class CashManagementAdmin(admin.ModelAdmin):
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


    @admin.register(BankTransfer)
    class BankTransferAdmin(admin.ModelAdmin):
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


    # =========================================================================
    # PaymentProvider (決済代行会社マスタ)
    # =========================================================================
    from .models import PaymentProvider, BillingPeriod, DebitExportBatch, DebitExportLine

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

            # tenant_id を取得
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

            # GET の場合は詳細画面にリダイレクト
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

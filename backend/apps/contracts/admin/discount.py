"""
Discount Admin - 割引マスタ管理
DiscountAdmin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import Discount


# =============================================================================
# T07: 割引マスタ
# =============================================================================
@admin.register(Discount)
class DiscountAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'discount_code', 'discount_name', 'discount_type',
        'is_employee_discount', 'applicable_brand', 'applicable_category',
        'calculation_type', 'get_value_display', 'end_condition', 'is_recurring',
        'valid_from', 'valid_until', 'is_active', 'tenant_ref'
    ]
    list_filter = [
        'tenant_ref', 'discount_type', 'calculation_type',
        'is_employee_discount', 'applicable_category', 'end_condition',
        'is_recurring', 'is_active'
    ]
    search_fields = ['discount_code', 'discount_name']
    ordering = ['discount_code']
    raw_id_fields = ['tenant_ref', 'applicable_brand']

    fieldsets = (
        ('基本情報', {
            'fields': ('discount_code', 'discount_name', 'discount_type')
        }),
        ('社割設定', {
            'fields': ('is_employee_discount',),
            'description': '社員の場合に自動適用される割引にチェック'
        }),
        ('割引設定', {
            'fields': ('calculation_type', 'value'),
            'description': '割合の場合は%、固定金額の場合は円で入力'
        }),
        ('適用対象', {
            'fields': ('applicable_brand', 'applicable_category'),
            'description': 'ブランドが空の場合は全ブランドに適用'
        }),
        ('終了条件', {
            'fields': ('end_condition', 'is_recurring'),
            'description': '割引の終了条件と繰り返し設定'
        }),
        ('適用期間', {
            'fields': ('valid_from', 'valid_until'),
            'description': '空欄の場合は常に適用'
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('ステータス', {
            'fields': ('is_active', 'tenant_ref')
        }),
    )

    actions = ['create_task_for_discount']

    @admin.display(description='値')
    def get_value_display(self, obj):
        if obj.calculation_type == 'percentage':
            return f"{obj.value}%"
        else:
            return f"¥{obj.value:,.0f}"

    @admin.action(description='選択した割引の確認タスクを作成')
    def create_task_for_discount(self, request, queryset):
        from apps.tasks.models import Task
        created_count = 0
        for discount in queryset:
            Task.objects.create(
                tenant_id=discount.tenant_id,
                task_type='request',
                title=f'割引確認: {discount.discount_name}',
                description=f'割引コード: {discount.discount_code}\n'
                           f'割引種別: {discount.get_discount_type_display()}\n'
                           f'計算種別: {discount.get_calculation_type_display()}\n'
                           f'値: {discount.value}\n'
                           f'適用期間: {discount.valid_from or "なし"} 〜 {discount.valid_until or "なし"}',
                status='new',
                priority='normal',
                source_type='discount',
                source_id=discount.id,
                source_url=f'/admin/contracts/discount/{discount.id}/change/',
            )
            created_count += 1
        self.message_user(request, f'{created_count}件の確認タスクを作成しました。')

    csv_import_fields = {
        '割引コード': 'discount_code',
        '割引名': 'discount_name',
        '割引種別': 'discount_type',
        '計算種別': 'calculation_type',
        '値': 'value',
        '適用開始日': 'valid_from',
        '適用終了日': 'valid_until',
        '有効': 'is_active',
    }
    csv_required_fields = ['割引コード', '割引名', '値']
    csv_unique_fields = ['discount_code']
    csv_export_fields = [
        'discount_code', 'discount_name', 'discount_type', 'calculation_type',
        'value', 'valid_from', 'valid_until', 'is_active'
    ]
    csv_export_headers = {
        'discount_code': '割引コード',
        'discount_name': '割引名',
        'discount_type': '割引種別',
        'calculation_type': '計算種別',
        'value': '値',
        'valid_from': '適用開始日',
        'valid_until': '適用終了日',
        'is_active': '有効',
    }

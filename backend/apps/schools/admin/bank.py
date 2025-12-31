"""
Bank Admin - 金融機関マスタ管理Admin
BankTypeAdmin, BankAdmin, BankBranchAdmin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import BankType, Bank, BankBranch


class BankBranchInline(admin.TabularInline):
    """支店インライン編集"""
    model = BankBranch
    extra = 1
    fields = ['branch_code', 'branch_name', 'branch_name_kana', 'branch_name_hiragana', 'aiueo_row', 'is_active']


@admin.register(BankType)
class BankTypeAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """金融機関種別Admin"""
    list_display = ['type_code', 'type_name', 'type_label', 'sort_order', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active']
    search_fields = ['type_code', 'type_name', 'type_label']
    ordering = ['sort_order', 'type_code']
    raw_id_fields = ['tenant_ref']

    csv_import_fields = {
        '種別コード': 'type_code',
        '種別名': 'type_name',
        '表示名': 'type_label',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['種別コード', '種別名']
    csv_unique_fields = ['type_code']
    csv_export_fields = ['type_code', 'type_name', 'type_label', 'sort_order', 'is_active']
    csv_export_headers = {
        'type_code': '種別コード',
        'type_name': '種別名',
        'type_label': '表示名',
        'sort_order': '並び順',
        'is_active': '有効',
    }


@admin.register(Bank)
class BankAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """金融機関マスタAdmin"""
    list_display = [
        'bank_code', 'bank_name', 'bank_name_kana', 'aiueo_row',
        'bank_type', 'get_branch_count', 'is_active', 'tenant_ref'
    ]
    list_filter = ['tenant_ref', 'is_active', 'aiueo_row', 'bank_type']
    search_fields = ['bank_code', 'bank_name', 'bank_name_kana', 'bank_name_hiragana']
    ordering = ['sort_order', 'bank_name_hiragana']
    raw_id_fields = ['tenant_ref']
    autocomplete_fields = ['bank_type']
    inlines = [BankBranchInline]

    fieldsets = (
        ('基本情報', {
            'fields': ('bank_code', 'bank_name', 'bank_type')
        }),
        ('カナ表記', {
            'fields': ('bank_name_kana', 'bank_name_half_kana', 'bank_name_hiragana', 'aiueo_row')
        }),
        ('表示設定', {
            'fields': ('sort_order', 'is_active', 'tenant_ref')
        }),
    )

    @admin.display(description='支店数')
    def get_branch_count(self, obj):
        return obj.branches.filter(is_active=True).count()

    csv_import_fields = {
        '金融機関コード': 'bank_code',
        '金融機関名': 'bank_name',
        '金融機関名カナ': 'bank_name_kana',
        '金融機関名半角カナ': 'bank_name_half_kana',
        '金融機関名ひらがな': 'bank_name_hiragana',
        'あいうえお行': 'aiueo_row',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['金融機関コード', '金融機関名']
    csv_unique_fields = ['bank_code']
    csv_export_fields = [
        'bank_code', 'bank_name', 'bank_name_kana', 'bank_name_half_kana',
        'bank_name_hiragana', 'aiueo_row', 'bank_type.type_code', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'bank_code': '金融機関コード',
        'bank_name': '金融機関名',
        'bank_name_kana': '金融機関名カナ',
        'bank_name_half_kana': '金融機関名半角カナ',
        'bank_name_hiragana': '金融機関名ひらがな',
        'aiueo_row': 'あいうえお行',
        'bank_type.type_code': '種別コード',
        'sort_order': '並び順',
        'is_active': '有効',
    }


@admin.register(BankBranch)
class BankBranchAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """金融機関支店マスタAdmin"""
    list_display = [
        'branch_code', 'branch_name', 'bank', 'branch_name_kana',
        'aiueo_row', 'is_active', 'tenant_ref'
    ]
    list_filter = ['tenant_ref', 'is_active', 'aiueo_row', 'bank']
    search_fields = ['branch_code', 'branch_name', 'branch_name_kana', 'bank__bank_name']
    ordering = ['bank', 'sort_order', 'branch_name_hiragana']
    raw_id_fields = ['tenant_ref']
    autocomplete_fields = ['bank']

    fieldsets = (
        ('基本情報', {
            'fields': ('bank', 'branch_code', 'branch_name')
        }),
        ('カナ表記', {
            'fields': ('branch_name_kana', 'branch_name_half_kana', 'branch_name_hiragana', 'aiueo_row')
        }),
        ('表示設定', {
            'fields': ('sort_order', 'is_active', 'tenant_ref')
        }),
    )

    csv_import_fields = {
        '金融機関コード': 'bank__bank_code',
        '支店コード': 'branch_code',
        '支店名': 'branch_name',
        '支店名カナ': 'branch_name_kana',
        '支店名半角カナ': 'branch_name_half_kana',
        '支店名ひらがな': 'branch_name_hiragana',
        'あいうえお行': 'aiueo_row',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['金融機関コード', '支店コード', '支店名']
    csv_unique_fields = ['branch_code']
    csv_export_fields = [
        'bank.bank_code', 'bank.bank_name', 'branch_code', 'branch_name',
        'branch_name_kana', 'branch_name_half_kana', 'branch_name_hiragana',
        'aiueo_row', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'bank.bank_code': '金融機関コード',
        'bank.bank_name': '金融機関名',
        'branch_code': '支店コード',
        'branch_name': '支店名',
        'branch_name_kana': '支店名カナ',
        'branch_name_half_kana': '支店名半角カナ',
        'branch_name_hiragana': '支店名ひらがな',
        'aiueo_row': 'あいうえお行',
        'sort_order': '並び順',
        'is_active': '有効',
    }

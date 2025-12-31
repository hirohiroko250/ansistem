"""
Guardian Admin - 保護者管理Admin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import Guardian


@admin.register(Guardian)
class GuardianAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['guardian_no', 'old_id', 'last_name', 'first_name', 'email', 'phone_mobile', 'prefecture', 'city', 'nearest_school', 'tenant_ref']
    list_display_links = ['guardian_no', 'last_name', 'first_name']
    list_filter = ['tenant_ref', 'prefecture', 'nearest_school']
    search_fields = ['guardian_no', 'old_id', 'last_name', 'first_name', 'email', 'phone', 'phone_mobile', 'postal_code', 'city']
    ordering = ['-created_at']
    raw_id_fields = ['tenant_ref', 'user', 'nearest_school']

    fieldsets = (
        ('基本情報', {
            'fields': ('guardian_no', 'old_id', 'user', 'tenant_ref')
        }),
        ('氏名', {
            'fields': (('last_name', 'first_name'), ('last_name_kana', 'first_name_kana'), ('last_name_roman', 'first_name_roman'))
        }),
        ('属性', {
            'fields': ('birth_date',)
        }),
        ('連絡先', {
            'fields': ('email', 'phone', 'phone_mobile', 'line_id')
        }),
        ('住所', {
            'fields': ('postal_code', ('prefecture', 'city'), 'address1', 'address2')
        }),
        ('勤務先', {
            'fields': ('workplace', 'workplace_phone'),
            'classes': ('collapse',)
        }),
        ('銀行口座情報', {
            'fields': (
                ('bank_name', 'bank_code'),
                ('branch_name', 'branch_code'),
                'account_type',
                'account_number',
                ('account_holder', 'account_holder_kana'),
            ),
            'description': '口座振替に使用する銀行口座情報'
        }),
        ('引き落とし設定', {
            'fields': ('withdrawal_day', 'payment_registered', 'payment_registered_at'),
        }),
        ('登録時情報', {
            'fields': ('nearest_school', 'interested_brands', 'referral_source', 'expectations'),
            'description': '新規登録時に入力された情報'
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    # CSV Import設定
    csv_import_fields = {
        '保護者番号': 'guardian_no',
        '旧システムID': 'old_id',
        '姓': 'last_name',
        '名': 'first_name',
        '姓（カナ）': 'last_name_kana',
        '名（カナ）': 'first_name_kana',
        'メールアドレス': 'email',
        '電話番号': 'phone',
        '携帯電話': 'phone_mobile',
        '勤務先': 'workplace',
        '勤務先電話番号': 'workplace_phone',
        '郵便番号': 'postal_code',
        '都道府県': 'prefecture',
        '市区町村': 'city',
        '住所1': 'address1',
        '住所2': 'address2',
        '紹介元': 'referral_source',
        '期待・要望': 'expectations',
        '備考': 'notes',
    }
    csv_required_fields = ['姓', '名']
    csv_unique_fields = ['guardian_no']
    csv_export_fields = [
        'guardian_no', 'old_id', 'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
        'email', 'phone', 'phone_mobile', 'workplace', 'workplace_phone',
        'postal_code', 'prefecture', 'city', 'address1', 'address2',
        'nearest_school.school_name', 'referral_source', 'expectations', 'notes'
    ]
    csv_export_headers = {
        'guardian_no': '保護者番号',
        'old_id': '旧システムID',
        'last_name': '姓',
        'first_name': '名',
        'last_name_kana': '姓（カナ）',
        'first_name_kana': '名（カナ）',
        'email': 'メールアドレス',
        'phone': '電話番号',
        'phone_mobile': '携帯電話',
        'workplace': '勤務先',
        'workplace_phone': '勤務先電話番号',
        'postal_code': '郵便番号',
        'prefecture': '都道府県',
        'city': '市区町村',
        'address1': '住所1',
        'address2': '住所2',
        'nearest_school.school_name': '最寄り校舎',
        'referral_source': '紹介元',
        'expectations': '期待・要望',
        'notes': '備考',
    }

"""
School Admin - 校舎管理Admin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import School
from .importer import SchoolCSVImporter


@admin.register(School)
class SchoolAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """校舎マスタAdmin（T10_校舎情報対応）"""
    list_display = ['tenant_ref', 'school_code', 'school_name', 'prefecture', 'city', 'is_active']
    list_filter = ['tenant_ref', 'is_active', 'prefecture']
    search_fields = ['school_code', 'school_name', 'city']
    ordering = ['sort_order', 'school_code']
    raw_id_fields = ['tenant_ref']

    # カスタムインポーター使用
    csv_importer_class = SchoolCSVImporter

    # CSV Import設定
    csv_import_fields = {
        '校舎コード': 'school_code',
        '校舎名': 'school_name',
        '校舎略称': 'school_short_name',
        '郵便番号': 'postal_code',
        '都道府県': 'prefecture',
        '市区町村': 'city',
        '住所1': 'address_line1',
        '住所2': 'address_line2',
        '電話番号': 'phone',
        'FAX番号': 'fax',
        'メールアドレス': 'email',
        '営業開始時間': 'opening_time',
        '営業終了時間': 'closing_time',
        '最寄り駅': 'nearest_station',
        '駐車場': 'has_parking',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['校舎コード', '校舎名']
    csv_unique_fields = ['school_code']
    csv_export_fields = [
        'school_code', 'school_name', 'school_name_short',
        'postal_code', 'prefecture', 'city', 'address1', 'address2',
        'phone', 'fax', 'email',
        'is_active', 'sort_order'
    ]
    csv_export_headers = {
        'school_code': '校舎コード',
        'school_name': '校舎名',
        'school_name_short': '校舎略称',
        'postal_code': '郵便番号',
        'prefecture': '都道府県',
        'city': '市区町村',
        'address1': '住所1',
        'address2': '住所2',
        'phone': '電話番号',
        'fax': 'FAX番号',
        'email': 'メールアドレス',
        'is_active': '有効',
        'sort_order': '並び順',
    }

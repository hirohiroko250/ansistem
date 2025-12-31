"""
Seminar Admin - 講習・検定管理
SeminarAdmin, CertificationAdmin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import Seminar, Certification


# =============================================================================
# T11: 講習マスタ
# =============================================================================
@admin.register(Seminar)
class SeminarAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'seminar_code', 'seminar_name', 'seminar_type', 'year',
        'base_price', 'is_active'
    ]
    list_filter = ['seminar_type', 'year', 'brand', 'is_active']
    search_fields = ['seminar_code', 'seminar_name']
    raw_id_fields = ['brand', 'grade']

    csv_import_fields = {
        '講習コード': 'seminar_code',
        '講習名': 'seminar_name',
        '講習種別': 'seminar_type',
        'ブランドコード': 'brand__brand_code',
        '学年コード': 'grade__grade_code',
        '年度': 'year',
        '開始日': 'start_date',
        '終了日': 'end_date',
        '価格': 'base_price',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['講習コード', '講習名', '年度']
    csv_unique_fields = ['seminar_code']
    csv_export_fields = [
        'seminar_code', 'seminar_name', 'seminar_type',
        'brand.brand_name', 'grade.grade_name',
        'year', 'start_date', 'end_date', 'base_price',
        'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'seminar_code': '講習コード',
        'seminar_name': '講習名',
        'seminar_type': '講習種別',
        'brand.brand_name': 'ブランド名',
        'grade.grade_name': '学年名',
        'year': '年度',
        'start_date': '開始日',
        'end_date': '終了日',
        'base_price': '価格',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }


# =============================================================================
# T12: 検定マスタ
# =============================================================================
@admin.register(Certification)
class CertificationAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'certification_code', 'certification_name', 'certification_type',
        'level', 'year', 'exam_fee', 'is_active'
    ]
    list_filter = ['certification_type', 'year', 'is_active']
    search_fields = ['certification_code', 'certification_name', 'level']
    raw_id_fields = ['brand']

    csv_import_fields = {
        '検定コード': 'certification_code',
        '検定名': 'certification_name',
        '検定種別': 'certification_type',
        '級・レベル': 'level',
        'ブランドコード': 'brand__brand_code',
        '年度': 'year',
        '試験日': 'exam_date',
        '検定料': 'exam_fee',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['検定コード', '検定名', '年度']
    csv_unique_fields = ['certification_code']
    csv_export_fields = [
        'certification_code', 'certification_name', 'certification_type',
        'level', 'brand.brand_name', 'year', 'exam_date', 'exam_fee',
        'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'certification_code': '検定コード',
        'certification_name': '検定名',
        'certification_type': '検定種別',
        'level': '級・レベル',
        'brand.brand_name': 'ブランド名',
        'year': '年度',
        'exam_date': '試験日',
        'exam_fee': '検定料',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }

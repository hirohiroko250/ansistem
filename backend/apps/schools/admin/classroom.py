"""
Classroom Admin - 教室・時間枠管理Admin
ClassroomAdmin, TimeSlotAdmin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import Classroom, TimeSlot
from .importer import ClassroomCSVImporter


@admin.register(Classroom)
class ClassroomAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """教室マスタAdmin（T11_ルーム情報対応）"""
    list_display = ['classroom_code', 'classroom_name', 'school', 'capacity', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active', 'school']
    search_fields = ['classroom_code', 'classroom_name']
    ordering = ['school', 'sort_order', 'classroom_code']
    raw_id_fields = ['tenant_ref']

    # カスタムインポーター使用
    csv_importer_class = ClassroomCSVImporter

    # CSV Import設定
    csv_import_fields = {
        '教室コード': 'classroom_code',
        '教室名': 'classroom_name',
        '校舎': 'school_name',  # 名前で検索してFKにマッピング
        '定員': 'capacity',
        'フロア': 'floor',
        '設備': 'equipment',
        '説明': 'description',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['教室コード', '教室名']
    csv_unique_fields = ['classroom_code']
    csv_export_fields = [
        'classroom_code', 'classroom_name', 'school.school_name',
        'capacity', 'floor', 'equipment', 'description', 'is_active', 'sort_order'
    ]
    csv_export_headers = {
        'classroom_code': '教室コード',
        'classroom_name': '教室名',
        'school.school_name': '校舎',
        'capacity': '定員',
        'floor': 'フロア',
        'equipment': '設備',
        'description': '説明',
        'is_active': '有効',
        'sort_order': '並び順',
    }


@admin.register(TimeSlot)
class TimeSlotAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """時間枠マスタAdmin"""
    list_display = ['slot_code', 'slot_name', 'start_time', 'end_time']
    ordering = ['sort_order', 'start_time']

    # CSV Import設定
    csv_import_fields = {
        '時間枠コード': 'slot_code',
        '時間枠名': 'slot_name',
        '開始時間': 'start_time',
        '終了時間': 'end_time',
        '時間（分）': 'duration_minutes',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['時間枠コード', '時間枠名', '開始時間', '終了時間']
    csv_unique_fields = ['slot_code']
    csv_export_fields = ['slot_code', 'slot_name', 'start_time', 'end_time', 'duration_minutes', 'sort_order', 'is_active']
    csv_export_headers = {
        'slot_code': '時間枠コード',
        'slot_name': '時間枠名',
        'start_time': '開始時間',
        'end_time': '終了時間',
        'duration_minutes': '時間（分）',
        'sort_order': '並び順',
        'is_active': '有効',
    }

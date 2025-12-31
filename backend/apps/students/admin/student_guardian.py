"""
StudentGuardian Admin - 生徒保護者関連Admin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import StudentGuardian


@admin.register(StudentGuardian)
class StudentGuardianAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['student', 'guardian', 'relationship', 'is_primary', 'is_emergency_contact']
    list_filter = ['relationship', 'is_primary', 'is_emergency_contact', 'is_billing_target']
    raw_id_fields = ['student', 'guardian']

    # CSV Import設定
    csv_import_fields = {
        '生徒番号': 'student__student_no',
        '保護者番号': 'guardian__guardian_no',
        '続柄': 'relationship',
        '主保護者': 'is_primary',
        '緊急連絡先': 'is_emergency_contact',
        '請求対象': 'is_billing_target',
    }
    csv_required_fields = ['生徒番号', '保護者番号']
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'guardian.guardian_no', 'guardian.last_name', 'guardian.first_name',
        'relationship', 'is_primary', 'is_emergency_contact', 'is_billing_target'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'guardian.guardian_no': '保護者番号',
        'guardian.last_name': '保護者姓',
        'guardian.first_name': '保護者名',
        'relationship': '続柄',
        'is_primary': '主保護者',
        'is_emergency_contact': '緊急連絡先',
        'is_billing_target': '請求対象',
    }

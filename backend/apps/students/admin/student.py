"""
Student Admin - 生徒管理Admin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import Student
from .importer import StudentCSVImporter


@admin.register(Student)
class StudentAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """生徒管理Admin"""

    # カスタムインポーター使用
    csv_importer_class = StudentCSVImporter
    list_display = ['student_no', 'old_id', 'last_name', 'first_name', 'grade', 'primary_school', 'status', 'enrollment_date', 'tenant_ref']
    list_filter = ['tenant_ref', 'status', 'grade', 'primary_school', 'primary_brand']
    search_fields = ['student_no', 'old_id', 'last_name', 'first_name', 'email']
    ordering = ['-created_at']
    raw_id_fields = ['grade', 'primary_school', 'primary_brand', 'user', 'tenant_ref']

    # CSV Import設定
    csv_import_fields = {
        '生徒番号': 'student_no',
        '旧システムID': 'old_id',
        '姓': 'last_name',
        '名': 'first_name',
        '姓（カナ）': 'last_name_kana',
        '名（カナ）': 'first_name_kana',
        '表示名': 'display_name',
        'メールアドレス': 'email',
        '電話番号': 'phone',
        'LINE ID': 'line_id',
        '生年月日': 'birth_date',
        '性別': 'gender',
        '在籍学校名': 'school_name',
        '学校種別': 'school_type',
        '主所属校舎': 'primary_school_name',  # 名前で検索してFKにマッピング
        '主所属ブランド': 'primary_brand_name',  # 名前で検索してFKにマッピング
        '学年': 'grade_name',  # 名前で検索してFKにマッピング
        '入塾日': 'enrollment_date',
        '退塾日': 'withdrawal_date',
        '退塾理由': 'withdrawal_reason',
        'ステータス': 'status',
        '備考': 'notes',
    }
    csv_required_fields = ['姓', '名']  # 生徒番号は自動発番されるため必須ではない
    csv_unique_fields = ['student_no']
    csv_export_fields = [
        'student_no', 'old_id', 'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
        'display_name', 'email', 'phone', 'line_id', 'birth_date', 'gender',
        'school_name', 'school_type', 'primary_school.school_name', 'primary_brand.brand_name',
        'grade.grade_name', 'enrollment_date', 'withdrawal_date', 'withdrawal_reason',
        'status', 'notes'
    ]
    csv_export_headers = {
        'student_no': '生徒番号',
        'old_id': '旧システムID',
        'last_name': '姓',
        'first_name': '名',
        'last_name_kana': '姓（カナ）',
        'first_name_kana': '名（カナ）',
        'display_name': '表示名',
        'email': 'メールアドレス',
        'phone': '電話番号',
        'line_id': 'LINE ID',
        'birth_date': '生年月日',
        'gender': '性別',
        'school_name': '在籍学校名',
        'school_type': '学校種別',
        'primary_school.school_name': '主所属校舎',
        'primary_brand.brand_name': '主所属ブランド',
        'grade.grade_name': '学年',
        'enrollment_date': '入塾日',
        'withdrawal_date': '退塾日',
        'withdrawal_reason': '退塾理由',
        'status': 'ステータス',
        'notes': '備考',
    }

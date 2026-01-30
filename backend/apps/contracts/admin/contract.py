"""
Contract Admin - 契約管理
ContractAdmin, StudentItemAdmin, StudentDiscountAdmin, SeminarEnrollmentAdmin, CertificationEnrollmentAdmin
"""
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from ..models import (
    Contract, StudentItem, StudentDiscount,
    SeminarEnrollment, CertificationEnrollment,
)


# =============================================================================
# 契約
# =============================================================================
class StudentItemInline(admin.TabularInline):
    model = StudentItem
    extra = 0
    raw_id_fields = ['product']
    readonly_fields = ['billing_month', 'product', 'quantity', 'unit_price', 'discount_amount', 'final_price']


@admin.register(Contract)
class ContractAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'contract_no', 'student', 'school', 'brand',
        'course', 'status', 'contract_date', 'monthly_total', 'tenant_ref'
    ]
    list_filter = ['tenant_ref', 'status', 'school', 'brand']
    search_fields = ['contract_no', 'student__last_name', 'student__first_name']
    raw_id_fields = ['student', 'guardian', 'school', 'brand', 'course', 'tenant_ref']
    inlines = [StudentItemInline]  # ContractHistoryInline added dynamically in __init__.py

    csv_import_fields = {
        '契約番号': 'contract_no',
        '生徒番号': 'student__student_no',
        '保護者番号': 'guardian__guardian_no',
        '教室コード': 'school__school_code',
        'ブランドコード': 'brand__brand_code',
        'コースコード': 'course__course_code',
        '契約日': 'contract_date',
        '開始日': 'start_date',
        '終了日': 'end_date',
        'ステータス': 'status',
        '月額合計': 'monthly_total',
        '備考': 'notes',
    }
    csv_required_fields = ['契約番号', '生徒番号', '教室コード', 'ブランドコード', '契約日', '開始日']
    csv_unique_fields = ['contract_no']
    csv_export_fields = [
        'contract_no', 'student.student_no', 'student.last_name', 'student.first_name',
        'guardian.guardian_no', 'school.school_name', 'brand.brand_name',
        'course.course_name', 'status', 'contract_date', 'start_date', 'end_date',
        'monthly_total', 'notes'
    ]
    csv_export_headers = {
        'contract_no': '契約番号',
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'guardian.guardian_no': '保護者番号',
        'school.school_name': '校舎名',
        'brand.brand_name': 'ブランド名',
        'course.course_name': 'コース名',
        'status': 'ステータス',
        'contract_date': '契約日',
        'start_date': '開始日',
        'end_date': '終了日',
        'monthly_total': '月額合計',
        'notes': '備考',
    }


# =============================================================================
# T04: 生徒商品（請求）
# =============================================================================
@admin.register(StudentItem)
class StudentItemAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'student', 'product', 'billing_month', 'quantity',
        'unit_price', 'discount_amount', 'final_price'
    ]
    list_filter = ['billing_month', 'product__item_type']
    search_fields = ['student__last_name', 'student__first_name', 'product__product_name']
    raw_id_fields = ['student', 'contract', 'product']

    csv_import_fields = {
        '旧システムID': 'old_id',
        '生徒番号': 'student__student_no',
        '契約番号': 'contract__contract_no',
        '商品コード': 'product__product_code',
        'ブランドコード': 'brand__brand_code',
        '校舎コード': 'school__school_code',
        'コースコード': 'course__course_code',
        '開始日': 'start_date',
        '曜日': 'day_of_week',
        '開始時間': 'start_time',
        '終了時間': 'end_time',
        '請求月': 'billing_month',
        '数量': 'quantity',
        '単価': 'unit_price',
        '割引額': 'discount_amount',
        '確定金額': 'final_price',
        '備考': 'notes',
    }
    csv_required_fields = ['生徒番号', '商品コード', '請求月', '単価', '確定金額']
    csv_unique_fields = []
    csv_export_fields = [
        'old_id',
        'student.student_no', 'student.last_name', 'student.first_name',
        'contract.contract_no',
        'product.product_code', 'product.product_name',
        'brand.brand_code', 'brand.brand_name',
        'school.school_code', 'school.school_name',
        'course.course_code', 'course.course_name',
        'start_date', 'day_of_week', 'start_time', 'end_time',
        'billing_month', 'quantity', 'unit_price', 'discount_amount', 'final_price', 'notes'
    ]
    csv_export_headers = {
        'old_id': '旧システムID',
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'contract.contract_no': '契約番号',
        'product.product_code': '商品コード',
        'product.product_name': '商品名',
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'start_date': '開始日',
        'day_of_week': '曜日',
        'start_time': '開始時間',
        'end_time': '終了時間',
        'billing_month': '請求月',
        'quantity': '数量',
        'unit_price': '単価',
        'discount_amount': '割引額',
        'final_price': '確定金額',
        'notes': '備考',
    }


# =============================================================================
# T06: 生徒割引
# =============================================================================
@admin.register(StudentDiscount)
class StudentDiscountAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'student', 'guardian', 'discount_name', 'amount', 'discount_unit',
        'start_date', 'end_date', 'is_recurring', 'is_active'
    ]
    list_filter = ['discount_unit', 'is_recurring', 'is_auto', 'is_active', 'end_condition']
    search_fields = [
        'discount_name', 'student__last_name', 'student__first_name',
        'guardian__last_name', 'guardian__first_name'
    ]
    raw_id_fields = ['student', 'guardian', 'contract', 'student_item', 'brand']
    date_hierarchy = 'start_date'

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'guardian.guardian_no', 'discount_name', 'amount', 'discount_unit',
        'start_date', 'end_date', 'is_recurring', 'is_auto', 'is_active',
        'end_condition', 'created_at',
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'guardian.guardian_no': '保護者番号',
        'discount_name': '割引名',
        'amount': '金額',
        'discount_unit': '割引単位',
        'start_date': '開始日',
        'end_date': '終了日',
        'is_recurring': '継続',
        'is_auto': '自動',
        'is_active': '有効',
        'end_condition': '終了条件',
        'created_at': '作成日時',
    }


# =============================================================================
# T55: 講習申込
# =============================================================================
@admin.register(SeminarEnrollment)
class SeminarEnrollmentAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'student', 'seminar', 'status', 'is_required',
        'unit_price', 'discount_amount', 'final_price', 'applied_at'
    ]
    list_filter = ['status', 'is_required', 'seminar__seminar_type', 'seminar__year']
    search_fields = ['student__last_name', 'student__first_name', 'seminar__seminar_name']
    raw_id_fields = ['student', 'seminar']

    csv_import_fields = {
        '生徒番号': 'student__student_no',
        '講習コード': 'seminar__seminar_code',
        'ステータス': 'status',
        '必須': 'is_required',
        '単価': 'unit_price',
        '割引額': 'discount_amount',
        '確定金額': 'final_price',
    }
    csv_required_fields = ['生徒番号', '講習コード']
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'seminar.seminar_code', 'seminar.seminar_name',
        'status', 'is_required', 'unit_price', 'discount_amount', 'final_price', 'applied_at'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'seminar.seminar_code': '講習コード',
        'seminar.seminar_name': '講習名',
        'status': 'ステータス',
        'is_required': '必須',
        'unit_price': '単価',
        'discount_amount': '割引額',
        'final_price': '確定金額',
        'applied_at': '申込日時',
    }


# =============================================================================
# T56: 検定申込
# =============================================================================
@admin.register(CertificationEnrollment)
class CertificationEnrollmentAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'student', 'certification', 'status',
        'exam_fee', 'final_price', 'score', 'applied_at'
    ]
    list_filter = ['status', 'certification__certification_type', 'certification__year']
    search_fields = ['student__last_name', 'student__first_name', 'certification__certification_name']
    raw_id_fields = ['student', 'certification']

    csv_import_fields = {
        '生徒番号': 'student__student_no',
        '検定コード': 'certification__certification_code',
        'ステータス': 'status',
        '検定料': 'exam_fee',
        '確定金額': 'final_price',
        '得点': 'score',
        '合否': 'result',
    }
    csv_required_fields = ['生徒番号', '検定コード']
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'certification.certification_code', 'certification.certification_name',
        'status', 'exam_fee', 'final_price', 'score', 'result', 'applied_at'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'certification.certification_code': '検定コード',
        'certification.certification_name': '検定名',
        'status': 'ステータス',
        'exam_fee': '検定料',
        'final_price': '確定金額',
        'score': '得点',
        'result': '合否',
        'applied_at': '申込日時',
    }

"""
HR Serializers
"""
from rest_framework import serializers
from .models import (
    Staff, StaffSchool, Shift, Attendance,
    SalaryMaster, PayrollItem, Payroll, PayrollDetail
)


class StaffListSerializer(serializers.ModelSerializer):
    """スタッフ一覧"""
    full_name = serializers.CharField(read_only=True)
    primary_school_name = serializers.CharField(source='primary_school.school_name', read_only=True)

    class Meta:
        model = Staff
        fields = [
            'id', 'staff_no', 'full_name', 'last_name', 'first_name',
            'staff_type', 'position', 'status',
            'primary_school', 'primary_school_name',
            'email', 'phone_mobile'
        ]


class StaffDetailSerializer(serializers.ModelSerializer):
    """スタッフ詳細"""
    full_name = serializers.CharField(read_only=True)
    primary_school_name = serializers.CharField(source='primary_school.school_name', read_only=True)
    teachable_subjects_data = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            'id', 'staff_no',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
            'full_name', 'display_name',
            'email', 'phone', 'phone_mobile',
            'postal_code', 'prefecture', 'city', 'address1', 'address2',
            'birth_date', 'gender', 'profile_image_url',
            'staff_type', 'position', 'hire_date', 'retirement_date', 'status',
            'primary_school', 'primary_school_name',
            'teachable_subjects', 'teachable_subjects_data',
            'bank_name', 'bank_branch', 'bank_account_type',
            'bank_account_number', 'bank_account_holder',
            'notes', 'custom_fields',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_teachable_subjects_data(self, obj):
        return [{
            'id': str(s.id),
            'subject_name': s.subject_name
        } for s in obj.teachable_subjects.all()]


class StaffCreateUpdateSerializer(serializers.ModelSerializer):
    """スタッフ作成・更新"""

    class Meta:
        model = Staff
        fields = [
            'staff_no',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana', 'display_name',
            'email', 'phone', 'phone_mobile',
            'postal_code', 'prefecture', 'city', 'address1', 'address2',
            'birth_date', 'gender',
            'staff_type', 'position', 'hire_date', 'status',
            'primary_school', 'teachable_subjects',
            'bank_name', 'bank_branch', 'bank_account_type',
            'bank_account_number', 'bank_account_holder',
            'notes', 'custom_fields'
        ]


class StaffSchoolSerializer(serializers.ModelSerializer):
    """スタッフ所属校舎"""
    school_name = serializers.CharField(source='school.school_name', read_only=True)

    class Meta:
        model = StaffSchool
        fields = ['id', 'staff', 'school', 'school_name', 'is_primary', 'start_date', 'end_date']
        read_only_fields = ['id']


class ShiftListSerializer(serializers.ModelSerializer):
    """シフト一覧"""
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)

    class Meta:
        model = Shift
        fields = [
            'id', 'staff', 'staff_name', 'school', 'school_name',
            'date', 'start_time', 'end_time', 'break_minutes', 'status'
        ]


class ShiftDetailSerializer(serializers.ModelSerializer):
    """シフト詳細"""
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)

    class Meta:
        model = Shift
        fields = [
            'id', 'staff', 'staff_name', 'school', 'school_name',
            'date', 'start_time', 'end_time', 'break_minutes',
            'status', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AttendanceSerializer(serializers.ModelSerializer):
    """勤怠記録"""
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id', 'staff', 'staff_name', 'school', 'school_name', 'shift',
            'date', 'attendance_type',
            'clock_in', 'clock_out', 'break_minutes',
            'work_minutes', 'overtime_minutes', 'late_minutes', 'early_leave_minutes',
            'lesson_count', 'notes',
            'is_approved', 'approved_by', 'approved_at'
        ]
        read_only_fields = ['id', 'work_minutes', 'overtime_minutes']


class SalaryMasterSerializer(serializers.ModelSerializer):
    """給与マスタ"""
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)

    class Meta:
        model = SalaryMaster
        fields = [
            'id', 'staff', 'staff_name', 'salary_type',
            'base_hourly_rate', 'base_lesson_rate', 'base_monthly_salary',
            'transportation_allowance', 'overtime_rate_multiplier',
            'valid_from', 'valid_until', 'notes'
        ]
        read_only_fields = ['id']


class PayrollItemSerializer(serializers.ModelSerializer):
    """給与項目"""

    class Meta:
        model = PayrollItem
        fields = [
            'id', 'item_code', 'item_name', 'item_type', 'calculation_type',
            'default_value', 'is_taxable', 'is_social_insurance_target',
            'sort_order', 'is_active'
        ]
        read_only_fields = ['id']


class PayrollDetailItemSerializer(serializers.ModelSerializer):
    """給与明細項目"""
    item_name = serializers.CharField(source='item.item_name', read_only=True)
    item_type = serializers.CharField(source='item.item_type', read_only=True)

    class Meta:
        model = PayrollDetail
        fields = ['id', 'item', 'item_name', 'item_type', 'amount', 'notes']
        read_only_fields = ['id']


class PayrollListSerializer(serializers.ModelSerializer):
    """給与明細一覧"""
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)

    class Meta:
        model = Payroll
        fields = [
            'id', 'staff', 'staff_name', 'year', 'month',
            'gross_salary', 'total_deductions', 'net_salary',
            'status', 'payment_date'
        ]


class PayrollDetailSerializer(serializers.ModelSerializer):
    """給与明細詳細"""
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    details = PayrollDetailItemSerializer(many=True, read_only=True)

    class Meta:
        model = Payroll
        fields = [
            'id', 'staff', 'staff_name', 'year', 'month', 'payment_date',
            'work_days', 'work_hours', 'overtime_hours', 'lesson_count',
            'gross_salary', 'total_deductions', 'net_salary',
            'status', 'calculated_at', 'approved_at', 'approved_by', 'paid_at',
            'notes', 'details',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

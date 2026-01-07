"""
Request Serializers - 休会・退会申請シリアライザ
"""
from rest_framework import serializers
from apps.students.models import SuspensionRequest, WithdrawalRequest
from apps.schools.models import Brand, School


class SuspensionRequestSerializer(serializers.ModelSerializer):
    """休会申請シリアライザ"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_no = serializers.CharField(source='student.student_no', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SuspensionRequest
        fields = [
            'id', 'student', 'student_name', 'student_no',
            'brand', 'brand_name', 'school', 'school_name',
            'suspend_from', 'suspend_until', 'return_day', 'keep_seat',
            'monthly_fee_during_suspension',
            'reason', 'reason_display', 'reason_detail',
            'status', 'status_display',
            'requested_at', 'requested_by', 'requested_by_name',
            'processed_at', 'processed_by', 'processed_by_name',
            'process_notes', 'resumed_at', 'resumed_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'student_name', 'student_no', 'school_name', 'brand_name',
            'requested_by', 'requested_by_name', 'requested_at',
            'processed_by', 'processed_by_name', 'processed_at',
            'process_notes', 'resumed_at', 'resumed_by',
            'status', 'created_at', 'updated_at'
        ]


class SuspensionRequestCreateSerializer(serializers.ModelSerializer):
    """休会申請作成用シリアライザ"""
    brand = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        required=False,
        allow_null=True
    )
    school = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = SuspensionRequest
        fields = [
            'student', 'brand', 'school',
            'suspend_from', 'suspend_until', 'return_day', 'keep_seat',
            'reason', 'reason_detail'
        ]

    def validate_student(self, value):
        """生徒が保護者に紐づいているか確認"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'guardian_profile') and request.user.guardian_profile:
            guardian = request.user.guardian_profile
            if value.guardian != guardian:
                raise serializers.ValidationError('この生徒に対する申請権限がありません')
        return value


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """退会申請シリアライザ"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_no = serializers.CharField(source='student.student_no', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'student', 'student_name', 'student_no',
            'brand', 'brand_name', 'school', 'school_name',
            'withdrawal_date', 'last_lesson_date',
            'reason', 'reason_display', 'reason_detail',
            'refund_amount', 'refund_calculated', 'remaining_tickets',
            'status', 'status_display',
            'requested_at', 'requested_by', 'requested_by_name',
            'processed_at', 'processed_by', 'processed_by_name',
            'process_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'student_name', 'student_no', 'school_name', 'brand_name',
            'requested_by', 'requested_by_name', 'requested_at',
            'processed_by', 'processed_by_name', 'processed_at',
            'process_notes', 'refund_amount', 'refund_calculated', 'remaining_tickets',
            'status', 'created_at', 'updated_at'
        ]


class WithdrawalRequestCreateSerializer(serializers.ModelSerializer):
    """退会申請作成用シリアライザ"""
    brand = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        required=False,
        allow_null=True
    )
    school = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = WithdrawalRequest
        fields = [
            'student', 'brand', 'school',
            'withdrawal_date', 'last_lesson_date',
            'reason', 'reason_detail'
        ]

    def validate_student(self, value):
        """生徒が保護者に紐づいているか確認"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'guardian_profile') and request.user.guardian_profile:
            guardian = request.user.guardian_profile
            if value.guardian != guardian:
                raise serializers.ValidationError('この生徒に対する申請権限がありません')
        return value

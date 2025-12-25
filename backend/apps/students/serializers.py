"""
Students Serializers
"""
from rest_framework import serializers
from .models import Student, Guardian, StudentSchool, StudentGuardian, SuspensionRequest, WithdrawalRequest, BankAccount, BankAccountChangeRequest
from apps.schools.models import Brand


class StudentListSerializer(serializers.ModelSerializer):
    """生徒一覧"""
    full_name = serializers.CharField(read_only=True)
    grade_name = serializers.SerializerMethodField()
    primary_school_name = serializers.CharField(source='primary_school.school_name', read_only=True)
    primary_brand_name = serializers.CharField(source='primary_brand.brand_name', read_only=True)
    guardian_id = serializers.UUIDField(source='guardian.id', read_only=True)
    guardian_no = serializers.CharField(source='guardian.guardian_no', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    guardian_phone = serializers.SerializerMethodField()
    brand_ids = serializers.PrimaryKeyRelatedField(source='brands', many=True, read_only=True)
    brand_names = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'student_no', 'full_name', 'last_name', 'first_name',
            'last_name_kana', 'first_name_kana',
            'birth_date', 'gender', 'school_name',
            'grade', 'grade_name', 'grade_text',
            'primary_school', 'primary_school_name', 'primary_brand', 'primary_brand_name',
            'brands', 'brand_ids', 'brand_names',
            'status', 'registered_date', 'trial_date', 'enrollment_date', 'suspended_date', 'withdrawal_date',
            'email', 'phone', 'notes',
            'guardian', 'guardian_id', 'guardian_no', 'guardian_name', 'guardian_phone'
        ]

    def get_brand_names(self, obj):
        """所属ブランド名のリストを返す"""
        return [brand.brand_name for brand in obj.brands.all()]

    def get_grade_name(self, obj):
        """grade_textがあればそれを、なければgrade.grade_nameを返す"""
        if obj.grade_text:
            return obj.grade_text
        if obj.grade:
            return obj.grade.grade_name
        return None

    def get_guardian_phone(self, obj):
        """保護者の電話番号を返す（携帯優先）"""
        if obj.guardian:
            return obj.guardian.phone_mobile or obj.guardian.phone
        return None


class StudentDetailSerializer(serializers.ModelSerializer):
    """生徒詳細"""
    full_name = serializers.CharField(read_only=True)
    full_name_kana = serializers.CharField(read_only=True)
    grade_name = serializers.SerializerMethodField()
    primary_school_name = serializers.SerializerMethodField()
    primary_brand_name = serializers.SerializerMethodField()
    brand_ids = serializers.PrimaryKeyRelatedField(source='brands', many=True, read_only=True)
    brand_names = serializers.SerializerMethodField()
    # 保護者情報
    guardian_id = serializers.UUIDField(source='guardian.id', read_only=True)
    guardian_no = serializers.CharField(source='guardian.guardian_no', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    guardian_phone = serializers.SerializerMethodField()
    guardian = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'student_no',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
            'full_name', 'full_name_kana', 'display_name',
            'email', 'phone', 'line_id',
            'birth_date', 'gender', 'profile_image_url',
            'school_name', 'school_type',
            'grade', 'grade_name', 'grade_text', 'grade_updated_at',
            'primary_school', 'primary_school_name',
            'primary_brand', 'primary_brand_name',
            'brands', 'brand_ids', 'brand_names',
            'status', 'registered_date', 'trial_date', 'enrollment_date', 'suspended_date', 'withdrawal_date', 'withdrawal_reason',
            'notes', 'tags', 'custom_fields',
            'guardian', 'guardian_id', 'guardian_no', 'guardian_name', 'guardian_phone',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_grade_name(self, obj):
        """grade_textがあればそれを、なければgrade.grade_nameを返す"""
        if obj.grade_text:
            return obj.grade_text
        if obj.grade:
            return obj.grade.grade_name
        return None

    def get_primary_school_name(self, obj):
        """主所属校舎名を返す（フォールバック: StudentSchool → Contract）"""
        # 1. primary_schoolがあればそれを返す
        if obj.primary_school:
            return obj.primary_school.school_name

        # 2. StudentSchoolから取得
        active_school = obj.school_enrollments.filter(
            enrollment_status='active',
            deleted_at__isnull=True
        ).select_related('school').first()
        if active_school and active_school.school:
            return active_school.school.school_name

        # 3. Contractから取得
        from apps.contracts.models import Contract
        active_contract = Contract.objects.filter(
            student=obj,
            status='active',
            deleted_at__isnull=True
        ).select_related('school').first()
        if active_contract and active_contract.school:
            return active_contract.school.school_name

        return None

    def get_primary_brand_name(self, obj):
        """主所属ブランド名を返す（フォールバック: brands → StudentSchool → Contract）"""
        # 1. primary_brandがあればそれを返す
        if obj.primary_brand:
            return obj.primary_brand.brand_name

        # 2. brandsから最初の1つを取得
        first_brand = obj.brands.first()
        if first_brand:
            return first_brand.brand_name

        # 3. StudentSchoolから取得
        active_school = obj.school_enrollments.filter(
            enrollment_status='active',
            deleted_at__isnull=True
        ).select_related('brand').first()
        if active_school and active_school.brand:
            return active_school.brand.brand_name

        # 4. Contractから取得
        from apps.contracts.models import Contract
        active_contract = Contract.objects.filter(
            student=obj,
            status='active',
            deleted_at__isnull=True
        ).select_related('brand').first()
        if active_contract and active_contract.brand:
            return active_contract.brand.brand_name

        return None

    def get_brand_names(self, obj):
        """所属ブランド名のリストを返す"""
        return [brand.brand_name for brand in obj.brands.all()]

    def get_guardian_phone(self, obj):
        """保護者の電話番号を返す（携帯優先）"""
        if obj.guardian:
            return obj.guardian.phone_mobile or obj.guardian.phone
        return None

    def get_guardian(self, obj):
        """保護者情報をシリアライズ"""
        if obj.guardian:
            return {
                'id': str(obj.guardian.id),
                'guardian_no': obj.guardian.guardian_no,
                'last_name': obj.guardian.last_name,
                'first_name': obj.guardian.first_name,
                'last_name_kana': obj.guardian.last_name_kana,
                'first_name_kana': obj.guardian.first_name_kana,
                'full_name': obj.guardian.full_name,
                'email': obj.guardian.email,
                'phone': obj.guardian.phone,
                'phone_mobile': obj.guardian.phone_mobile,
                'postal_code': obj.guardian.postal_code,
                'prefecture': obj.guardian.prefecture,
                'city': obj.guardian.city,
                'address1': obj.guardian.address1,
                'address2': obj.guardian.address2,
            }
        return None


class StudentCreateSerializer(serializers.ModelSerializer):
    """生徒作成"""
    student_no = serializers.CharField(required=False, allow_blank=True)
    full_name = serializers.CharField(read_only=True)
    grade_name = serializers.SerializerMethodField()
    # フロントエンドから送られる 'grade' を grade_text にマッピング
    grade = serializers.CharField(source='grade_text', required=False, allow_blank=True)
    guardian_id = serializers.UUIDField(source='guardian.id', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'student_no',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana', 'display_name',
            'full_name',
            'email', 'phone', 'line_id',
            'birth_date', 'gender',
            'school_name', 'school_type', 'grade', 'grade_name',
            'status', 'registered_date', 'trial_date', 'enrollment_date', 'suspended_date', 'withdrawal_date',
            'notes', 'tags', 'custom_fields',
            'guardian', 'guardian_id', 'guardian_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'full_name', 'grade_name', 'guardian', 'guardian_id', 'guardian_name', 'created_at', 'updated_at']

    def get_grade_name(self, obj):
        """grade_textを返す"""
        return obj.grade_text if obj.grade_text else None


class StudentUpdateSerializer(serializers.ModelSerializer):
    """生徒更新"""
    brands = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Brand.objects.all(),
        required=False
    )

    class Meta:
        model = Student
        fields = [
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana', 'display_name',
            'email', 'phone', 'line_id',
            'birth_date', 'gender', 'profile_image_url',
            'school_name', 'school_type', 'grade',
            'primary_school', 'primary_brand', 'brands',
            'status', 'registered_date', 'trial_date', 'enrollment_date', 'suspended_date', 'withdrawal_date', 'withdrawal_reason',
            'notes', 'tags', 'custom_fields'
        ]


class GuardianListSerializer(serializers.ModelSerializer):
    """保護者一覧"""
    full_name = serializers.CharField(read_only=True)
    student_count = serializers.IntegerField(read_only=True)
    student_names = serializers.SerializerMethodField()
    has_account = serializers.SerializerMethodField()

    class Meta:
        model = Guardian
        fields = [
            'id', 'guardian_no', 'full_name', 'last_name', 'first_name',
            'last_name_kana', 'first_name_kana',
            'email', 'phone', 'phone_mobile', 'student_count', 'student_names',
            'has_account'
        ]

    def get_student_names(self, obj):
        """保護者に紐づく生徒名のリストを返す"""
        children = obj.children.filter(deleted_at__isnull=True)[:5]  # 最大5人
        return [f"{s.last_name}{s.first_name}" for s in children]

    def get_has_account(self, obj):
        """保護者にログインアカウントが紐付いているか"""
        return obj.user_id is not None


class GuardianDetailSerializer(serializers.ModelSerializer):
    """保護者詳細"""
    full_name = serializers.CharField(read_only=True)
    has_account = serializers.SerializerMethodField()
    is_employee = serializers.BooleanField(read_only=True)
    employee_discount_info = serializers.DictField(read_only=True)

    class Meta:
        model = Guardian
        fields = [
            'id', 'guardian_no',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana', 'full_name',
            'email', 'phone', 'phone_mobile', 'line_id',
            'postal_code', 'prefecture', 'city', 'address1', 'address2',
            'workplace', 'workplace_phone',
            # 支払い情報
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_number', 'account_holder', 'account_holder_kana',
            'withdrawal_day', 'payment_registered', 'payment_registered_at',
            'notes',
            'has_account',
            # 社員情報
            'is_employee', 'employee_discount_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'has_account', 'is_employee', 'employee_discount_info']

    def get_has_account(self, obj):
        """保護者にログインアカウントが紐付いているか"""
        return obj.user_id is not None


class GuardianPaymentSerializer(serializers.ModelSerializer):
    """保護者支払い情報"""
    full_name = serializers.CharField(read_only=True)
    account_number_masked = serializers.SerializerMethodField()

    class Meta:
        model = Guardian
        fields = [
            'id', 'guardian_no', 'full_name',
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_number', 'account_number_masked',
            'account_holder', 'account_holder_kana',
            'withdrawal_day', 'payment_registered', 'payment_registered_at'
        ]
        read_only_fields = ['id', 'guardian_no', 'full_name', 'account_number_masked']

    def get_account_number_masked(self, obj):
        """口座番号をマスク（下4桁のみ表示）"""
        if obj.account_number and len(obj.account_number) >= 4:
            return '•' * (len(obj.account_number) - 4) + obj.account_number[-4:]
        return obj.account_number or ''


class GuardianPaymentUpdateSerializer(serializers.ModelSerializer):
    """保護者支払い情報更新"""

    class Meta:
        model = Guardian
        fields = [
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_number', 'account_holder', 'account_holder_kana',
            'withdrawal_day'
        ]

    def update(self, instance, validated_data):
        from django.utils import timezone
        # 支払い情報を更新
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # 登録フラグと日時を設定
        instance.payment_registered = True
        instance.payment_registered_at = timezone.now()
        instance.save()
        return instance


class GuardianCreateUpdateSerializer(serializers.ModelSerializer):
    """保護者作成・更新"""

    class Meta:
        model = Guardian
        fields = [
            'guardian_no',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
            'email', 'phone', 'phone_mobile', 'line_id',
            'postal_code', 'prefecture', 'city', 'address1', 'address2',
            'workplace', 'workplace_phone',
            'notes'
        ]


class StudentSchoolSerializer(serializers.ModelSerializer):
    """生徒所属"""
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    class_schedule_name = serializers.CharField(source='class_schedule.class_name', read_only=True)
    day_of_week_display = serializers.SerializerMethodField()

    class Meta:
        model = StudentSchool
        fields = [
            'id', 'student', 'school', 'school_name', 'brand', 'brand_name',
            'enrollment_status', 'start_date', 'end_date', 'is_primary', 'notes',
            'class_schedule', 'class_schedule_name', 'day_of_week', 'day_of_week_display',
            'start_time', 'end_time'
        ]
        read_only_fields = ['id']

    def get_day_of_week_display(self, obj):
        days = {1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'}
        return days.get(obj.day_of_week, '')


class StudentGuardianSerializer(serializers.ModelSerializer):
    """生徒保護者関連"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = StudentGuardian
        fields = [
            'id', 'student', 'student_name', 'guardian', 'guardian_name',
            'relationship', 'is_primary', 'is_emergency_contact',
            'is_billing_target', 'contact_priority', 'notes'
        ]
        read_only_fields = ['id']


class StudentWithGuardiansSerializer(serializers.ModelSerializer):
    """生徒（保護者情報付き）"""
    full_name = serializers.CharField(read_only=True)
    guardians = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'student_no', 'full_name', 'last_name', 'first_name',
            'email', 'phone', 'status', 'guardians'
        ]

    def get_guardians(self, obj):
        relations = obj.guardian_relations.select_related('guardian').all()
        return [{
            'id': str(r.guardian.id),
            'name': r.guardian.full_name,
            'relationship': r.relationship,
            'is_primary': r.is_primary,
            'phone': r.guardian.phone or r.guardian.phone_mobile,
            'email': r.guardian.email,
        } for r in relations]


# =====================================
# 休会・退会申請用シリアライザ
# =====================================

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
            'suspend_from', 'suspend_until', 'keep_seat',
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

    class Meta:
        model = SuspensionRequest
        fields = [
            'student', 'brand', 'school',
            'suspend_from', 'suspend_until', 'keep_seat',
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


# =====================================
# 銀行口座関連シリアライザ
# =====================================

class BankAccountSerializer(serializers.ModelSerializer):
    """銀行口座シリアライザ"""
    guardian_name = serializers.SerializerMethodField()
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            'id', 'guardian', 'guardian_name',
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_type_display',
            'account_number', 'account_holder', 'account_holder_kana',
            'is_primary', 'is_active', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'guardian_name', 'created_at', 'updated_at']

    def get_guardian_name(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name} {obj.guardian.first_name}"
        return ""


class BankAccountChangeRequestSerializer(serializers.ModelSerializer):
    """銀行口座変更申請シリアライザ"""
    guardian_name = serializers.SerializerMethodField()
    guardian_no = serializers.CharField(source='guardian.guardian_no', read_only=True)
    guardian_email = serializers.CharField(source='guardian.email', read_only=True)
    guardian_phone = serializers.SerializerMethodField()
    guardian_address = serializers.SerializerMethodField()
    guardian_name_kana = serializers.SerializerMethodField()
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    processed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BankAccountChangeRequest
        fields = [
            'id', 'guardian', 'guardian_name', 'guardian_no',
            'guardian_email', 'guardian_phone', 'guardian_address', 'guardian_name_kana',
            'existing_account',
            'request_type', 'request_type_display',
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_type_display',
            'account_number', 'account_holder', 'account_holder_kana',
            'is_primary',
            'status', 'status_display',
            'requested_at', 'requested_by', 'requested_by_name', 'request_notes',
            'processed_at', 'processed_by', 'processed_by_name', 'process_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'guardian_name', 'guardian_no',
            'guardian_email', 'guardian_phone', 'guardian_address', 'guardian_name_kana',
            'request_type_display', 'status_display', 'account_type_display',
            'requested_at', 'requested_by', 'requested_by_name',
            'processed_at', 'processed_by', 'processed_by_name', 'process_notes',
            'status', 'created_at', 'updated_at'
        ]

    def get_guardian_name(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name} {obj.guardian.first_name}"
        return ""

    def get_guardian_name_kana(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name_kana} {obj.guardian.first_name_kana}".strip()
        return ""

    def get_guardian_phone(self, obj):
        if obj.guardian:
            return obj.guardian.phone_mobile or obj.guardian.phone or ""
        return ""

    def get_guardian_address(self, obj):
        if obj.guardian:
            parts = [
                obj.guardian.postal_code,
                obj.guardian.prefecture,
                obj.guardian.city,
                obj.guardian.address1,
                obj.guardian.address2,
            ]
            return " ".join(p for p in parts if p)
        return ""

    def get_requested_by_name(self, obj):
        if obj.requested_by:
            return f"{obj.requested_by.first_name} {obj.requested_by.last_name}".strip() or obj.requested_by.email
        return ""

    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return f"{obj.processed_by.first_name} {obj.processed_by.last_name}".strip() or obj.processed_by.email
        return ""


class BankAccountChangeRequestCreateSerializer(serializers.ModelSerializer):
    """銀行口座変更申請作成用シリアライザ"""

    class Meta:
        model = BankAccountChangeRequest
        fields = [
            'existing_account', 'request_type',
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_number',
            'account_holder', 'account_holder_kana',
            'is_primary', 'request_notes'
        ]

    def validate(self, data):
        request_type = data.get('request_type', 'new')

        # 新規・変更の場合は銀行情報が必須
        if request_type in ('new', 'update'):
            required_fields = ['bank_name', 'branch_name', 'account_number', 'account_holder', 'account_holder_kana']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError({field: 'この項目は必須です。'})

        # 変更・削除の場合はexisting_accountが必須
        if request_type in ('update', 'delete'):
            if not data.get('existing_account'):
                raise serializers.ValidationError({'existing_account': '変更・削除には既存口座の指定が必須です。'})

        return data

"""
Students Serializers
"""
from rest_framework import serializers
from .models import Student, Guardian, StudentSchool, StudentGuardian
from apps.schools.models import Brand


class StudentListSerializer(serializers.ModelSerializer):
    """生徒一覧"""
    full_name = serializers.CharField(read_only=True)
    grade_name = serializers.SerializerMethodField()
    primary_school_name = serializers.CharField(source='primary_school.school_name', read_only=True)
    primary_brand_name = serializers.CharField(source='primary_brand.brand_name', read_only=True)
    guardian_id = serializers.UUIDField(source='guardian.id', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    brand_ids = serializers.PrimaryKeyRelatedField(source='brands', many=True, read_only=True)
    brand_names = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'student_no', 'full_name', 'last_name', 'first_name',
            'birth_date', 'gender', 'school_name',
            'grade', 'grade_name', 'grade_text',
            'primary_school', 'primary_school_name', 'primary_brand', 'primary_brand_name',
            'brands', 'brand_ids', 'brand_names',
            'status', 'registered_date', 'trial_date', 'enrollment_date', 'suspended_date', 'withdrawal_date',
            'email', 'phone',
            'guardian', 'guardian_id', 'guardian_name'
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


class StudentDetailSerializer(serializers.ModelSerializer):
    """生徒詳細"""
    full_name = serializers.CharField(read_only=True)
    full_name_kana = serializers.CharField(read_only=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True)
    primary_school_name = serializers.CharField(source='primary_school.school_name', read_only=True)
    primary_brand_name = serializers.CharField(source='primary_brand.brand_name', read_only=True)
    brand_ids = serializers.PrimaryKeyRelatedField(source='brands', many=True, read_only=True)
    brand_names = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'student_no',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
            'full_name', 'full_name_kana', 'display_name',
            'email', 'phone', 'line_id',
            'birth_date', 'gender', 'profile_image_url',
            'school_name', 'school_type',
            'grade', 'grade_name', 'grade_updated_at',
            'primary_school', 'primary_school_name',
            'primary_brand', 'primary_brand_name',
            'brands', 'brand_ids', 'brand_names',
            'status', 'registered_date', 'trial_date', 'enrollment_date', 'suspended_date', 'withdrawal_date', 'withdrawal_reason',
            'notes', 'tags', 'custom_fields',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_brand_names(self, obj):
        """所属ブランド名のリストを返す"""
        return [brand.brand_name for brand in obj.brands.all()]


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

    class Meta:
        model = Guardian
        fields = [
            'id', 'guardian_no', 'full_name', 'last_name', 'first_name',
            'email', 'phone', 'phone_mobile', 'student_count'
        ]


class GuardianDetailSerializer(serializers.ModelSerializer):
    """保護者詳細"""
    full_name = serializers.CharField(read_only=True)

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
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


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

    class Meta:
        model = StudentSchool
        fields = [
            'id', 'student', 'school', 'school_name', 'brand', 'brand_name',
            'enrollment_status', 'start_date', 'end_date', 'is_primary', 'notes'
        ]
        read_only_fields = ['id']


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

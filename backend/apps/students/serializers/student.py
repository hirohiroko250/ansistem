"""
Student Serializers - 生徒シリアライザ
"""
from rest_framework import serializers
from apps.students.models import Student
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
        if obj.grade_text:
            return obj.grade_text
        if obj.grade:
            return obj.grade.grade_name
        return None

    def get_primary_school_name(self, obj):
        """主所属校舎名を返す（フォールバック: StudentSchool → Contract）"""
        if obj.primary_school:
            return obj.primary_school.school_name

        active_school = obj.school_enrollments.filter(
            enrollment_status='active',
            deleted_at__isnull=True
        ).select_related('school').first()
        if active_school and active_school.school:
            return active_school.school.school_name

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
        """主所属ブランド名を返す"""
        if obj.primary_brand:
            return obj.primary_brand.brand_name

        first_brand = obj.brands.first()
        if first_brand:
            return first_brand.brand_name

        active_school = obj.school_enrollments.filter(
            enrollment_status='active',
            deleted_at__isnull=True
        ).select_related('brand').first()
        if active_school and active_school.brand:
            return active_school.brand.brand_name

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
        return [brand.brand_name for brand in obj.brands.all()]

    def get_guardian_phone(self, obj):
        if obj.guardian:
            return obj.guardian.phone_mobile or obj.guardian.phone
        return None

    def get_guardian(self, obj):
        """保護者情報をシリアライズ（FS割の紹介者情報を含む）"""
        if not obj.guardian:
            return None

        guardian = obj.guardian
        fs_discounts = []
        try:
            from apps.students.models import FSDiscount
            for fs in FSDiscount.objects.filter(
                guardian=guardian,
                status='active'
            ).select_related('friendship__requester', 'friendship__target'):
                friendship = fs.friendship
                if friendship:
                    if friendship.requester_id == guardian.id:
                        partner = friendship.target
                        role = 'referrer'
                        role_display = '紹介者'
                    else:
                        partner = friendship.requester
                        role = 'referred'
                        role_display = '被紹介者'

                    fs_discounts.append({
                        'id': str(fs.id),
                        'role': role,
                        'role_display': role_display,
                        'partner_name': partner.full_name if partner else None,
                        'partner_id': str(partner.id) if partner else None,
                        'discount_type': fs.discount_type,
                        'discount_type_display': fs.get_discount_type_display(),
                        'discount_value': float(fs.discount_value),
                        'valid_from': str(fs.valid_from) if fs.valid_from else None,
                        'valid_until': str(fs.valid_until) if fs.valid_until else None,
                    })
        except Exception:
            pass

        return {
            'id': str(guardian.id),
            'guardian_no': guardian.guardian_no,
            'last_name': guardian.last_name,
            'first_name': guardian.first_name,
            'last_name_kana': guardian.last_name_kana,
            'first_name_kana': guardian.first_name_kana,
            'full_name': guardian.full_name,
            'email': guardian.email,
            'phone': guardian.phone,
            'phone_mobile': guardian.phone_mobile,
            'postal_code': guardian.postal_code,
            'prefecture': guardian.prefecture,
            'city': guardian.city,
            'address1': guardian.address1,
            'address2': guardian.address2,
            'fs_discounts': fs_discounts,
        }


class StudentCreateSerializer(serializers.ModelSerializer):
    """生徒作成"""
    student_no = serializers.CharField(required=False, allow_blank=True)
    full_name = serializers.CharField(read_only=True)
    grade_name = serializers.SerializerMethodField()
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

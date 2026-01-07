"""
Tenants Serializers
"""
from rest_framework import serializers
from .models import Tenant, Position, FeatureMaster, PositionPermission, Employee, EmployeeGroup


class TenantSerializer(serializers.ModelSerializer):
    """テナント一覧"""

    class Meta:
        model = Tenant
        fields = [
            'id', 'tenant_code', 'tenant_name', 'plan_type',
            'is_active', 'created_at'
        ]


class TenantDetailSerializer(serializers.ModelSerializer):
    """テナント詳細"""

    class Meta:
        model = Tenant
        fields = [
            'id', 'tenant_code', 'tenant_name', 'plan_type',
            'contact_email', 'contact_phone',
            'settings', 'features',
            'max_users', 'max_schools',
            'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# =============================================================================
# 役職・権限関連
# =============================================================================

class PositionSerializer(serializers.ModelSerializer):
    """役職シリアライザ"""

    class Meta:
        model = Position
        fields = [
            'id', 'position_code', 'position_name', 'rank',
            'school_restriction', 'brand_restriction',
            'bulk_email_restriction', 'email_approval_required',
            'is_accounting', 'is_active',
        ]


class FeatureMasterSerializer(serializers.ModelSerializer):
    """機能マスタシリアライザ"""

    class Meta:
        model = FeatureMaster
        fields = [
            'id', 'feature_code', 'feature_name', 'parent_code',
            'category', 'description', 'display_order', 'is_active',
        ]


class PositionPermissionSerializer(serializers.ModelSerializer):
    """役職権限シリアライザ"""
    position_name = serializers.CharField(source='position.position_name', read_only=True)
    feature_code = serializers.CharField(source='feature.feature_code', read_only=True)
    feature_name = serializers.CharField(source='feature.feature_name', read_only=True)

    class Meta:
        model = PositionPermission
        fields = [
            'id', 'position', 'position_name',
            'feature', 'feature_code', 'feature_name',
            'has_permission',
        ]


class PositionPermissionMatrixSerializer(serializers.Serializer):
    """権限マトリックス更新用シリアライザ"""
    position_id = serializers.UUIDField()
    feature_id = serializers.UUIDField()
    has_permission = serializers.BooleanField()


class BulkPermissionUpdateSerializer(serializers.Serializer):
    """一括権限更新用シリアライザ"""
    permissions = PositionPermissionMatrixSerializer(many=True)


# =============================================================================
# 社員関連
# =============================================================================

class EmployeeListSerializer(serializers.ModelSerializer):
    """社員一覧シリアライザ（ドロップダウン用）"""
    full_name = serializers.SerializerMethodField()
    position_name = serializers.CharField(source='position.position_name', read_only=True, allow_null=True)
    schools_list = serializers.SerializerMethodField()
    brands_list = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_no', 'full_name', 'last_name', 'first_name',
            'email', 'phone', 'department', 'position', 'position_name',
            'profile_image_url', 'schools_list', 'brands_list', 'is_active',
        ]

    def get_full_name(self, obj):
        return f"{obj.last_name} {obj.first_name}"

    def get_schools_list(self, obj):
        return [{'id': str(s.id), 'name': s.school_name} for s in obj.schools.all()]

    def get_brands_list(self, obj):
        return [{'id': str(b.id), 'name': b.brand_name} for b in obj.brands.all()]


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """社員詳細シリアライザ"""
    full_name = serializers.SerializerMethodField()
    position_name = serializers.CharField(source='position.position_name', read_only=True, allow_null=True)
    schools_list = serializers.SerializerMethodField()
    brands_list = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_no', 'full_name', 'last_name', 'first_name',
            'email', 'phone', 'department', 'position', 'position_name', 'position_text',
            'profile_image_url', 'schools_list', 'brands_list',
            'hire_date', 'termination_date',
            'postal_code', 'prefecture', 'city', 'address', 'nationality',
            'discount_flag', 'discount_amount', 'discount_unit',
            'discount_category_name', 'discount_category_code',
            'ozaworks_registered', 'is_active',
        ]

    def get_full_name(self, obj):
        return f"{obj.last_name} {obj.first_name}"

    def get_schools_list(self, obj):
        return [{'id': str(s.id), 'name': s.school_name} for s in obj.schools.all()]

    def get_brands_list(self, obj):
        return [{'id': str(b.id), 'name': b.brand_name} for b in obj.brands.all()]


# =============================================================================
# 社員グループ関連
# =============================================================================

class EmployeeGroupListSerializer(serializers.ModelSerializer):
    """社員グループ一覧シリアライザ"""
    member_count = serializers.IntegerField(read_only=True)
    members = EmployeeListSerializer(many=True, read_only=True)

    class Meta:
        model = EmployeeGroup
        fields = [
            'id', 'name', 'description', 'member_count', 'members',
            'is_active', 'created_at', 'updated_at',
        ]


class EmployeeGroupDetailSerializer(serializers.ModelSerializer):
    """社員グループ詳細シリアライザ"""
    member_count = serializers.IntegerField(read_only=True)
    members = EmployeeListSerializer(many=True, read_only=True)

    class Meta:
        model = EmployeeGroup
        fields = [
            'id', 'name', 'description', 'member_count', 'members',
            'is_active', 'created_at', 'updated_at',
        ]


class EmployeeGroupCreateUpdateSerializer(serializers.ModelSerializer):
    """社員グループ作成・更新シリアライザ"""
    member_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = EmployeeGroup
        fields = ['id', 'name', 'description', 'member_ids', 'is_active']
        read_only_fields = ['id']

    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids', [])
        group = EmployeeGroup.objects.create(**validated_data)
        if member_ids:
            employees = Employee.objects.filter(id__in=member_ids)
            group.members.set(employees)
        return group

    def update(self, instance, validated_data):
        member_ids = validated_data.pop('member_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if member_ids is not None:
            employees = Employee.objects.filter(id__in=member_ids)
            instance.members.set(employees)
        return instance

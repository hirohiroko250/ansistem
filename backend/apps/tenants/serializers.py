"""
Tenants Serializers
"""
from rest_framework import serializers
from .models import Tenant, Position, FeatureMaster, PositionPermission


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
            'address', 'logo_url',
            'settings', 'features',
            'max_users', 'max_students', 'max_schools',
            'contract_start_date', 'contract_end_date',
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

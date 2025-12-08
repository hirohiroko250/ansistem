"""
Tenants Serializers
"""
from rest_framework import serializers
from .models import Tenant


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

"""
Certification Serializers - 検定シリアライザ
CertificationListSerializer, CertificationDetailSerializer
"""
from rest_framework import serializers
from ..models import Certification


class CertificationListSerializer(serializers.ModelSerializer):
    """検定一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)

    class Meta:
        model = Certification
        fields = [
            'id', 'certification_code', 'certification_name',
            'certification_type', 'level',
            'brand', 'brand_name', 'year', 'exam_fee', 'is_active'
        ]


class CertificationDetailSerializer(serializers.ModelSerializer):
    """検定詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)

    class Meta:
        model = Certification
        fields = [
            'id', 'certification_code', 'certification_name',
            'certification_type', 'level',
            'brand', 'brand_name', 'year', 'exam_date', 'exam_fee',
            'description', 'sort_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

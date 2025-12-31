"""
Seminar Serializers - 講習シリアライザ
SeminarListSerializer, SeminarDetailSerializer
"""
from rest_framework import serializers
from ..models import Seminar


class SeminarListSerializer(serializers.ModelSerializer):
    """講習一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)

    class Meta:
        model = Seminar
        fields = [
            'id', 'seminar_code', 'seminar_name', 'seminar_type',
            'brand', 'brand_name', 'year', 'base_price', 'is_active'
        ]


class SeminarDetailSerializer(serializers.ModelSerializer):
    """講習詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True)

    class Meta:
        model = Seminar
        fields = [
            'id', 'seminar_code', 'seminar_name', 'seminar_type',
            'brand', 'brand_name', 'grade', 'grade_name',
            'year', 'start_date', 'end_date', 'base_price',
            'description', 'sort_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

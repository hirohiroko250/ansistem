"""
Discount Serializers - 割引シリアライザ
DiscountListSerializer, DiscountDetailSerializer
"""
from rest_framework import serializers
from ..models import Discount


class DiscountListSerializer(serializers.ModelSerializer):
    """割引一覧"""

    class Meta:
        model = Discount
        fields = [
            'id', 'discount_code', 'discount_name', 'discount_type',
            'calculation_type', 'value', 'is_active'
        ]


class DiscountDetailSerializer(serializers.ModelSerializer):
    """割引詳細"""

    class Meta:
        model = Discount
        fields = [
            'id', 'discount_code', 'discount_name', 'discount_type',
            'calculation_type', 'value',
            'valid_from', 'valid_until', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

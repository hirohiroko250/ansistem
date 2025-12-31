"""
Product Serializers - 商品シリアライザ
ProductListSerializer, ProductDetailSerializer
"""
from rest_framework import serializers
from ..models import Product


class ProductListSerializer(serializers.ModelSerializer):
    """商品一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'product_name', 'item_type',
            'brand', 'brand_name', 'school', 'school_name',
            'grade', 'grade_name',
            'base_price', 'is_one_time', 'is_active'
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """商品詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'product_name', 'product_name_short',
            'item_type',
            'brand', 'brand_name', 'school', 'school_name',
            'grade', 'grade_name',
            'base_price', 'tax_rate', 'tax_type',
            'is_one_time',
            'description', 'sort_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

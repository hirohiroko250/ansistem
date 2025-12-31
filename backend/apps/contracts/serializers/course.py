"""
Course Serializers - コースシリアライザ
CourseItemSerializer, CourseListSerializer, CourseDetailSerializer
"""
from rest_framework import serializers
from ..models import Course, CourseItem


class CourseItemSerializer(serializers.ModelSerializer):
    """コース商品構成"""
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = CourseItem
        fields = [
            'id', 'product', 'product_name', 'quantity',
            'price_override', 'price', 'sort_order', 'is_active'
        ]

    def get_price(self, obj):
        return obj.get_price()


class CourseListSerializer(serializers.ModelSerializer):
    """コース一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'course_code', 'course_name', 'brand', 'brand_name',
            'course_price', 'price', 'is_active'
        ]

    def get_price(self, obj):
        return obj.get_price()


class CourseDetailSerializer(serializers.ModelSerializer):
    """コース詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True)
    course_items = CourseItemSerializer(many=True, read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'course_code', 'course_name',
            'brand', 'brand_name', 'school', 'school_name',
            'grade', 'grade_name',
            'course_price', 'price',
            'description', 'sort_order', 'is_active',
            'course_items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_price(self, obj):
        return obj.get_price()

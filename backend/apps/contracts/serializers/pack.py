"""
Pack Serializers - パックシリアライザ
PackCourseSerializer, PackListSerializer, PackDetailSerializer
"""
from rest_framework import serializers
from ..models import Pack, PackCourse


class PackCourseSerializer(serializers.ModelSerializer):
    """パックコース構成"""
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    course_price = serializers.SerializerMethodField()

    class Meta:
        model = PackCourse
        fields = [
            'id', 'course', 'course_name', 'course_price',
            'sort_order', 'is_active'
        ]

    def get_course_price(self, obj):
        return obj.course.get_price()


class PackListSerializer(serializers.ModelSerializer):
    """パック一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Pack
        fields = [
            'id', 'pack_code', 'pack_name', 'brand', 'brand_name',
            'pack_price', 'price', 'discount_type', 'discount_value', 'is_active'
        ]

    def get_price(self, obj):
        return obj.get_price()


class PackDetailSerializer(serializers.ModelSerializer):
    """パック詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    pack_courses = PackCourseSerializer(many=True, read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Pack
        fields = [
            'id', 'pack_code', 'pack_name',
            'brand', 'brand_name',
            'pack_price', 'price', 'discount_type', 'discount_value',
            'description', 'sort_order', 'is_active',
            'pack_courses',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_price(self, obj):
        return obj.get_price()

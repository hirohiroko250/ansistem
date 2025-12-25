"""
Knowledge Serializers
"""
from rest_framework import serializers
from .models import ManualCategory, Manual, TemplateCategory, ChatTemplate


class ManualCategorySerializer(serializers.ModelSerializer):
    """マニュアルカテゴリシリアライザ"""
    manual_count = serializers.SerializerMethodField()

    class Meta:
        model = ManualCategory
        fields = [
            'id', 'name', 'slug', 'description', 'parent',
            'sort_order', 'is_active', 'manual_count'
        ]

    def get_manual_count(self, obj):
        return obj.manuals.filter(is_published=True).count()


class ManualListSerializer(serializers.ModelSerializer):
    """マニュアル一覧シリアライザ"""
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Manual
        fields = [
            'id', 'title', 'slug', 'category', 'category_name',
            'summary', 'tags', 'author_name', 'external_url',
            'view_count', 'is_published', 'is_pinned',
            'created_at', 'updated_at'
        ]

    def get_author_name(self, obj):
        if obj.author:
            return f"{obj.author.last_name} {obj.author.first_name}"
        return None


class ManualDetailSerializer(serializers.ModelSerializer):
    """マニュアル詳細シリアライザ"""
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Manual
        fields = [
            'id', 'title', 'slug', 'category', 'category_name',
            'content', 'summary', 'tags', 'author', 'author_name',
            'external_url', 'view_count', 'is_published', 'is_pinned',
            'published_at', 'created_at', 'updated_at'
        ]

    def get_author_name(self, obj):
        if obj.author:
            return f"{obj.author.last_name} {obj.author.first_name}"
        return None


class ManualCreateUpdateSerializer(serializers.ModelSerializer):
    """マニュアル作成・更新シリアライザ"""

    class Meta:
        model = Manual
        fields = [
            'title', 'slug', 'category', 'content', 'summary',
            'tags', 'author', 'external_url', 'is_published', 'is_pinned'
        ]


class TemplateCategorySerializer(serializers.ModelSerializer):
    """テンプレートカテゴリシリアライザ"""
    template_count = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCategory
        fields = [
            'id', 'name', 'slug', 'description',
            'sort_order', 'is_active', 'template_count'
        ]

    def get_template_count(self, obj):
        return obj.templates.filter(is_active=True).count()


class ChatTemplateListSerializer(serializers.ModelSerializer):
    """テンプレート一覧シリアライザ"""
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)

    class Meta:
        model = ChatTemplate
        fields = [
            'id', 'title', 'template_type', 'template_type_display',
            'category', 'category_name', 'scene', 'tags',
            'use_count', 'is_active', 'is_default',
            'created_at', 'updated_at'
        ]


class ChatTemplateDetailSerializer(serializers.ModelSerializer):
    """テンプレート詳細シリアライザ"""
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)

    class Meta:
        model = ChatTemplate
        fields = [
            'id', 'title', 'template_type', 'template_type_display',
            'category', 'category_name', 'scene',
            'subject', 'content', 'variables', 'tags',
            'use_count', 'is_active', 'is_default',
            'created_at', 'updated_at'
        ]


class ChatTemplateCreateUpdateSerializer(serializers.ModelSerializer):
    """テンプレート作成・更新シリアライザ"""

    class Meta:
        model = ChatTemplate
        fields = [
            'title', 'template_type', 'category', 'scene',
            'subject', 'content', 'variables', 'tags',
            'is_active', 'is_default'
        ]


class ChatTemplateRenderSerializer(serializers.Serializer):
    """テンプレートレンダリング用シリアライザ"""
    context = serializers.DictField(child=serializers.CharField())

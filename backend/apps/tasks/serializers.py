"""Task serializers."""
from rest_framework import serializers
from .models import Task, TaskCategory, TaskComment


class TaskCategorySerializer(serializers.ModelSerializer):
    """作業カテゴリシリアライザ"""
    class Meta:
        model = TaskCategory
        fields = [
            'id', 'category_code', 'category_name', 'icon', 'color',
            'sort_order', 'is_active', 'created_at', 'updated_at'
        ]


class TaskSerializer(serializers.ModelSerializer):
    """作業シリアライザ"""
    category_name = serializers.CharField(source='category.category_name', read_only=True, allow_null=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True, allow_null=True)
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True, allow_null=True)
    student_name = serializers.SerializerMethodField()
    guardian_name = serializers.SerializerMethodField()
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'task_type', 'task_type_display', 'category', 'category_name',
            'title', 'description', 'status', 'status_display', 'priority', 'priority_display',
            'school', 'school_name', 'brand', 'brand_name',
            'student', 'student_name', 'guardian', 'guardian_name',
            'assigned_to_id', 'created_by_id', 'due_date', 'completed_at',
            'source_type', 'source_id', 'source_url', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.last_name}{obj.student.first_name}"
        return None

    def get_guardian_name(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name}{obj.guardian.first_name}"
        return None


class TaskCreateUpdateSerializer(serializers.ModelSerializer):
    """作業作成・更新シリアライザ"""
    class Meta:
        model = Task
        fields = [
            'task_type', 'category', 'title', 'description', 'status', 'priority',
            'school', 'brand', 'student', 'guardian',
            'assigned_to_id', 'due_date',
            'source_type', 'source_id', 'source_url', 'metadata'
        ]


class TaskCommentSerializer(serializers.ModelSerializer):
    """作業コメントシリアライザ"""
    class Meta:
        model = TaskComment
        fields = [
            'id', 'task', 'comment', 'commented_by_id', 'is_internal',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

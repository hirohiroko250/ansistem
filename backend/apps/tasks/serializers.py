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
    student_no = serializers.SerializerMethodField()
    guardian_name = serializers.SerializerMethodField()
    guardian_no = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'task_type', 'task_type_display', 'category', 'category_name',
            'title', 'description', 'status', 'status_display', 'priority', 'priority_display',
            'school', 'school_name', 'brand', 'brand_name',
            'student', 'student_no', 'student_name', 'guardian', 'guardian_no', 'guardian_name',
            'assigned_to_id', 'assigned_to_name', 'created_by_id', 'created_by_name', 'due_date', 'completed_at',
            'source_type', 'source_id', 'source_url', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.last_name}{obj.student.first_name}"
        return None

    def get_student_no(self, obj):
        if obj.student:
            return obj.student.student_no
        return None

    def get_guardian_name(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name}{obj.guardian.first_name}"
        return None

    def get_guardian_no(self, obj):
        if obj.guardian:
            return obj.guardian.guardian_no
        return None

    def get_assigned_to_name(self, obj):
        """担当者名を取得"""
        if obj.assigned_to_id:
            from apps.tenants.models import Employee
            try:
                employee = Employee.objects.get(id=obj.assigned_to_id)
                return employee.full_name
            except Employee.DoesNotExist:
                pass
        return None

    def get_created_by_name(self, obj):
        """作成者名を取得"""
        if obj.created_by_id:
            from apps.tenants.models import Employee
            try:
                employee = Employee.objects.get(id=obj.created_by_id)
                return employee.full_name
            except Employee.DoesNotExist:
                pass
        return None


class TaskDetailSerializer(TaskSerializer):
    """作業詳細シリアライザ（生徒・保護者情報付き）"""
    student_detail = serializers.SerializerMethodField()
    guardian_detail = serializers.SerializerMethodField()

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ['student_detail', 'guardian_detail']

    def get_student_detail(self, obj):
        """生徒の詳細情報を返す"""
        if not obj.student:
            return None
        s = obj.student
        # 受講中コース一覧
        active_courses = []
        try:
            from apps.contracts.models import Contract
            contracts = Contract.objects.filter(
                student=s, status='active'
            ).select_related('course', 'brand', 'school')
            for c in contracts:
                active_courses.append({
                    'id': str(c.id),
                    'course_name': c.course.course_name if c.course else '',
                    'brand_name': c.brand.brand_name if c.brand else '',
                    'school_name': c.school.school_name if c.school else '',
                })
        except Exception:
            pass

        return {
            'id': str(s.id),
            'student_no': s.student_no,
            'full_name': f"{s.last_name}{s.first_name}",
            'status': s.status,
            'status_display': s.get_status_display() if hasattr(s, 'get_status_display') else s.status,
            'grade_text': s.grade_text or '',
            'birth_date': str(s.birth_date) if s.birth_date else None,
            'gender': s.gender,
            'email': s.email,
            'phone': s.phone,
            'line_id': s.line_id,
            'enrollment_date': str(s.enrollment_date) if s.enrollment_date else None,
            'registered_date': str(s.registered_date) if s.registered_date else None,
            'primary_school_name': s.primary_school.school_name if s.primary_school else None,
            'primary_brand_name': s.primary_brand.brand_name if s.primary_brand else None,
            'active_courses': active_courses,
            'guardian_id': str(s.guardian_id) if s.guardian_id else None,
        }

    def get_guardian_detail(self, obj):
        """保護者の詳細情報を返す"""
        guardian = obj.guardian
        # タスクにguardianが紐付いていない場合、生徒の主保護者をフォールバック
        if not guardian and obj.student and obj.student.guardian:
            guardian = obj.student.guardian
        if not guardian:
            return None
        return {
            'id': str(guardian.id),
            'guardian_no': guardian.guardian_no,
            'full_name': f"{guardian.last_name}{guardian.first_name}",
            'email': guardian.email,
            'phone': guardian.phone,
            'phone_mobile': guardian.phone_mobile,
            'line_id': guardian.line_id,
        }


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
    commented_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskComment
        fields = [
            'id', 'task', 'comment', 'commented_by_id', 'commented_by_name', 'is_internal',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_commented_by_name(self, obj):
        """コメント者名を取得"""
        if obj.commented_by_id:
            from apps.tenants.models import Employee
            try:
                employee = Employee.objects.get(id=obj.commented_by_id)
                return employee.full_name
            except Employee.DoesNotExist:
                pass
        return None

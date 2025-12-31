"""
Enrollment Serializers - 生徒所属・保護者関連シリアライザ
"""
from rest_framework import serializers
from apps.students.models import StudentSchool, StudentGuardian


class StudentSchoolSerializer(serializers.ModelSerializer):
    """生徒所属"""
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    class_schedule_name = serializers.CharField(source='class_schedule.class_name', read_only=True)
    day_of_week_display = serializers.SerializerMethodField()

    class Meta:
        model = StudentSchool
        fields = [
            'id', 'student', 'school', 'school_name', 'brand', 'brand_name',
            'enrollment_status', 'start_date', 'end_date', 'is_primary', 'notes',
            'class_schedule', 'class_schedule_name', 'day_of_week', 'day_of_week_display',
            'start_time', 'end_time'
        ]
        read_only_fields = ['id']

    def get_day_of_week_display(self, obj):
        days = {1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'}
        return days.get(obj.day_of_week, '')


class StudentGuardianSerializer(serializers.ModelSerializer):
    """生徒保護者関連"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = StudentGuardian
        fields = [
            'id', 'student', 'student_name', 'guardian', 'guardian_name',
            'relationship', 'is_primary', 'is_emergency_contact',
            'is_billing_target', 'contact_priority', 'notes'
        ]
        read_only_fields = ['id']

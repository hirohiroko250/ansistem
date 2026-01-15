"""
HR Serializers - 勤怠管理シリアライザ
"""
from rest_framework import serializers
from .models import HRAttendance


class HRAttendanceSerializer(serializers.ModelSerializer):
    """勤怠記録シリアライザ"""
    userId = serializers.UUIDField(source='user.id', read_only=True)
    user = serializers.SerializerMethodField()
    clockInTime = serializers.DateTimeField(source='clock_in', read_only=True)
    clockOutTime = serializers.DateTimeField(source='clock_out', read_only=True)
    breakMinutes = serializers.IntegerField(source='break_minutes', read_only=True)
    workMinutes = serializers.IntegerField(source='work_minutes', read_only=True)
    overtimeMinutes = serializers.IntegerField(source='overtime_minutes', read_only=True)
    schoolId = serializers.UUIDField(source='school.id', read_only=True, allow_null=True)
    school = serializers.SerializerMethodField()
    dailyReport = serializers.CharField(source='daily_report', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = HRAttendance
        fields = [
            'id', 'userId', 'user', 'date',
            'clockInTime', 'clockOutTime',
            'breakMinutes', 'workMinutes', 'overtimeMinutes',
            'status', 'schoolId', 'school',
            'dailyReport', 'notes',
            'createdAt', 'updatedAt'
        ]

    def get_user(self, obj):
        if obj.user:
            return {
                'id': str(obj.user.id),
                'fullName': obj.user.full_name,
                'email': obj.user.email
            }
        return None

    def get_school(self, obj):
        if obj.school:
            return {
                'id': str(obj.school.id),
                'name': obj.school.school_name,
                'shortName': obj.school.short_name if hasattr(obj.school, 'short_name') else None
            }
        return None

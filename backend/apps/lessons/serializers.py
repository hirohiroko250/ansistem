"""
Lessons Serializers
"""
from rest_framework import serializers
from .models import (
    TimeSlot, LessonSchedule, LessonRecord,
    Attendance, MakeupLesson, GroupLessonEnrollment
)


class TimeSlotSerializer(serializers.ModelSerializer):
    """時間割"""

    class Meta:
        model = TimeSlot
        fields = [
            'id', 'slot_code', 'slot_name',
            'start_time', 'end_time', 'duration_minutes',
            'school', 'day_of_week', 'sort_order', 'is_active'
        ]
        read_only_fields = ['id']


class LessonScheduleListSerializer(serializers.ModelSerializer):
    """授業スケジュール一覧"""
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.classroom_name', read_only=True)

    class Meta:
        model = LessonSchedule
        fields = [
            'id', 'school', 'school_name', 'classroom', 'classroom_name',
            'subject', 'subject_name', 'lesson_type',
            'date', 'start_time', 'end_time',
            'teacher', 'teacher_name', 'student', 'student_name',
            'class_name', 'status'
        ]

    def get_teacher_name(self, obj):
        if obj.teacher:
            return f"{obj.teacher.last_name} {obj.teacher.first_name}".strip() or obj.teacher.email
        return None


class LessonScheduleDetailSerializer(serializers.ModelSerializer):
    """授業スケジュール詳細"""
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.classroom_name', read_only=True)
    time_slot_name = serializers.CharField(source='time_slot.slot_name', read_only=True)

    class Meta:
        model = LessonSchedule
        fields = [
            'id', 'school', 'school_name', 'classroom', 'classroom_name',
            'subject', 'subject_name', 'lesson_type',
            'date', 'time_slot', 'time_slot_name', 'start_time', 'end_time',
            'teacher', 'teacher_name', 'student', 'student_name',
            'contract', 'contract_detail_id',
            'class_name', 'capacity', 'status', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_teacher_name(self, obj):
        if obj.teacher:
            return f"{obj.teacher.last_name} {obj.teacher.first_name}".strip() or obj.teacher.email
        return None


class LessonScheduleCreateSerializer(serializers.ModelSerializer):
    """授業スケジュール作成"""

    class Meta:
        model = LessonSchedule
        fields = [
            'school', 'classroom', 'subject', 'lesson_type',
            'date', 'time_slot', 'start_time', 'end_time',
            'teacher', 'student', 'contract', 'contract_detail_id',
            'class_name', 'capacity', 'notes'
        ]


class LessonRecordSerializer(serializers.ModelSerializer):
    """授業実績"""
    schedule_info = serializers.SerializerMethodField()

    class Meta:
        model = LessonRecord
        fields = [
            'id', 'schedule', 'schedule_info',
            'actual_start_time', 'actual_end_time', 'actual_duration_minutes',
            'content', 'homework', 'next_lesson_plan',
            'understanding_level', 'attitude_evaluation', 'homework_status',
            'teacher_comment', 'internal_memo',
            'recorded_at', 'recorded_by'
        ]
        read_only_fields = ['id', 'recorded_at']

    def get_schedule_info(self, obj):
        schedule = obj.schedule
        teacher_name = None
        if schedule.teacher:
            teacher_name = f"{schedule.teacher.last_name} {schedule.teacher.first_name}".strip() or schedule.teacher.email
        return {
            'date': schedule.date,
            'subject': schedule.subject.subject_name if schedule.subject else None,
            'student': schedule.student.full_name if schedule.student else None,
            'teacher': teacher_name,
        }


class AttendanceSerializer(serializers.ModelSerializer):
    """出席記録"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id', 'schedule', 'student', 'student_name',
            'status', 'check_in_time', 'check_out_time',
            'absence_reason', 'absence_notified_at', 'notes'
        ]
        read_only_fields = ['id']


class MakeupLessonListSerializer(serializers.ModelSerializer):
    """振替一覧"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    original_date = serializers.DateField(source='original_schedule.date', read_only=True)
    original_subject = serializers.CharField(
        source='original_schedule.subject.subject_name', read_only=True
    )

    class Meta:
        model = MakeupLesson
        fields = [
            'id', 'student', 'student_name',
            'original_schedule', 'original_date', 'original_subject',
            'makeup_schedule', 'preferred_date',
            'status', 'valid_until', 'requested_at'
        ]


class MakeupLessonDetailSerializer(serializers.ModelSerializer):
    """振替詳細"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    original_schedule_info = serializers.SerializerMethodField()
    makeup_schedule_info = serializers.SerializerMethodField()

    class Meta:
        model = MakeupLesson
        fields = [
            'id', 'original_schedule', 'original_schedule_info',
            'student', 'student_name',
            'makeup_schedule', 'makeup_schedule_info',
            'preferred_date', 'preferred_time_slot',
            'status', 'valid_until',
            'requested_at', 'requested_by',
            'processed_at', 'processed_by',
            'reason', 'notes'
        ]
        read_only_fields = ['id', 'requested_at']

    def get_original_schedule_info(self, obj):
        schedule = obj.original_schedule
        return {
            'date': schedule.date,
            'start_time': schedule.start_time,
            'end_time': schedule.end_time,
            'subject': schedule.subject.subject_name if schedule.subject else None,
        }

    def get_makeup_schedule_info(self, obj):
        if not obj.makeup_schedule:
            return None
        schedule = obj.makeup_schedule
        return {
            'date': schedule.date,
            'start_time': schedule.start_time,
            'end_time': schedule.end_time,
            'subject': schedule.subject.subject_name if schedule.subject else None,
        }


class GroupLessonEnrollmentSerializer(serializers.ModelSerializer):
    """集団授業受講者"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = GroupLessonEnrollment
        fields = ['id', 'schedule', 'student', 'student_name', 'enrolled_at']
        read_only_fields = ['id', 'enrolled_at']


class CalendarEventSerializer(serializers.Serializer):
    """カレンダー表示用"""
    id = serializers.UUIDField()
    title = serializers.CharField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    type = serializers.CharField()
    status = serializers.CharField()
    color = serializers.CharField(required=False)
    resource_id = serializers.UUIDField(required=False)

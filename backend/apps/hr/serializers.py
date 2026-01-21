"""
HR Serializers - 勤怠管理シリアライザ
"""
from rest_framework import serializers
from .models import (
    HRAttendance,
    StaffAvailability,
    StaffAvailabilityBooking,
    StaffWorkSchedule,
    StaffProfile,
    StaffSkill,
    StaffReview,
    StaffProfilePhoto,
)


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


class StaffAvailabilitySerializer(serializers.ModelSerializer):
    """社員空き時間シリアライザ"""
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    school_id = serializers.UUIDField(source='school.id', read_only=True, allow_null=True)
    school_name = serializers.SerializerMethodField()
    is_bookable = serializers.BooleanField(read_only=True)
    remaining_slots = serializers.IntegerField(read_only=True)
    bookings_count = serializers.SerializerMethodField()

    class Meta:
        model = StaffAvailability
        fields = [
            'id', 'employee_id', 'employee_name',
            'date', 'start_time', 'end_time',
            'status', 'capacity', 'current_bookings',
            'cancel_deadline_minutes',
            'school_id', 'school_name',
            'online_available', 'meeting_url',
            'notes', 'is_recurring', 'recurring_pattern',
            'is_bookable', 'remaining_slots', 'bookings_count',
            'created_at', 'updated_at'
        ]

    def get_school_name(self, obj):
        return obj.school.school_name if obj.school else None

    def get_bookings_count(self, obj):
        return obj.bookings.exclude(status='cancelled').count()


class StaffAvailabilityCreateSerializer(serializers.ModelSerializer):
    """社員空き時間作成シリアライザ"""

    class Meta:
        model = StaffAvailability
        fields = [
            'date', 'start_time', 'end_time',
            'capacity', 'cancel_deadline_minutes',
            'school', 'online_available', 'meeting_url',
            'notes', 'is_recurring', 'recurring_pattern', 'recurring_end_date'
        ]


class StaffAvailabilityBookingSerializer(serializers.ModelSerializer):
    """空き時間予約シリアライザ"""
    availability_info = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)

    class Meta:
        model = StaffAvailabilityBooking
        fields = [
            'id', 'availability', 'availability_info',
            'student', 'student_name', 'status',
            'request_message', 'staff_notes',
            'student_item', 'cancelled_at', 'cancel_reason',
            'can_cancel', 'created_at', 'updated_at'
        ]

    def get_availability_info(self, obj):
        return {
            'id': str(obj.availability.id),
            'date': obj.availability.date,
            'start_time': obj.availability.start_time,
            'end_time': obj.availability.end_time,
            'employee_name': obj.availability.employee.full_name,
        }


class StaffWorkScheduleSerializer(serializers.ModelSerializer):
    """勤務スケジュールシリアライザ"""
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    school_name = serializers.SerializerMethodField()

    class Meta:
        model = StaffWorkSchedule
        fields = [
            'id', 'employee_id', 'employee_name',
            'date', 'schedule_type',
            'planned_start', 'planned_end',
            'school', 'school_name', 'notes',
            'is_approved', 'approved_by',
            'created_at', 'updated_at'
        ]

    def get_school_name(self, obj):
        return obj.school.school_name if obj.school else None


class StaffSkillSerializer(serializers.ModelSerializer):
    """講師スキルシリアライザ"""

    class Meta:
        model = StaffSkill
        fields = ['id', 'category', 'name', 'level', 'display_order', 'color']


class StaffReviewSerializer(serializers.ModelSerializer):
    """講師レビューシリアライザ"""
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = StaffReview
        fields = [
            'id', 'rating', 'comment',
            'student_name', 'is_anonymous',
            'created_at'
        ]

    def get_student_name(self, obj):
        if obj.is_anonymous or not obj.student:
            return None
        return obj.student.full_name


class StaffProfilePhotoSerializer(serializers.ModelSerializer):
    """講師写真シリアライザ"""

    class Meta:
        model = StaffProfilePhoto
        fields = ['id', 'image_url', 'caption', 'is_main', 'display_order']


class StaffProfileSerializer(serializers.ModelSerializer):
    """講師プロフィールシリアライザ"""
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_email = serializers.CharField(source='employee.email', read_only=True)
    profile_image_url = serializers.CharField(source='employee.profile_image_url', read_only=True)
    position_name = serializers.SerializerMethodField()
    skills = StaffSkillSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    photos = StaffProfilePhotoSerializer(many=True, read_only=True)
    brands = serializers.SerializerMethodField()

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'employee_id', 'employee_name', 'employee_email',
            'profile_image_url', 'position_name',
            'display_name', 'greeting', 'bio', 'lesson_style', 'career',
            'origin_country', 'residence_country',
            'communication_tool', 'communication_url',
            'line_id', 'twitter_url', 'instagram_url', 'youtube_url',
            'rating', 'review_count', 'lesson_count', 'points',
            'is_public', 'is_bookable', 'admin_comment',
            'skills', 'reviews', 'photos', 'brands',
            'created_at', 'updated_at'
        ]

    def get_position_name(self, obj):
        if obj.employee.position:
            return obj.employee.position.position_name
        return obj.employee.position_text

    def get_reviews(self, obj):
        # 公開されたレビューのみ返す
        public_reviews = obj.reviews.filter(is_public=True, is_approved=True)[:5]
        return StaffReviewSerializer(public_reviews, many=True).data

    def get_brands(self, obj):
        return [
            {'id': str(b.id), 'name': b.brand_name}
            for b in obj.employee.brands.all()
        ]


class StaffProfileUpdateSerializer(serializers.ModelSerializer):
    """講師プロフィール更新シリアライザ"""

    class Meta:
        model = StaffProfile
        fields = [
            'display_name', 'greeting', 'bio', 'lesson_style', 'career',
            'origin_country', 'residence_country',
            'communication_tool', 'communication_url',
            'line_id', 'twitter_url', 'instagram_url', 'youtube_url',
            'is_public', 'is_bookable', 'admin_comment'
        ]

"""
Schools Serializers
"""
from rest_framework import serializers
from .models import Brand, School, Grade, Subject, Classroom, TimeSlot, SchoolSchedule, SchoolCourse, SchoolClosure


class BrandListSerializer(serializers.ModelSerializer):
    """ブランド一覧"""
    school_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Brand
        fields = [
            'id', 'brand_code', 'brand_name', 'brand_name_short',
            'brand_type', 'logo_url', 'color_primary',
            'sort_order', 'is_active', 'school_count'
        ]


class BrandDetailSerializer(serializers.ModelSerializer):
    """ブランド詳細"""

    class Meta:
        model = Brand
        fields = [
            'id', 'brand_code', 'brand_name', 'brand_name_short',
            'brand_type', 'description', 'logo_url',
            'color_primary', 'color_secondary',
            'sort_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BrandCreateUpdateSerializer(serializers.ModelSerializer):
    """ブランド作成・更新"""

    class Meta:
        model = Brand
        fields = [
            'brand_code', 'brand_name', 'brand_name_short',
            'brand_type', 'description', 'logo_url',
            'color_primary', 'color_secondary',
            'sort_order', 'is_active'
        ]


class SchoolListSerializer(serializers.ModelSerializer):
    """校舎一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)

    class Meta:
        model = School
        fields = [
            'id', 'school_code', 'school_name', 'school_name_short',
            'brand', 'brand_name', 'school_type',
            'prefecture', 'city', 'phone',
            'sort_order', 'is_active'
        ]


class SchoolDetailSerializer(serializers.ModelSerializer):
    """校舎詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)

    class Meta:
        model = School
        fields = [
            'id', 'brand', 'brand_name',
            'school_code', 'school_name', 'school_name_short', 'school_type',
            'postal_code', 'prefecture', 'city', 'address1', 'address2',
            'phone', 'fax', 'email',
            'latitude', 'longitude',
            'capacity', 'opening_date', 'closing_date',
            'settings', 'sort_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SchoolCreateUpdateSerializer(serializers.ModelSerializer):
    """校舎作成・更新"""

    class Meta:
        model = School
        fields = [
            'brand', 'school_code', 'school_name', 'school_name_short', 'school_type',
            'postal_code', 'prefecture', 'city', 'address1', 'address2',
            'phone', 'fax', 'email',
            'latitude', 'longitude',
            'capacity', 'opening_date', 'closing_date',
            'settings', 'sort_order', 'is_active'
        ]


class GradeSerializer(serializers.ModelSerializer):
    """学年"""

    class Meta:
        model = Grade
        fields = [
            'id', 'grade_code', 'grade_name', 'grade_name_short',
            'category', 'school_year', 'sort_order', 'is_active'
        ]
        read_only_fields = ['id']


class SubjectSerializer(serializers.ModelSerializer):
    """教科"""

    class Meta:
        model = Subject
        fields = [
            'id', 'subject_code', 'subject_name', 'subject_name_short',
            'category', 'color', 'icon', 'sort_order', 'is_active'
        ]
        read_only_fields = ['id']


class ClassroomListSerializer(serializers.ModelSerializer):
    """教室一覧"""
    school_name = serializers.CharField(source='school.school_name', read_only=True)

    class Meta:
        model = Classroom
        fields = [
            'id', 'school', 'school_name',
            'classroom_code', 'classroom_name',
            'capacity', 'room_type', 'is_active'
        ]


class ClassroomDetailSerializer(serializers.ModelSerializer):
    """教室詳細"""
    school_name = serializers.CharField(source='school.school_name', read_only=True)

    class Meta:
        model = Classroom
        fields = [
            'id', 'school', 'school_name',
            'classroom_code', 'classroom_name',
            'capacity', 'floor', 'room_type', 'equipment',
            'sort_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PublicSchoolSerializer(serializers.ModelSerializer):
    """公開校舎情報（認証不要・新規登録用）"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    brand_code = serializers.CharField(source='brand.brand_code', read_only=True)

    class Meta:
        model = School
        fields = [
            'id', 'school_code', 'school_name',
            'brand_name', 'brand_code',
            'prefecture', 'city', 'address1',
            'phone',
        ]


# ========================================
# TimeSlot（時間帯）
# ========================================
class TimeSlotSerializer(serializers.ModelSerializer):
    """時間帯"""

    class Meta:
        model = TimeSlot
        fields = [
            'id', 'slot_code', 'slot_name',
            'start_time', 'end_time', 'duration_minutes',
            'sort_order', 'is_active'
        ]
        read_only_fields = ['id']


# ========================================
# SchoolSchedule（校舎開講スケジュール）
# ========================================
class SchoolScheduleListSerializer(serializers.ModelSerializer):
    """校舎開講スケジュール一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    brand_code = serializers.CharField(source='brand.brand_code', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    school_code = serializers.CharField(source='school.school_code', read_only=True)
    time_slot_name = serializers.CharField(source='time_slot.slot_name', read_only=True)
    time_slot_code = serializers.CharField(source='time_slot.slot_code', read_only=True)
    start_time = serializers.TimeField(source='time_slot.start_time', read_only=True)
    end_time = serializers.TimeField(source='time_slot.end_time', read_only=True)
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    available_seats = serializers.IntegerField(read_only=True)

    class Meta:
        model = SchoolSchedule
        fields = [
            'id', 'brand', 'brand_code', 'brand_name',
            'school', 'school_code', 'school_name',
            'day_of_week', 'day_of_week_display',
            'time_slot', 'time_slot_code', 'time_slot_name',
            'start_time', 'end_time',
            'capacity', 'reserved_seats', 'available_seats',
            'valid_from', 'valid_until',
            'is_active'
        ]


class SchoolScheduleDetailSerializer(serializers.ModelSerializer):
    """校舎開講スケジュール詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    time_slot_name = serializers.CharField(source='time_slot.slot_name', read_only=True)
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    available_seats = serializers.IntegerField(read_only=True)

    class Meta:
        model = SchoolSchedule
        fields = [
            'id', 'brand', 'brand_name',
            'school', 'school_name',
            'day_of_week', 'day_of_week_display',
            'time_slot', 'time_slot_name',
            'capacity', 'reserved_seats', 'available_seats',
            'valid_from', 'valid_until',
            'notes', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SchoolScheduleCreateUpdateSerializer(serializers.ModelSerializer):
    """校舎開講スケジュール作成・更新"""

    class Meta:
        model = SchoolSchedule
        fields = [
            'brand', 'school', 'day_of_week', 'time_slot',
            'capacity', 'reserved_seats',
            'valid_from', 'valid_until',
            'notes', 'is_active'
        ]


# ========================================
# SchoolCourse（校舎別コース）
# ========================================
class SchoolCourseListSerializer(serializers.ModelSerializer):
    """校舎別コース一覧"""
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    school_code = serializers.CharField(source='school.school_code', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    course_code = serializers.CharField(source='course.course_code', read_only=True)
    schedule_info = serializers.SerializerMethodField()
    effective_capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = SchoolCourse
        fields = [
            'id', 'school', 'school_code', 'school_name',
            'course', 'course_code', 'course_name',
            'schedule', 'schedule_info',
            'capacity_override', 'effective_capacity',
            'valid_from', 'valid_until',
            'is_active'
        ]

    def get_schedule_info(self, obj):
        if obj.schedule:
            return f"{obj.schedule.get_day_of_week_display()} {obj.schedule.time_slot.slot_name}"
        return None


class SchoolCourseDetailSerializer(serializers.ModelSerializer):
    """校舎別コース詳細"""
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    effective_capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = SchoolCourse
        fields = [
            'id', 'school', 'school_name',
            'course', 'course_name',
            'schedule', 'capacity_override', 'effective_capacity',
            'valid_from', 'valid_until',
            'notes', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ========================================
# SchoolClosure（休講）
# ========================================
class SchoolClosureListSerializer(serializers.ModelSerializer):
    """休講一覧"""
    school_name = serializers.CharField(source='school.school_name', read_only=True, allow_null=True)
    school_code = serializers.CharField(source='school.school_code', read_only=True, allow_null=True)
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True, allow_null=True)
    brand_code = serializers.CharField(source='brand.brand_code', read_only=True, allow_null=True)
    closure_type_display = serializers.CharField(source='get_closure_type_display', read_only=True)

    class Meta:
        model = SchoolClosure
        fields = [
            'id', 'school', 'school_code', 'school_name',
            'brand', 'brand_code', 'brand_name',
            'schedule',
            'closure_date', 'closure_type', 'closure_type_display',
            'has_makeup', 'makeup_date',
            'reason'
        ]


class SchoolClosureDetailSerializer(serializers.ModelSerializer):
    """休講詳細"""
    school_name = serializers.CharField(source='school.school_name', read_only=True, allow_null=True)
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True, allow_null=True)
    closure_type_display = serializers.CharField(source='get_closure_type_display', read_only=True)

    class Meta:
        model = SchoolClosure
        fields = [
            'id', 'school', 'school_name',
            'brand', 'brand_name',
            'schedule', 'makeup_schedule',
            'closure_date', 'closure_type', 'closure_type_display',
            'has_makeup', 'makeup_date',
            'reason', 'notes', 'notified_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SchoolClosureCreateUpdateSerializer(serializers.ModelSerializer):
    """休講作成・更新"""

    class Meta:
        model = SchoolClosure
        fields = [
            'school', 'brand', 'schedule',
            'closure_date', 'closure_type',
            'has_makeup', 'makeup_date', 'makeup_schedule',
            'reason', 'notes', 'notified_at'
        ]

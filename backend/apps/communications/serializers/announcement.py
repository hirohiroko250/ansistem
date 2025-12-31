"""
Announcement Serializers - お知らせシリアライザー
"""
from rest_framework import serializers
from apps.communications.models import Announcement, AnnouncementRead


class AnnouncementListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'target_type', 'status',
            'scheduled_at', 'sent_at', 'sent_count', 'read_count',
            'created_by', 'created_by_name', 'created_at'
        ]


class AnnouncementDetailSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    target_schools_detail = serializers.SerializerMethodField()
    target_grades_detail = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            'id', 'tenant_id', 'title', 'content', 'target_type',
            'target_schools', 'target_schools_detail',
            'target_grades', 'target_grades_detail',
            'status', 'scheduled_at', 'sent_at',
            'sent_count', 'read_count',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant_id', 'sent_at', 'sent_count', 'read_count', 'created_at', 'updated_at']

    def get_target_schools_detail(self, obj):
        return [{'id': s.id, 'name': s.school_name} for s in obj.target_schools.all()]

    def get_target_grades_detail(self, obj):
        return [{'id': g.id, 'name': g.grade_name} for g in obj.target_grades.all()]


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'target_type',
            'target_schools', 'target_grades', 'scheduled_at'
        ]

"""
Contact Log & Notification Serializers - 対応履歴・通知シリアライザー
"""
from rest_framework import serializers
from apps.communications.models import ContactLog, ContactLogComment, Notification


class ContactLogCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = ContactLogComment
        fields = ['id', 'contact_log', 'user', 'user_name', 'content', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class ContactLogListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    handled_by_name = serializers.CharField(source='handled_by.full_name', read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = ContactLog
        fields = [
            'id', 'contact_type', 'subject', 'student', 'student_name',
            'guardian', 'guardian_name', 'school', 'handled_by', 'handled_by_name',
            'priority', 'status', 'follow_up_date', 'tags',
            'comment_count', 'created_at', 'updated_at'
        ]

    def get_comment_count(self, obj):
        return obj.comments.count()


class ContactLogDetailSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    handled_by_name = serializers.CharField(source='handled_by.full_name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)
    comments = ContactLogCommentSerializer(many=True, read_only=True)

    class Meta:
        model = ContactLog
        fields = [
            'id', 'tenant_id', 'contact_type', 'subject', 'content',
            'student', 'student_name', 'guardian', 'guardian_name',
            'school', 'school_name', 'handled_by', 'handled_by_name',
            'priority', 'status', 'related_channel',
            'follow_up_date', 'follow_up_notes',
            'resolved_at', 'resolved_by', 'resolved_by_name',
            'tags', 'comments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant_id', 'created_at', 'updated_at']


class ContactLogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactLog
        fields = [
            'contact_type', 'subject', 'content',
            'student', 'guardian', 'school',
            'priority', 'status', 'follow_up_date', 'follow_up_notes', 'tags'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'content',
            'link_type', 'link_id', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

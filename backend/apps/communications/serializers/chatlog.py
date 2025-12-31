"""
ChatLog Serializers - チャットログシリアライザー
"""
from rest_framework import serializers
from apps.communications.models import ChatLog


class ChatLogSerializer(serializers.ModelSerializer):
    """チャットログシリアライザー"""

    class Meta:
        model = ChatLog
        fields = [
            'id', 'tenant_id', 'message', 'school', 'school_name',
            'guardian', 'guardian_name', 'brand', 'brand_name',
            'content', 'sender_type', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class ChatLogListSerializer(serializers.ModelSerializer):
    """チャットログ一覧用シリアライザー"""

    class Meta:
        model = ChatLog
        fields = [
            'id', 'brand_name', 'school_name', 'guardian_name',
            'content', 'sender_type', 'timestamp'
        ]

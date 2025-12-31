"""
Bot Serializers - ボットシリアライザー
"""
from rest_framework import serializers
from apps.communications.models import BotConfig, BotFAQ, BotConversation


class BotFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotFAQ
        fields = [
            'id', 'bot_config', 'category', 'question', 'keywords',
            'answer', 'next_action', 'sort_order', 'is_active'
        ]
        read_only_fields = ['id']


class BotConfigSerializer(serializers.ModelSerializer):
    faqs = BotFAQSerializer(many=True, read_only=True)
    faq_count = serializers.SerializerMethodField()

    class Meta:
        model = BotConfig
        fields = [
            'id', 'tenant_id', 'name', 'bot_type',
            'welcome_message', 'fallback_message',
            'is_active', 'ai_enabled', 'ai_model', 'ai_system_prompt',
            'faqs', 'faq_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant_id', 'created_at', 'updated_at']

    def get_faq_count(self, obj):
        return obj.faqs.filter(is_active=True).count()


class BotConversationSerializer(serializers.ModelSerializer):
    matched_faq_question = serializers.CharField(source='matched_faq.question', read_only=True)

    class Meta:
        model = BotConversation
        fields = [
            'id', 'channel', 'bot_config', 'user_input', 'bot_response',
            'matched_faq', 'matched_faq_question', 'is_ai_response',
            'escalated_to_staff', 'escalated_at', 'was_helpful', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BotChatSerializer(serializers.Serializer):
    """ボットチャット用"""
    message = serializers.CharField()
    channel_id = serializers.UUIDField(required=False)

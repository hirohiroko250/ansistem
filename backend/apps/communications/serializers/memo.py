"""
Memo Serializers - 伝言メモ・TEL登録メモ
"""
from rest_framework import serializers
from apps.communications.models import MessageMemo, TelMemo


class MessageMemoSerializer(serializers.ModelSerializer):
    """伝言メモシリアライザ"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_no = serializers.CharField(source='student.student_no', read_only=True)
    guardian_no = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    completed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MessageMemo
        fields = [
            'id', 'tenant_id',
            'student', 'student_id', 'student_name', 'student_no', 'guardian_no',
            'content', 'priority', 'status',
            'created_by', 'created_by_name',
            'completed_by', 'completed_by_name', 'completed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'completed_by', 'completed_at', 'created_at', 'updated_at']

    def get_guardian_no(self, obj):
        if obj.student and obj.student.guardian:
            return obj.student.guardian.guardian_no
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None

    def get_completed_by_name(self, obj):
        if obj.completed_by:
            return obj.completed_by.get_full_name() or obj.completed_by.email
        return None


class MessageMemoCreateSerializer(serializers.ModelSerializer):
    """伝言メモ作成シリアライザ"""
    student_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = MessageMemo
        fields = ['student_id', 'content', 'priority']

    def create(self, validated_data):
        student_id = validated_data.pop('student_id')
        validated_data['student_id'] = student_id
        return super().create(validated_data)


class TelMemoSerializer(serializers.ModelSerializer):
    """TEL登録メモシリアライザ"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_no = serializers.CharField(source='student.student_no', read_only=True)
    guardian_no = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TelMemo
        fields = [
            'id', 'tenant_id',
            'student', 'student_id', 'student_name', 'student_no', 'guardian_no',
            'phone_number', 'call_direction', 'call_result',
            'content',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_guardian_no(self, obj):
        if obj.student and obj.student.guardian:
            return obj.student.guardian.guardian_no
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None


class TelMemoCreateSerializer(serializers.ModelSerializer):
    """TEL登録メモ作成シリアライザ"""
    student_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = TelMemo
        fields = ['student_id', 'phone_number', 'call_direction', 'call_result', 'content']

    def create(self, validated_data):
        student_id = validated_data.pop('student_id')
        validated_data['student_id'] = student_id
        return super().create(validated_data)

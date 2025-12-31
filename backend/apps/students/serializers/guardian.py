"""
Guardian Serializers - 保護者シリアライザ
"""
from rest_framework import serializers
from apps.students.models import Guardian


class GuardianListSerializer(serializers.ModelSerializer):
    """保護者一覧"""
    full_name = serializers.CharField(read_only=True)
    student_count = serializers.IntegerField(read_only=True)
    student_names = serializers.SerializerMethodField()
    has_account = serializers.SerializerMethodField()

    class Meta:
        model = Guardian
        fields = [
            'id', 'guardian_no', 'full_name', 'last_name', 'first_name',
            'last_name_kana', 'first_name_kana',
            'email', 'phone', 'phone_mobile', 'student_count', 'student_names',
            'has_account'
        ]

    def get_student_names(self, obj):
        """保護者に紐づく生徒名のリストを返す"""
        children = obj.children.filter(deleted_at__isnull=True)[:5]
        return [f"{s.last_name}{s.first_name}" for s in children]

    def get_has_account(self, obj):
        """保護者にログインアカウントが紐付いているか"""
        return obj.user_id is not None


class GuardianDetailSerializer(serializers.ModelSerializer):
    """保護者詳細"""
    full_name = serializers.CharField(read_only=True)
    has_account = serializers.SerializerMethodField()
    is_employee = serializers.BooleanField(read_only=True)
    employee_discount_info = serializers.DictField(read_only=True)

    class Meta:
        model = Guardian
        fields = [
            'id', 'guardian_no',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana', 'full_name',
            'email', 'phone', 'phone_mobile', 'line_id',
            'postal_code', 'prefecture', 'city', 'address1', 'address2',
            'workplace', 'workplace_phone',
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_number', 'account_holder', 'account_holder_kana',
            'withdrawal_day', 'payment_registered', 'payment_registered_at',
            'notes',
            'has_account',
            'is_employee', 'employee_discount_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'has_account', 'is_employee', 'employee_discount_info']

    def get_has_account(self, obj):
        return obj.user_id is not None


class GuardianPaymentSerializer(serializers.ModelSerializer):
    """保護者支払い情報"""
    full_name = serializers.CharField(read_only=True)
    account_number_masked = serializers.SerializerMethodField()

    class Meta:
        model = Guardian
        fields = [
            'id', 'guardian_no', 'full_name',
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_number', 'account_number_masked',
            'account_holder', 'account_holder_kana',
            'withdrawal_day', 'payment_registered', 'payment_registered_at'
        ]
        read_only_fields = ['id', 'guardian_no', 'full_name', 'account_number_masked']

    def get_account_number_masked(self, obj):
        """口座番号をマスク（下4桁のみ表示）"""
        if obj.account_number and len(obj.account_number) >= 4:
            return '•' * (len(obj.account_number) - 4) + obj.account_number[-4:]
        return obj.account_number or ''


class GuardianPaymentUpdateSerializer(serializers.ModelSerializer):
    """保護者支払い情報更新"""

    class Meta:
        model = Guardian
        fields = [
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_number', 'account_holder', 'account_holder_kana',
            'withdrawal_day'
        ]

    def update(self, instance, validated_data):
        from django.utils import timezone
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.payment_registered = True
        instance.payment_registered_at = timezone.now()
        instance.save()
        return instance


class GuardianCreateUpdateSerializer(serializers.ModelSerializer):
    """保護者作成・更新"""

    class Meta:
        model = Guardian
        fields = [
            'guardian_no',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
            'email', 'phone', 'phone_mobile', 'line_id',
            'postal_code', 'prefecture', 'city', 'address1', 'address2',
            'workplace', 'workplace_phone',
            'notes'
        ]

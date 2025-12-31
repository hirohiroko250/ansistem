"""
Bank Serializers - 銀行口座関連シリアライザ
"""
from rest_framework import serializers
from apps.students.models import BankAccount, BankAccountChangeRequest


class BankAccountSerializer(serializers.ModelSerializer):
    """銀行口座シリアライザ"""
    guardian_name = serializers.SerializerMethodField()
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            'id', 'guardian', 'guardian_name',
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_type_display',
            'account_number', 'account_holder', 'account_holder_kana',
            'is_primary', 'is_active', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'guardian_name', 'created_at', 'updated_at']

    def get_guardian_name(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name} {obj.guardian.first_name}"
        return ""


class BankAccountChangeRequestSerializer(serializers.ModelSerializer):
    """銀行口座変更申請シリアライザ"""
    guardian_name = serializers.SerializerMethodField()
    guardian_no = serializers.CharField(source='guardian.guardian_no', read_only=True)
    guardian_email = serializers.CharField(source='guardian.email', read_only=True)
    guardian_phone = serializers.SerializerMethodField()
    guardian_address = serializers.SerializerMethodField()
    guardian_name_kana = serializers.SerializerMethodField()
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    processed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BankAccountChangeRequest
        fields = [
            'id', 'guardian', 'guardian_name', 'guardian_no',
            'guardian_email', 'guardian_phone', 'guardian_address', 'guardian_name_kana',
            'existing_account',
            'request_type', 'request_type_display',
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_type_display',
            'account_number', 'account_holder', 'account_holder_kana',
            'is_primary',
            'status', 'status_display',
            'requested_at', 'requested_by', 'requested_by_name', 'request_notes',
            'processed_at', 'processed_by', 'processed_by_name', 'process_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'guardian_name', 'guardian_no',
            'guardian_email', 'guardian_phone', 'guardian_address', 'guardian_name_kana',
            'request_type_display', 'status_display', 'account_type_display',
            'requested_at', 'requested_by', 'requested_by_name',
            'processed_at', 'processed_by', 'processed_by_name', 'process_notes',
            'status', 'created_at', 'updated_at'
        ]

    def get_guardian_name(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name} {obj.guardian.first_name}"
        return ""

    def get_guardian_name_kana(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name_kana} {obj.guardian.first_name_kana}".strip()
        return ""

    def get_guardian_phone(self, obj):
        if obj.guardian:
            return obj.guardian.phone_mobile or obj.guardian.phone or ""
        return ""

    def get_guardian_address(self, obj):
        if obj.guardian:
            parts = [
                obj.guardian.postal_code,
                obj.guardian.prefecture,
                obj.guardian.city,
                obj.guardian.address1,
                obj.guardian.address2,
            ]
            return " ".join(p for p in parts if p)
        return ""

    def get_requested_by_name(self, obj):
        if obj.requested_by:
            return f"{obj.requested_by.first_name} {obj.requested_by.last_name}".strip() or obj.requested_by.email
        return ""

    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return f"{obj.processed_by.first_name} {obj.processed_by.last_name}".strip() or obj.processed_by.email
        return ""


class BankAccountChangeRequestCreateSerializer(serializers.ModelSerializer):
    """銀行口座変更申請作成用シリアライザ"""

    class Meta:
        model = BankAccountChangeRequest
        fields = [
            'existing_account', 'request_type',
            'bank_name', 'bank_code', 'branch_name', 'branch_code',
            'account_type', 'account_number',
            'account_holder', 'account_holder_kana',
            'is_primary', 'request_notes'
        ]

    def validate(self, data):
        request_type = data.get('request_type', 'new')

        # 新規・変更の場合は銀行情報が必須
        if request_type in ('new', 'update'):
            required_fields = ['bank_name', 'branch_name', 'account_number', 'account_holder', 'account_holder_kana']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError({field: 'この項目は必須です。'})

        # 変更・削除の場合はexisting_accountが必須
        if request_type in ('update', 'delete'):
            if not data.get('existing_account'):
                raise serializers.ValidationError({'existing_account': '変更・削除には既存口座の指定が必須です。'})

        return data

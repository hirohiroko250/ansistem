"""
Mile Serializers - マイルシリアライザー
"""
from rest_framework import serializers
from apps.billing.models import MileTransaction


class MileTransactionSerializer(serializers.ModelSerializer):
    """マイル取引シリアライザ"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = MileTransaction
        fields = [
            'id', 'guardian', 'guardian_name', 'invoice',
            'transaction_type', 'transaction_type_display',
            'miles', 'balance_after', 'discount_amount',
            'earn_source', 'earn_date', 'expire_date',
            'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MileBalanceSerializer(serializers.Serializer):
    """マイル残高シリアライザ"""
    guardian_id = serializers.UUIDField()
    balance = serializers.IntegerField()
    can_use = serializers.BooleanField()
    min_use = serializers.IntegerField(default=4)


class MileCalculateSerializer(serializers.Serializer):
    """マイル割引計算用シリアライザ"""
    miles_to_use = serializers.IntegerField(min_value=0)

    def validate_miles_to_use(self, value):
        if value > 0 and value < 4:
            raise serializers.ValidationError('マイルは4pt以上から使用可能です')
        return value


class MileUseSerializer(serializers.Serializer):
    """マイル使用用シリアライザ"""
    guardian_id = serializers.UUIDField()
    invoice_id = serializers.UUIDField()
    miles_to_use = serializers.IntegerField(min_value=4)

    def validate_miles_to_use(self, value):
        if value < 4:
            raise serializers.ValidationError('マイルは4pt以上から使用可能です')
        return value

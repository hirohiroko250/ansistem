"""
Balance Serializers - 預り金・相殺ログシリアライザー
"""
from rest_framework import serializers
from apps.billing.models import GuardianBalance, OffsetLog


class GuardianBalanceSerializer(serializers.ModelSerializer):
    """預り金残高シリアライザ"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)

    class Meta:
        model = GuardianBalance
        fields = [
            'id', 'guardian', 'guardian_name',
            'balance', 'last_updated', 'notes',
        ]
        read_only_fields = ['id', 'balance', 'last_updated']


class BalanceDepositSerializer(serializers.Serializer):
    """預り金入金用シリアライザ"""
    guardian_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=0)
    reason = serializers.CharField(required=False, allow_blank=True)


class BalanceOffsetSerializer(serializers.Serializer):
    """預り金相殺用シリアライザ"""
    guardian_id = serializers.UUIDField()
    invoice_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=0)


class OffsetLogSerializer(serializers.ModelSerializer):
    """相殺ログシリアライザ（通帳表示用）"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    # 請求書情報
    invoice_no = serializers.SerializerMethodField()
    invoice_billing_label = serializers.SerializerMethodField()
    # 入金情報
    payment_no = serializers.SerializerMethodField()
    payment_method_display = serializers.SerializerMethodField()

    class Meta:
        model = OffsetLog
        fields = [
            'id', 'guardian', 'guardian_name',
            'invoice', 'invoice_no', 'invoice_billing_label',
            'payment', 'payment_no', 'payment_method_display',
            'transaction_type', 'transaction_type_display',
            'amount', 'balance_after', 'reason',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_invoice_no(self, obj):
        return obj.invoice.invoice_no if obj.invoice else None

    def get_invoice_billing_label(self, obj):
        if obj.invoice:
            return f"{obj.invoice.billing_year}年{obj.invoice.billing_month}月分"
        return None

    def get_payment_no(self, obj):
        return obj.payment.payment_no if obj.payment else None

    def get_payment_method_display(self, obj):
        return obj.payment.get_method_display() if obj.payment else None

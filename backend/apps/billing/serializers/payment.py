"""
Payment Serializers - 入金シリアライザー
"""
from rest_framework import serializers
from apps.billing.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """入金シリアライザ"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    invoice_no = serializers.CharField(source='invoice.invoice_no', read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_no', 'guardian', 'guardian_name',
            'invoice', 'invoice_no',
            'payment_date', 'amount',
            'method', 'method_display',
            'status', 'status_display',
            'debit_result_code', 'debit_result_message',
            'payer_name', 'bank_name',
            'notes', 'registered_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'payment_no', 'registered_by',
            'created_at', 'updated_at',
        ]


class PaymentCreateSerializer(serializers.Serializer):
    """入金登録用シリアライザ"""
    guardian_id = serializers.UUIDField()
    invoice_id = serializers.UUIDField(required=False, allow_null=True)
    payment_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=0)
    method = serializers.ChoiceField(choices=Payment.Method.choices)
    payer_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bank_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class DirectDebitResultSerializer(serializers.Serializer):
    """口座振替結果取込用シリアライザ"""
    payment_id = serializers.UUIDField()
    result_code = serializers.CharField(max_length=10)
    result_message = serializers.CharField(max_length=200, required=False, allow_blank=True)

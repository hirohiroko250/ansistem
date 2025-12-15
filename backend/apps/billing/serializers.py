"""
Billing Serializers - 請求・入金・預り金・マイル管理
"""
from rest_framework import serializers
from decimal import Decimal
from .models import (
    Invoice, InvoiceLine, Payment, GuardianBalance,
    OffsetLog, RefundRequest, MileTransaction
)


# =============================================================================
# Invoice Serializers
# =============================================================================
class InvoiceLineSerializer(serializers.ModelSerializer):
    """請求明細シリアライザ"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    product_name_display = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = InvoiceLine
        fields = [
            'id', 'student', 'student_name', 'student_item', 'product', 'product_name_display',
            'item_name', 'item_type', 'description',
            'period_start', 'period_end',
            'quantity', 'unit_price', 'line_total',
            'tax_category', 'tax_rate', 'tax_amount',
            'discount_amount', 'discount_reason',
            'company_discount', 'partner_discount',
            'sort_order',
        ]
        read_only_fields = ['id', 'line_total', 'tax_amount']


class InvoiceSerializer(serializers.ModelSerializer):
    """請求書シリアライザ"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_no', 'guardian', 'guardian_name',
            'billing_year', 'billing_month',
            'issue_date', 'due_date',
            'subtotal', 'tax_amount', 'discount_total',
            'miles_used', 'miles_discount', 'total_amount',
            'paid_amount', 'balance_due',
            'carry_over_amount', 'payment_method',
            'status', 'status_display',
            'confirmed_at', 'confirmed_by',
            'is_locked', 'locked_at', 'export_batch_no',
            'notes', 'lines',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'invoice_no', 'subtotal', 'tax_amount',
            'total_amount', 'paid_amount', 'balance_due',
            'confirmed_at', 'confirmed_by',
            'is_locked', 'locked_at', 'export_batch_no',
            'created_at', 'updated_at',
        ]

    def validate(self, attrs):
        """ロック済み請求書の編集を禁止"""
        if self.instance and self.instance.is_locked:
            raise serializers.ValidationError('この請求書はエクスポート済みのため編集できません')
        return attrs


class InvoicePreviewSerializer(serializers.Serializer):
    """請求書プレビュー用シリアライザ"""
    guardian_id = serializers.UUIDField()
    billing_year = serializers.IntegerField()
    billing_month = serializers.IntegerField()
    use_miles = serializers.IntegerField(default=0, required=False)


class InvoiceConfirmSerializer(serializers.Serializer):
    """請求書確定用シリアライザ"""
    invoice_id = serializers.UUIDField()


# =============================================================================
# Payment Serializers
# =============================================================================
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


# =============================================================================
# GuardianBalance Serializers
# =============================================================================
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


# =============================================================================
# OffsetLog Serializers
# =============================================================================
class OffsetLogSerializer(serializers.ModelSerializer):
    """相殺ログシリアライザ"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = OffsetLog
        fields = [
            'id', 'guardian', 'guardian_name',
            'invoice', 'payment',
            'transaction_type', 'transaction_type_display',
            'amount', 'balance_after', 'reason',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# =============================================================================
# RefundRequest Serializers
# =============================================================================
class RefundRequestSerializer(serializers.ModelSerializer):
    """返金申請シリアライザ"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    refund_method_display = serializers.CharField(source='get_refund_method_display', read_only=True)

    class Meta:
        model = RefundRequest
        fields = [
            'id', 'request_no', 'guardian', 'guardian_name',
            'invoice', 'refund_amount', 'refund_method', 'refund_method_display',
            'reason', 'status', 'status_display',
            'requested_by', 'requested_at',
            'approved_by', 'approved_at',
            'processed_at', 'process_notes',
        ]
        read_only_fields = [
            'id', 'request_no', 'requested_by', 'requested_at',
            'approved_by', 'approved_at', 'processed_at',
        ]


class RefundRequestCreateSerializer(serializers.Serializer):
    """返金申請作成用シリアライザ"""
    guardian_id = serializers.UUIDField()
    invoice_id = serializers.UUIDField(required=False, allow_null=True)
    refund_amount = serializers.DecimalField(max_digits=12, decimal_places=0)
    refund_method = serializers.ChoiceField(choices=RefundRequest.RefundMethod.choices)
    reason = serializers.CharField()


class RefundApproveSerializer(serializers.Serializer):
    """返金申請承認用シリアライザ"""
    request_id = serializers.UUIDField()
    approve = serializers.BooleanField()
    reject_reason = serializers.CharField(required=False, allow_blank=True)


# =============================================================================
# MileTransaction Serializers
# =============================================================================
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

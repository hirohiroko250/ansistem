"""
Refund Serializers - 返金シリアライザー
"""
from rest_framework import serializers
from apps.billing.models import RefundRequest


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

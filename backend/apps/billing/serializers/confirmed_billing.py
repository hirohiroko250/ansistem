"""
Confirmed Billing Serializers - 請求確定シリアライザー
"""
from rest_framework import serializers
from apps.billing.models import ConfirmedBilling


class ConfirmedBillingSerializer(serializers.ModelSerializer):
    """請求確定シリアライザ"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    confirmed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ConfirmedBilling
        fields = [
            'id', 'student', 'student_name', 'guardian', 'guardian_name',
            'year', 'month', 'billing_deadline',
            'subtotal', 'discount_total', 'tax_amount', 'total_amount',
            'paid_amount', 'balance', 'carry_over_amount',
            'adjustment_amount', 'adjustment_note',
            'items_snapshot', 'discounts_snapshot',
            'status', 'status_display',
            'payment_method', 'payment_method_display',
            'confirmed_at', 'confirmed_by', 'confirmed_by_name',
            'paid_at', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'subtotal', 'discount_total', 'tax_amount', 'total_amount',
            'items_snapshot', 'discounts_snapshot',
            'confirmed_at', 'confirmed_by',
            'created_at', 'updated_at',
        ]

    def get_confirmed_by_name(self, obj):
        return obj.confirmed_by.full_name if obj.confirmed_by else None


class ConfirmedBillingListSerializer(serializers.ModelSerializer):
    """請求確定一覧用シリアライザ"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_no = serializers.CharField(source='student.student_no', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    guardian_no = serializers.CharField(source='guardian.guardian_no', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = ConfirmedBilling
        fields = [
            'id', 'student', 'student_name', 'student_no', 'guardian', 'guardian_name', 'guardian_no',
            'year', 'month',
            'subtotal', 'discount_total', 'total_amount', 'paid_amount', 'balance',
            'carry_over_amount', 'adjustment_amount', 'adjustment_note',
            'items_snapshot', 'discounts_snapshot',
            'status', 'status_display',
            'payment_method', 'payment_method_display',
            'confirmed_at', 'paid_at',
        ]


class ConfirmedBillingCreateSerializer(serializers.Serializer):
    """請求確定データ作成用シリアライザ"""
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    student_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text='指定しない場合は全生徒が対象'
    )


class BillingConfirmBatchSerializer(serializers.Serializer):
    """締日確定一括処理用シリアライザ"""
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    close_deadline = serializers.BooleanField(
        default=True,
        help_text='締日を締めるかどうか'
    )

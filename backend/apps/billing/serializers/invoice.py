"""
Invoice Serializers - 請求書シリアライザー
"""
from rest_framework import serializers
from apps.billing.models import Invoice, InvoiceLine, GuardianBalance


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
    # 保護者の預り金残高
    guardian_balance = serializers.SerializerMethodField()

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
            'guardian_balance',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'invoice_no', 'subtotal', 'tax_amount',
            'total_amount', 'paid_amount', 'balance_due',
            'confirmed_at', 'confirmed_by',
            'is_locked', 'locked_at', 'export_batch_no',
            'created_at', 'updated_at',
        ]

    def get_guardian_balance(self, obj):
        """保護者の預り金残高を取得"""
        try:
            balance_obj = GuardianBalance.objects.filter(guardian=obj.guardian).first()
            return int(balance_obj.balance) if balance_obj else 0
        except Exception:
            return 0

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

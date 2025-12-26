"""
Billing Serializers - 請求・入金・預り金・マイル管理
"""
from rest_framework import serializers
from decimal import Decimal
from django.db import models
from .models import (
    Invoice, InvoiceLine, Payment, GuardianBalance,
    OffsetLog, RefundRequest, MileTransaction,
    BankTransfer, BankTransferImport, ConfirmedBilling,
    MonthlyBillingDeadline
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


# =============================================================================
# BankTransfer Serializers
# =============================================================================
class BankTransferSerializer(serializers.ModelSerializer):
    """振込入金シリアライザ"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    invoice_no = serializers.CharField(source='invoice.invoice_no', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    matched_by_name = serializers.CharField(source='matched_by.full_name', read_only=True)

    # 候補保護者リスト（自動照合結果）
    candidate_guardians = serializers.SerializerMethodField()

    class Meta:
        model = BankTransfer
        fields = [
            'id', 'guardian', 'guardian_name', 'invoice', 'invoice_no',
            'transfer_date', 'amount', 'payer_name', 'payer_name_kana',
            'guardian_no_hint',
            'source_bank_name', 'source_branch_name',
            'status', 'status_display',
            'matched_by', 'matched_by_name', 'matched_at',
            'import_batch_id', 'import_row_no',
            'notes', 'candidate_guardians',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'matched_by', 'matched_at',
            'created_at', 'updated_at',
        ]

    def get_candidate_guardians(self, obj):
        """照合候補の保護者リストを取得（過去の照合履歴の完全一致のみ）"""
        if obj.status != BankTransfer.Status.PENDING:
            return []

        candidates = []
        seen_guardian_ids = set()

        # 過去の振込履歴から同じ振込人名義（完全一致）で照合実績のある保護者を取得
        payer_name = obj.payer_name.replace('　', ' ').strip() if obj.payer_name else ''
        payer_name_kana = obj.payer_name_kana.replace('　', ' ').strip() if obj.payer_name_kana else ''

        if payer_name or payer_name_kana:
            # 完全一致で検索
            query = models.Q()
            if payer_name:
                query |= models.Q(payer_name__iexact=payer_name)
            if payer_name_kana:
                query |= models.Q(payer_name_kana__iexact=payer_name_kana)

            past_transfers = BankTransfer.objects.filter(
                tenant_id=obj.tenant_id,
                status__in=[BankTransfer.Status.MATCHED, BankTransfer.Status.APPLIED],
                guardian__isnull=False,
            ).filter(query).exclude(id=obj.id).select_related('guardian').order_by('-transfer_date')[:10]

            for pt in past_transfers:
                if pt.guardian_id and str(pt.guardian_id) not in seen_guardian_ids:
                    g = pt.guardian
                    seen_guardian_ids.add(str(g.id))

                    # 請求書を取得
                    invoices = Invoice.objects.filter(
                        guardian=g,
                        status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE]
                    ).order_by('-billing_year', '-billing_month')[:3]

                    candidates.append({
                        'guardianId': str(g.id),
                        'guardianNo': g.guardian_no or '',
                        'guardianName': g.full_name,
                        'guardianNameKana': f"{g.last_name_kana or ''} {g.first_name_kana or ''}".strip(),
                        'matchSource': 'history',
                        'matchLabel': '過去の照合履歴',
                        'invoices': [{
                            'invoiceId': str(inv.id),
                            'invoiceNo': inv.invoice_no,
                            'billingLabel': f"{inv.billing_year}年{inv.billing_month}月分",
                            'totalAmount': int(inv.total_amount),
                            'balanceDue': int(inv.balance_due),
                        } for inv in invoices]
                    })

        return candidates


class BankTransferMatchSerializer(serializers.Serializer):
    """振込照合用シリアライザ"""
    transfer_id = serializers.UUIDField()
    guardian_id = serializers.UUIDField()
    invoice_id = serializers.UUIDField(required=False, allow_null=True)
    apply_payment = serializers.BooleanField(default=False)


class BankTransferBulkMatchSerializer(serializers.Serializer):
    """一括照合用シリアライザ"""
    matches = BankTransferMatchSerializer(many=True)


# =============================================================================
# BankTransferImport Serializers
# =============================================================================
class BankTransferImportSerializer(serializers.ModelSerializer):
    """振込インポートバッチシリアライザ"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    imported_by_name = serializers.CharField(source='imported_by.full_name', read_only=True)
    confirmed_by_name = serializers.CharField(source='confirmed_by.full_name', read_only=True)

    # 関連する振込データ
    transfers = serializers.SerializerMethodField()

    class Meta:
        model = BankTransferImport
        fields = [
            'id', 'batch_no', 'file_name', 'file_type',
            'total_count', 'matched_count', 'unmatched_count', 'error_count',
            'total_amount', 'status', 'status_display',
            'imported_by', 'imported_by_name', 'imported_at',
            'confirmed_by', 'confirmed_by_name', 'confirmed_at',
            'notes', 'transfers',
        ]
        read_only_fields = [
            'id', 'batch_no', 'total_count', 'matched_count',
            'unmatched_count', 'error_count', 'total_amount',
            'status', 'imported_by', 'imported_at',
            'confirmed_by', 'confirmed_at',
        ]

    def get_transfers(self, obj):
        """関連する振込データを取得"""
        transfers = BankTransfer.objects.filter(
            import_batch_id=str(obj.id)
        ).order_by('import_row_no')
        return BankTransferSerializer(transfers, many=True).data


class BankTransferImportUploadSerializer(serializers.Serializer):
    """振込データアップロード用シリアライザ"""
    file = serializers.FileField()
    date_column = serializers.CharField(default='振込日', required=False)
    amount_column = serializers.CharField(default='金額', required=False)
    payer_name_column = serializers.CharField(default='振込人名義', required=False)
    payer_name_kana_column = serializers.CharField(default='振込人名義カナ', required=False)
    bank_name_column = serializers.CharField(default='銀行名', required=False)
    branch_name_column = serializers.CharField(default='支店名', required=False)


# =============================================================================
# ConfirmedBilling Serializers
# =============================================================================
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

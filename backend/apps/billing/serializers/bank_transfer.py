"""
Bank Transfer Serializers - 振込入金シリアライザー
"""
from rest_framework import serializers
from django.db import models
from apps.billing.models import BankTransfer, BankTransferImport, Invoice


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

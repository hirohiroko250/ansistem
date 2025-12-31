"""
Mile ViewSet - マイル取引管理API
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view

from ..models import Invoice, MileTransaction
from ..serializers import (
    InvoiceSerializer, MileTransactionSerializer,
    MileCalculateSerializer, MileUseSerializer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MileTransaction ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='マイル取引一覧'),
    retrieve=extend_schema(summary='マイル取引詳細'),
)
class MileTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """マイル取引API（読み取り専用）"""
    serializer_class = MileTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MileTransaction.objects.filter(
            tenant_id=self.request.user.tenant_id
        ).select_related('guardian', 'invoice')

    @extend_schema(summary='マイル残高取得')
    @action(detail=False, methods=['get'], url_path='balance/(?P<guardian_id>[^/.]+)')
    def balance(self, request, guardian_id=None):
        """保護者のマイル残高を取得"""
        from apps.students.models import Guardian
        guardian = get_object_or_404(Guardian, id=guardian_id)

        balance = MileTransaction.get_balance(guardian)
        can_use = MileTransaction.can_use_miles(guardian)

        return Response({
            'guardian_id': str(guardian_id),
            'balance': balance,
            'can_use': can_use,
            'min_use': 4,
        })

    @extend_schema(summary='マイル割引計算', request=MileCalculateSerializer)
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """使用マイル数から割引額を計算"""
        serializer = MileCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        miles = serializer.validated_data['miles_to_use']
        discount = MileTransaction.calculate_discount(miles)

        return Response({
            'miles_to_use': miles,
            'discount_amount': discount,
        })

    @extend_schema(summary='マイル使用', request=MileUseSerializer)
    @action(detail=False, methods=['post'])
    def use(self, request):
        """マイルを使用して割引適用"""
        serializer = MileUseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.students.models import Guardian
        guardian = get_object_or_404(Guardian, id=data['guardian_id'])
        invoice = get_object_or_404(
            Invoice,
            id=data['invoice_id'],
            tenant_id=request.user.tenant_id
        )

        # マイル使用可能チェック
        if not MileTransaction.can_use_miles(guardian):
            return Response(
                {'error': 'マイルを使用するには2つ以上のコース契約が必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 残高チェック
        current_balance = MileTransaction.get_balance(guardian)
        miles_to_use = data['miles_to_use']
        if miles_to_use > current_balance:
            return Response(
                {'error': f'マイル残高が不足しています（残高: {current_balance}pt）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 割引額計算
        discount_amount = MileTransaction.calculate_discount(miles_to_use)

        with transaction.atomic():
            # マイル取引を記録
            new_balance = current_balance - miles_to_use
            mile_tx = MileTransaction.objects.create(
                tenant_id=request.user.tenant_id,
                guardian=guardian,
                invoice=invoice,
                transaction_type=MileTransaction.TransactionType.USE,
                miles=-miles_to_use,
                balance_after=new_balance,
                discount_amount=discount_amount,
                notes=f'請求書 {invoice.invoice_no} でのマイル使用',
            )

            # 請求書にマイル割引を適用
            invoice.miles_used = miles_to_use
            invoice.miles_discount = discount_amount
            invoice.calculate_totals()
            invoice.save()

        return Response({
            'miles_used': miles_to_use,
            'discount_amount': discount_amount,
            'new_balance': new_balance,
            'invoice': InvoiceSerializer(invoice).data,
        })

    @extend_schema(summary='保護者のマイル履歴')
    @action(detail=False, methods=['get'], url_path='by-guardian/(?P<guardian_id>[^/.]+)')
    def by_guardian(self, request, guardian_id=None):
        """保護者IDでマイル取引を取得"""
        transactions = self.get_queryset().filter(guardian_id=guardian_id)
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)

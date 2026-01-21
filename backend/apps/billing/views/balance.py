"""
Balance ViewSets - 預り金残高・相殺ログ管理API
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from drf_spectacular.utils import extend_schema, extend_schema_view

from ..models import (
    Invoice, Payment, GuardianBalance, OffsetLog
)
from apps.core.exceptions import ValidationException
from ..serializers import (
    GuardianBalanceSerializer, BalanceDepositSerializer, BalanceOffsetSerializer,
    OffsetLogSerializer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# GuardianBalance ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='預り金残高一覧'),
    retrieve=extend_schema(summary='預り金残高詳細'),
)
class GuardianBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """預り金残高管理API"""
    serializer_class = GuardianBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GuardianBalance.objects.filter(
            tenant_id=self.request.user.tenant_id
        ).select_related('guardian')

    @extend_schema(summary='預り金入金', request=BalanceDepositSerializer)
    @action(detail=False, methods=['post'])
    def deposit(self, request):
        """預り金に入金"""
        serializer = BalanceDepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        balance, created = GuardianBalance.objects.get_or_create(
            tenant_id=request.user.tenant_id,
            guardian_id=data['guardian_id'],
            defaults={'balance': Decimal('0')}
        )

        balance.add_balance(data['amount'], data.get('reason', ''))
        return Response(GuardianBalanceSerializer(balance).data)

    @extend_schema(summary='預り金相殺', request=BalanceOffsetSerializer)
    @action(detail=False, methods=['post'])
    def offset(self, request):
        """預り金を請求書に相殺"""
        serializer = BalanceOffsetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        balance = get_object_or_404(
            GuardianBalance,
            guardian_id=data['guardian_id'],
            tenant_id=request.user.tenant_id
        )
        invoice = get_object_or_404(
            Invoice,
            id=data['invoice_id'],
            tenant_id=request.user.tenant_id
        )

        try:
            with transaction.atomic():
                balance.use_balance(
                    data['amount'],
                    invoice=invoice,
                    reason=f'請求書 {invoice.invoice_no} への相殺'
                )

                # 相殺入金を作成
                Payment.objects.create(
                    tenant_id=request.user.tenant_id,
                    payment_no=Payment.generate_payment_no(request.user.tenant_id),
                    guardian=invoice.guardian,
                    invoice=invoice,
                    payment_date=timezone.now().date(),
                    amount=data['amount'],
                    method=Payment.Method.OFFSET,
                    status=Payment.Status.SUCCESS,
                    notes='預り金からの相殺',
                    registered_by=request.user,
                )

                # 請求書の入金額を更新
                invoice.paid_amount += data['amount']
                invoice.balance_due = invoice.total_amount - invoice.paid_amount
                if invoice.balance_due <= 0:
                    invoice.status = Invoice.Status.PAID
                elif invoice.paid_amount > 0:
                    invoice.status = Invoice.Status.PARTIAL
                invoice.save()

        except ValueError as e:
            raise ValidationException(str(e))

        return Response(GuardianBalanceSerializer(balance).data)

    @extend_schema(summary='保護者の預り金残高')
    @action(detail=False, methods=['get'], url_path='by-guardian/(?P<guardian_id>[^/.]+)')
    def by_guardian(self, request, guardian_id=None):
        """保護者IDで預り金残高を取得"""
        balance = self.get_queryset().filter(guardian_id=guardian_id).first()
        if balance:
            return Response({
                'guardian_id': str(guardian_id),
                'balance': int(balance.balance),
                'last_updated': balance.last_updated.isoformat() if balance.last_updated else None,
            })
        else:
            return Response({
                'guardian_id': str(guardian_id),
                'balance': 0,
                'last_updated': None,
            })


# =============================================================================
# OffsetLog ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='相殺ログ一覧'),
    retrieve=extend_schema(summary='相殺ログ詳細'),
)
class OffsetLogViewSet(viewsets.ReadOnlyModelViewSet):
    """相殺ログAPI（読み取り専用）"""
    serializer_class = OffsetLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OffsetLog.objects.filter(
            tenant_id=self.request.user.tenant_id
        ).select_related('guardian', 'invoice', 'payment')

    @extend_schema(summary='保護者の相殺履歴')
    @action(detail=False, methods=['get'], url_path='by-guardian/(?P<guardian_id>[^/.]+)')
    def by_guardian(self, request, guardian_id=None):
        """保護者IDで相殺ログを取得"""
        logs = self.get_queryset().filter(guardian_id=guardian_id)
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

    @extend_schema(summary='自分の通帳（入出金履歴）')
    @action(detail=False, methods=['get'], url_path='my-passbook')
    def my_passbook(self, request):
        """ログイン中の保護者の通帳（入出金履歴）を取得"""
        from apps.students.models import Guardian

        # ログインユーザーに紐づく保護者を取得
        guardian = Guardian.objects.filter(user=request.user).first()
        if not guardian:
            return Response({'detail': '保護者情報が見つかりません'}, status=404)

        # 相殺ログを取得（新しい順）
        logs = self.get_queryset().filter(guardian=guardian).order_by('-created_at')

        # 現在の残高も返す
        from apps.billing.models import GuardianBalance
        balance_obj = GuardianBalance.objects.filter(guardian=guardian).first()
        current_balance = int(balance_obj.balance) if balance_obj else 0

        serializer = self.get_serializer(logs, many=True)
        return Response({
            'guardian_id': str(guardian.id),
            'guardian_name': guardian.full_name,
            'current_balance': current_balance,
            'transactions': serializer.data
        })

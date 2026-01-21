"""
PaymentProvider ViewSet - 決済代行会社（締日設定）管理API
"""
import logging
from datetime import date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from drf_spectacular.utils import extend_schema

from ..models import PaymentProvider, BillingPeriod
from apps.core.exceptions import ValidationException

logger = logging.getLogger(__name__)


class PaymentProviderViewSet(viewsets.ModelViewSet):
    """決済代行会社管理API（締日・引落日設定含む）"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return PaymentProvider.objects.filter(
            tenant_id=tenant_id
        ).order_by('name')

    def get_serializer_class(self):
        class PaymentProviderSerializer(serializers.ModelSerializer):
            class Meta:
                model = PaymentProvider
                fields = [
                    'id', 'code', 'name', 'consignor_code',
                    'closing_day', 'debit_day',
                    'is_active', 'default_bank_code', 'file_encoding',
                ]

        return PaymentProviderSerializer

    @extend_schema(summary='現在の締日情報を取得')
    @action(detail=False, methods=['get'])
    def current_deadlines(self, request):
        """現在月の締日情報を取得"""
        import calendar

        today = date.today()
        # tenant_idフィルタを外して全プロバイダーを取得
        providers = PaymentProvider.objects.filter(is_active=True)

        deadlines = []
        for provider in providers:
            # 締日を計算
            closing_day = provider.closing_day or 25
            try:
                closing_date = date(today.year, today.month, closing_day)
            except ValueError:
                # 月末日を超える場合は月末日
                last_day = calendar.monthrange(today.year, today.month)[1]
                closing_date = date(today.year, today.month, last_day)

            # 引落日を計算
            debit_day = provider.debit_day or 27
            debit_month = today.month + 1 if today.month < 12 else 1
            debit_year = today.year if today.month < 12 else today.year + 1
            try:
                debit_date = date(debit_year, debit_month, debit_day)
            except ValueError:
                last_day = calendar.monthrange(debit_year, debit_month)[1]
                debit_date = date(debit_year, debit_month, last_day)

            # この期間が締め済みかどうか確認
            billing_period = BillingPeriod.objects.filter(
                provider=provider,
                year=today.year,
                month=today.month
            ).first()

            deadlines.append({
                'providerId': str(provider.id),
                'providerName': provider.name,
                'providerCode': provider.code,
                'closingDay': closing_day,
                'closingDate': closing_date.isoformat(),
                'closingDateDisplay': f"{today.month}月{closing_day}日",
                'debitDay': debit_day,
                'debitDate': debit_date.isoformat(),
                'debitDateDisplay': f"{debit_month}月{debit_day}日",
                'isClosed': billing_period.is_closed if billing_period else False,
                'closedAt': billing_period.closed_at.isoformat() if billing_period and billing_period.closed_at else None,
                'daysUntilClosing': (closing_date - today).days,
                'canEdit': not (billing_period and billing_period.is_closed) and closing_date >= today,
            })

        return Response({
            'today': today.isoformat(),
            'currentYear': today.year,
            'currentMonth': today.month,
            'deadlines': deadlines,
        })

    @extend_schema(summary='締日設定を更新')
    @action(detail=True, methods=['patch'])
    def update_deadline(self, request, pk=None):
        """締日・引落日の設定を更新"""
        provider = self.get_object()

        closing_day = request.data.get('closing_day')
        debit_day = request.data.get('debit_day')

        if closing_day is not None:
            if not (1 <= closing_day <= 31):
                raise ValidationException('締日は1〜31の間で設定してください')
            provider.closing_day = closing_day

        if debit_day is not None:
            if not (1 <= debit_day <= 31):
                raise ValidationException('引落日は1〜31の間で設定してください')
            provider.debit_day = debit_day

        provider.save()

        return Response({
            'success': True,
            'closing_day': provider.closing_day,
            'debit_day': provider.debit_day,
        })

    @extend_schema(summary='締日設定を新規作成')
    @action(detail=False, methods=['post'])
    def create_deadline(self, request):
        """締日・引落日の設定を新規作成（デフォルトプロバイダー）"""
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        closing_day = request.data.get('closing_day', 25)
        debit_day = request.data.get('debit_day', 27)

        if not (1 <= closing_day <= 31):
            raise ValidationException('締日は1〜31の間で設定してください')
        if not (1 <= debit_day <= 31):
            raise ValidationException('引落日は1〜31の間で設定してください')

        # デフォルトプロバイダーを作成または取得
        provider, created = PaymentProvider.objects.get_or_create(
            tenant_id=tenant_id,
            code='DEFAULT',
            defaults={
                'name': 'デフォルト',
                'closing_day': closing_day,
                'debit_day': debit_day,
                'is_active': True,
            }
        )

        if not created:
            # 既存のプロバイダーの場合は更新
            provider.closing_day = closing_day
            provider.debit_day = debit_day
            provider.save()

        return Response({
            'success': True,
            'provider_id': str(provider.id),
            'closing_day': provider.closing_day,
            'debit_day': provider.debit_day,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

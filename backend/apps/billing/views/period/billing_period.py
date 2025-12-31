"""
BillingPeriodViewSet - 請求期間管理API
"""
import logging
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from apps.billing.models import BillingPeriod, PaymentProvider

logger = logging.getLogger(__name__)


class BillingPeriodViewSet(viewsets.ModelViewSet):
    """請求期間管理API"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return BillingPeriod.objects.filter(
            tenant_id=tenant_id
        ).select_related('provider', 'closed_by').order_by('-year', '-month')

    def get_serializer_class(self):
        class BillingPeriodSerializer(serializers.ModelSerializer):
            provider_name = serializers.CharField(source='provider.name', read_only=True)
            closed_by_name = serializers.SerializerMethodField()

            class Meta:
                model = BillingPeriod
                fields = [
                    'id', 'provider', 'provider_name', 'year', 'month',
                    'closing_date', 'is_closed', 'closed_at', 'closed_by', 'closed_by_name',
                    'notes',
                ]

            def get_closed_by_name(self, obj):
                if obj.closed_by:
                    return f"{obj.closed_by.last_name}{obj.closed_by.first_name}"
                return None

        return BillingPeriodSerializer

    @extend_schema(summary='締め処理実行')
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """指定期間の締め処理を実行"""
        period = self.get_object()

        if period.is_closed:
            return Response({'error': 'この期間は既に締め処理済みです'}, status=400)

        period.is_closed = True
        period.closed_at = timezone.now()
        period.closed_by = request.user
        period.save()

        return Response({
            'success': True,
            'message': f'{period.year}年{period.month}月の締め処理が完了しました',
            'closed_at': period.closed_at.isoformat(),
        })

    @extend_schema(summary='締め解除')
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """締め処理を解除（管理者のみ）"""
        from apps.core.permissions import is_admin_user

        if not is_admin_user(request.user):
            return Response({'error': '管理者権限が必要です'}, status=403)

        period = self.get_object()

        if not period.is_closed:
            return Response({'error': 'この期間は締め処理されていません'}, status=400)

        period.is_closed = False
        period.closed_at = None
        period.closed_by = None
        period.notes = f"{period.notes}\n{timezone.now().strftime('%Y-%m-%d %H:%M')} 締め解除: {request.user.last_name}{request.user.first_name}"
        period.save()

        return Response({
            'success': True,
            'message': f'{period.year}年{period.month}月の締め処理を解除しました',
        })

    @extend_schema(summary='新規入会時の請求情報を取得')
    @action(detail=False, methods=['get'])
    def enrollment_billing_info(self, request):
        """新規入会時の請求月情報を取得

        締日を考慮して、どの月から請求できるかを返す。
        """
        from apps.billing.services.period_service import BillingPeriodService

        # 入会日（指定がなければ今日）
        enrollment_date_str = request.query_params.get('enrollment_date')
        if enrollment_date_str:
            try:
                enrollment_date = datetime.strptime(enrollment_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': '日付形式が不正です（YYYY-MM-DD）'}, status=400)
        else:
            enrollment_date = timezone.now().date()

        tenant_id = getattr(request, 'tenant_id', None)
        service = BillingPeriodService(tenant_id)

        # プロバイダー指定（指定がなければアクティブな最初のプロバイダー）
        provider_id = request.query_params.get('provider_id')
        if provider_id:
            provider = PaymentProvider.objects.filter(id=provider_id).first()
        else:
            provider = PaymentProvider.objects.filter(
                tenant_id=tenant_id,
                is_active=True
            ).first()

        billing_info = service.get_billing_info_for_new_enrollment(
            enrollment_date=enrollment_date,
            provider=provider
        )

        return Response(billing_info)

    @extend_schema(summary='チケット購入時の請求月を取得')
    @action(detail=False, methods=['get'])
    def ticket_billing_info(self, request):
        """チケット購入時の請求月を判定

        締日を考慮して、どの月の請求になるかを返す。
        """
        from apps.billing.services.period_service import BillingPeriodService

        # 購入日（指定がなければ今日）
        purchase_date_str = request.query_params.get('purchase_date')
        if purchase_date_str:
            try:
                purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': '日付形式が不正です（YYYY-MM-DD）'}, status=400)
        else:
            purchase_date = timezone.now().date()

        tenant_id = getattr(request, 'tenant_id', None)
        service = BillingPeriodService(tenant_id)

        # プロバイダー指定
        provider_id = request.query_params.get('provider_id')
        if provider_id:
            provider = PaymentProvider.objects.filter(id=provider_id).first()
        else:
            provider = PaymentProvider.objects.filter(
                tenant_id=tenant_id,
                is_active=True
            ).first()

        ticket_info = service.get_ticket_billing_month(
            purchase_date=purchase_date,
            provider=provider
        )

        return Response(ticket_info)

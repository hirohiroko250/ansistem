"""
MonthlyBillingDeadlineViewSet - 月次請求締切管理API
"""
import logging
from datetime import date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from drf_spectacular.utils import extend_schema

from apps.billing.models import MonthlyBillingDeadline, PaymentProvider
from apps.billing.services import ConfirmedBillingService
from apps.core.exceptions import ValidationException, BusinessRuleViolationError, OZAException

logger = logging.getLogger(__name__)


class MonthlyBillingDeadlineViewSet(viewsets.ModelViewSet):
    """月次請求締切管理API

    内部的な締日管理。締日を過ぎると、その月の請求データは編集不可になる。
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id
        # テナントIDが取得できない場合はデフォルトテナントを使用
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id
        if not tenant_id:
            return MonthlyBillingDeadline.objects.none()
        return MonthlyBillingDeadline.objects.filter(
            tenant_id=tenant_id
        ).order_by('-year', '-month')

    def get_serializer_class(self):
        class MonthlyBillingDeadlineSerializer(serializers.ModelSerializer):
            is_closed = serializers.SerializerMethodField()
            status = serializers.SerializerMethodField()
            status_display = serializers.SerializerMethodField()
            closing_date_display = serializers.SerializerMethodField()
            can_edit = serializers.SerializerMethodField()
            manually_closed_by_name = serializers.SerializerMethodField()
            reopened_by_name = serializers.SerializerMethodField()
            under_review_by_name = serializers.SerializerMethodField()

            class Meta:
                model = MonthlyBillingDeadline
                fields = [
                    'id', 'year', 'month', 'closing_day',
                    'auto_close', 'is_manually_closed', 'manually_closed_at',
                    'manually_closed_by', 'manually_closed_by_name',
                    'is_reopened', 'reopened_at', 'reopened_by', 'reopened_by_name',
                    'reopen_reason',
                    'is_under_review', 'under_review_at', 'under_review_by', 'under_review_by_name',
                    'notes',
                    'is_closed', 'status', 'status_display', 'closing_date_display', 'can_edit',
                ]
                read_only_fields = ['id', 'is_closed', 'status', 'status_display', 'closing_date_display', 'can_edit']

            def get_is_closed(self, obj):
                return obj.is_closed

            def get_status(self, obj):
                return obj.status

            def get_status_display(self, obj):
                return obj.status_display

            def get_closing_date_display(self, obj):
                return obj.closing_date.strftime('%Y-%m-%d')

            def get_can_edit(self, obj):
                return obj.can_edit

            def get_manually_closed_by_name(self, obj):
                if obj.manually_closed_by:
                    return f"{obj.manually_closed_by.last_name}{obj.manually_closed_by.first_name}"
                return None

            def get_reopened_by_name(self, obj):
                if obj.reopened_by:
                    return f"{obj.reopened_by.last_name}{obj.reopened_by.first_name}"
                return None

            def get_under_review_by_name(self, obj):
                if obj.under_review_by:
                    return f"{obj.under_review_by.last_name}{obj.under_review_by.first_name}"
                return None

        return MonthlyBillingDeadlineSerializer

    def _get_tenant_id(self, request):
        """テナントIDを取得（ヘルパーメソッド）"""
        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id and hasattr(request, 'user') and hasattr(request.user, 'tenant_id'):
            tenant_id = request.user.tenant_id
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id
        return tenant_id

    @extend_schema(summary='締切状態一覧を取得')
    @action(detail=False, methods=['get'])
    def status_list(self, request):
        """現在月を中心とした締切状態一覧を取得"""
        today = date.today()
        tenant_id = self._get_tenant_id(request)

        # デフォルト締日を取得（PaymentProviderから）
        default_closing_day = 25
        provider = PaymentProvider.objects.filter(
            tenant_id=tenant_id,
            is_active=True
        ).first()
        if provider:
            default_closing_day = provider.closing_day or 25

        # 請求対象月の最小値を計算（締日を基準）
        if today.day < default_closing_day:
            min_billing_month = today.month + 1
        else:
            min_billing_month = today.month + 2
        min_billing_year = today.year
        if min_billing_month > 12:
            min_billing_month -= 12
            min_billing_year += 1

        # 過去3ヶ月〜未来6ヶ月の締切状態を取得
        months = []
        first_open_found = False
        current_billing_year = None
        current_billing_month = None

        for offset in range(-3, 7):
            year = today.year
            month = today.month + offset
            while month <= 0:
                month += 12
                year -= 1
            while month > 12:
                month -= 12
                year += 1

            deadline, created = MonthlyBillingDeadline.get_or_create_for_month(
                tenant_id=tenant_id,
                year=year,
                month=month,
                closing_day=default_closing_day
            )

            # 最初の未確定月を現在の請求月とする
            is_current = False
            if not first_open_found and not deadline.is_closed:
                if (year > min_billing_year) or (year == min_billing_year and month >= min_billing_month):
                    is_current = True
                    first_open_found = True
                    current_billing_year = year
                    current_billing_month = month

            months.append({
                'id': str(deadline.id),
                'year': deadline.year,
                'month': deadline.month,
                'label': f'{deadline.year}年{deadline.month}月分',
                'closingDay': deadline.closing_day,
                'closingDate': deadline.closing_date.strftime('%Y-%m-%d'),
                'status': deadline.status,
                'statusDisplay': deadline.status_display,
                'isClosed': deadline.is_closed,
                'isUnderReview': deadline.is_under_review,
                'canEdit': deadline.can_edit,
                'isManuallyClosed': deadline.is_manually_closed,
                'isReopened': deadline.is_reopened,
                'isCurrent': is_current,
            })

        return Response({
            'currentYear': today.year,
            'currentMonth': today.month,
            'billingYear': current_billing_year,
            'billingMonth': current_billing_month,
            'defaultClosingDay': default_closing_day,
            'months': months,
        })

    @extend_schema(summary='月の編集可否をチェック')
    @action(detail=False, methods=['get'])
    def check_editable(self, request):
        """指定月が編集可能かどうかをチェック"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            raise ValidationException('year と month を指定してください')

        try:
            year = int(year)
            month = int(month)
        except ValueError:
            raise ValidationException('year と month は整数で指定してください')

        tenant_id = self._get_tenant_id(request)
        is_editable = MonthlyBillingDeadline.is_month_editable(tenant_id, year, month)

        return Response({
            'year': year,
            'month': month,
            'is_editable': is_editable,
            'message': f'{year}年{month}月分は{"編集可能" if is_editable else "締め済みのため編集不可"}です',
        })

    @extend_schema(summary='手動で締める')
    @action(detail=True, methods=['post'])
    def close_manually(self, request, pk=None):
        """指定月を手動で締める（確定データも生成）"""
        deadline = self.get_object()

        if deadline.is_closed:
            raise BusinessRuleViolationError('この月は既に締め済みです')

        notes = request.data.get('notes', '')

        try:
            result = ConfirmedBillingService.close_month(
                tenant_id=deadline.tenant_id,
                year=deadline.year,
                month=deadline.month,
                notes=notes,
                user=request.user
            )
            return Response(result)
        except ValueError as e:
            raise ValidationException(str(e))
        except Exception as e:
            logger.error(f'Error closing month: {e}')
            raise OZAException('締め処理中にエラーが発生しました', status_code=500)

    @extend_schema(summary='確認中にする')
    @action(detail=True, methods=['post'])
    def start_review(self, request, pk=None):
        """指定月を確認中にする（経理確認開始）"""
        deadline = self.get_object()

        try:
            ConfirmedBillingService.start_review(deadline, request.user)
            return Response({
                'success': True,
                'message': f'{deadline.year}年{deadline.month}月分を確認中にしました',
                'status': deadline.status,
                'status_display': deadline.status_display,
            })
        except ValueError as e:
            raise ValidationException(str(e))

    @extend_schema(summary='確認中を解除する')
    @action(detail=True, methods=['post'])
    def cancel_review(self, request, pk=None):
        """確認中を解除して通常状態に戻す"""
        deadline = self.get_object()

        try:
            ConfirmedBillingService.cancel_review(deadline, request.user)
            return Response({
                'success': True,
                'message': f'{deadline.year}年{deadline.month}月分の確認を解除しました',
                'status': deadline.status,
                'status_display': deadline.status_display,
            })
        except ValueError as e:
            raise ValidationException(str(e))

    @extend_schema(summary='締めを解除する')
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """指定月の締めを解除する（要理由）"""
        deadline = self.get_object()
        reason = request.data.get('reason', '')

        try:
            ConfirmedBillingService.reopen_month(deadline, reason, request.user)
            return Response({
                'success': True,
                'message': f'{deadline.year}年{deadline.month}月分の締めを解除しました',
                'is_closed': deadline.is_closed,
            })
        except ValueError as e:
            raise ValidationException(str(e))

    @extend_schema(summary='締日設定を更新')
    @action(detail=True, methods=['patch'])
    def update_closing_day(self, request, pk=None):
        """締日を更新"""
        deadline = self.get_object()

        closing_day = request.data.get('closing_day')
        if closing_day is None:
            raise ValidationException('closing_day を指定してください')

        if not (1 <= closing_day <= 31):
            raise ValidationException('締日は1〜31の間で設定してください')

        deadline.closing_day = closing_day
        deadline.save()

        return Response({
            'success': True,
            'closing_day': deadline.closing_day,
            'closing_date': deadline.closing_date.strftime('%Y-%m-%d'),
        })

    @extend_schema(summary='デフォルト締日を設定')
    @action(detail=False, methods=['post'])
    def set_default_closing_day(self, request):
        """デフォルト締日を設定（PaymentProviderに保存）"""
        closing_day = request.data.get('closing_day')
        if closing_day is None:
            raise ValidationException('closing_day を指定してください')

        try:
            closing_day = int(closing_day)
        except ValueError:
            raise ValidationException('closing_day は整数で指定してください')

        if not (1 <= closing_day <= 31):
            raise ValidationException('締日は1〜31の間で設定してください')

        tenant_id = self._get_tenant_id(request)

        # PaymentProviderのデフォルト締日を更新
        provider = PaymentProvider.objects.filter(
            tenant_id=tenant_id,
            is_active=True
        ).first()

        if provider:
            provider.closing_day = closing_day
            provider.save()
        else:
            # PaymentProviderがない場合は作成
            provider = PaymentProvider.objects.create(
                tenant_id=tenant_id,
                code='default',
                name='デフォルト',
                consignor_code='0000000000',
                closing_day=closing_day,
                is_active=True
            )

        return Response({
            'success': True,
            'closing_day': closing_day,
            'message': f'デフォルト締日を{closing_day}日に設定しました',
        })

"""
ConfirmedBilling ViewSet - 請求確定データ管理API
"""
from decimal import Decimal, InvalidOperation

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from apps.billing.models import ConfirmedBilling
from apps.billing.serializers import ConfirmedBillingSerializer, ConfirmedBillingListSerializer
from apps.billing.services.receipt_service import generate_receipt_response
from .mixins import BillingCreationMixin, BillingExportMixin
from apps.core.exceptions import ValidationException


def _get_tenant_id(request):
    """リクエストからテナントIDを取得"""
    tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)
    if not tenant_id:
        from apps.tenants.models import Tenant
        default_tenant = Tenant.objects.first()
        if default_tenant:
            tenant_id = default_tenant.id
    return tenant_id


@extend_schema_view(
    list=extend_schema(summary='請求確定一覧'),
    retrieve=extend_schema(summary='請求確定詳細'),
)
class ConfirmedBillingViewSet(
    BillingCreationMixin,
    BillingExportMixin,
    viewsets.ModelViewSet
):
    """請求確定データ管理API

    締日確定時に生徒ごとの請求データをスナップショットとして保存。
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.core.permissions import is_admin_user

        queryset = ConfirmedBilling.objects.filter(
            deleted_at__isnull=True
        ).select_related(
            'student', 'guardian', 'billing_deadline', 'confirmed_by'
        )

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=self.request.user.tenant_id)
        else:
            tenant_id = _get_tenant_id(self.request)
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)

        # フィルター適用
        queryset = self._apply_filters(queryset)

        return queryset.order_by('-year', '-month', '-confirmed_at')

    def _apply_filters(self, queryset):
        """クエリパラメータによるフィルター"""
        # 年月でフィルタ
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        if year:
            queryset = queryset.filter(year=int(year))
        if month:
            queryset = queryset.filter(month=int(month))

        # ステータスでフィルタ
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 保護者でフィルタ
        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(guardian_id=guardian_id)

        # 生徒でフィルタ
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        # 検索（名前・ID）
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(student__last_name__icontains=search) |
                models.Q(student__first_name__icontains=search) |
                models.Q(student__last_name_kana__icontains=search) |
                models.Q(student__first_name_kana__icontains=search) |
                models.Q(student__student_no__icontains=search) |
                models.Q(student__old_id__icontains=search) |
                models.Q(guardian__last_name__icontains=search) |
                models.Q(guardian__first_name__icontains=search) |
                models.Q(guardian__guardian_no__icontains=search) |
                models.Q(guardian__old_id__icontains=search)
            )

        # 0円の請求は除外（include_zero=trueの場合は含める）
        include_zero = self.request.query_params.get('include_zero', 'false').lower() == 'true'
        if not include_zero:
            queryset = queryset.filter(total_amount__gt=0)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ConfirmedBillingListSerializer
        return ConfirmedBillingSerializer

    @extend_schema(summary='入金を記録')
    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        """確定データに入金を記録"""
        confirmed = self.get_object()
        amount = request.data.get('amount')

        if not amount:
            raise ValidationException('金額を指定してください')

        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationException('金額の形式が不正です')

        if amount <= 0:
            raise ValidationException('金額は正の数で指定してください')

        confirmed.paid_amount += amount
        confirmed.update_payment_status()

        return Response({
            'success': True,
            'paid_amount': int(confirmed.paid_amount),
            'balance': int(confirmed.balance),
            'status': confirmed.status,
            'status_display': confirmed.get_status_display(),
        })

    @extend_schema(summary='月別サマリを取得')
    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        """指定月の請求確定サマリを取得"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            raise ValidationException('year と month を指定してください')

        tenant_id = _get_tenant_id(request)

        confirmed_billings = ConfirmedBilling.objects.filter(
            tenant_id=tenant_id,
            year=int(year),
            month=int(month),
            deleted_at__isnull=True
        )

        billings_with_amount = confirmed_billings.filter(total_amount__gt=0)

        total_count = billings_with_amount.count()
        total_amount = sum(c.total_amount for c in billings_with_amount)
        total_paid = sum(c.paid_amount for c in billings_with_amount)
        total_balance = sum(c.balance for c in billings_with_amount)

        status_counts = {}
        for status_choice in ConfirmedBilling.Status.choices:
            status_code = status_choice[0]
            count = billings_with_amount.filter(status=status_code).count()
            status_counts[status_code] = {
                'label': status_choice[1],
                'count': count,
            }

        payment_method_counts = {}
        for method_choice in ConfirmedBilling.PaymentMethod.choices:
            method_code = method_choice[0]
            filtered = billings_with_amount.filter(payment_method=method_code)
            count = filtered.count()
            amount = sum(c.total_amount for c in filtered)
            payment_method_counts[method_code] = {
                'label': method_choice[1],
                'count': count,
                'amount': int(amount),
            }

        return Response({
            'year': int(year),
            'month': int(month),
            'total_count': total_count,
            'total_amount': int(total_amount),
            'total_paid': int(total_paid),
            'total_balance': int(total_balance),
            'collection_rate': round(float(total_paid / total_amount * 100), 1) if total_amount > 0 else 0,
            'status_counts': status_counts,
            'payment_method_counts': payment_method_counts,
        })

    @extend_schema(summary='領収書PDFを生成（管理者向け）')
    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        """指定された請求確定データの領収書PDFを生成"""
        confirmed = self.get_object()

        # 入金済みでない場合は領収書発行不可
        if confirmed.status not in [ConfirmedBilling.Status.PAID, ConfirmedBilling.Status.PARTIAL]:
            return Response(
                {'error': '入金が確認されていないため領収書を発行できません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return generate_receipt_response(confirmed)

    @extend_schema(
        summary='領収書PDFを生成（保護者向け）',
        parameters=[
            OpenApiParameter(name='year', type=int, required=True, description='請求年'),
            OpenApiParameter(name='month', type=int, required=True, description='請求月'),
        ]
    )
    @action(detail=False, methods=['get'], url_path='my-receipt')
    def my_receipt(self, request):
        """保護者が自分の領収書PDFをダウンロード

        ログイン中の保護者に紐づく請求確定データの領収書を生成。
        子ども全員分の請求を合算した領収書を発行。
        """
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            return Response(
                {'error': 'year と month を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return Response(
                {'error': 'year と month は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ログイン中のユーザーに紐づくGuardianを取得
        user = request.user
        guardian = getattr(user, 'guardian', None)

        if not guardian:
            # Guardianが直接紐づいていない場合、guardian_idで検索
            from apps.students.models import Guardian
            guardian = Guardian.objects.filter(user=user).first()

        if not guardian:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = _get_tenant_id(request)

        # 該当月の請求確定データを取得
        confirmed_billings = ConfirmedBilling.objects.filter(
            tenant_id=tenant_id,
            guardian=guardian,
            year=year,
            month=month,
            deleted_at__isnull=True,
            status__in=[ConfirmedBilling.Status.PAID, ConfirmedBilling.Status.PARTIAL],
        )

        if not confirmed_billings.exists():
            return Response(
                {'error': '該当する入金済みの請求データが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 最初の請求データを使用して領収書を生成
        # 複数の子どもがいる場合でも、保護者単位で1つの領収書を発行
        confirmed = confirmed_billings.first()

        return generate_receipt_response(confirmed)

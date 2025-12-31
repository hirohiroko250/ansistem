"""
Student Item Views - 生徒商品・割引管理
StudentItemViewSet, StudentDiscountViewSet
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import models
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from apps.core.pagination import AdminResultsSetPagination
from ..models import StudentItem, StudentDiscount
from ..serializers import StudentItemSerializer, StudentDiscountSerializer


class StudentItemViewSet(CSVMixin, viewsets.ModelViewSet):
    """生徒商品（請求明細）ビューセット"""
    serializer_class = StudentItemSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = AdminResultsSetPagination

    csv_filename_prefix = 'student_items'

    def get_queryset(self):
        from apps.core.permissions import is_admin_user
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = StudentItem.objects.filter(
            deleted_at__isnull=True
        ).select_related('student', 'contract', 'product', 'brand', 'school', 'course')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        billing_month = self.request.query_params.get('billing_month')
        if billing_month:
            queryset = queryset.filter(billing_month=billing_month)

        # 年月フィルタ（billing_month形式: YYYY-MM）
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        if year:
            if month:
                # 年月両方指定: billing_month = YYYY-MM
                queryset = queryset.filter(billing_month=f"{year}-{month.zfill(2)}")
            else:
                # 年のみ指定: billing_month starts with YYYY
                queryset = queryset.filter(billing_month__startswith=year)

        contract_id = self.request.query_params.get('contract_id')
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)

        return queryset.order_by('-created_at')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def _check_billing_permission(self, instance, action='編集'):
        """請求データの編集権限をチェック

        - 確定済み: 誰も編集不可
        - 確認中: 経理・管理者のみ編集可
        - 未締め: 誰でも編集可
        - 現在または将来の請求期間: 編集可
        """
        from rest_framework.exceptions import PermissionDenied
        from apps.billing.models import MonthlyBillingDeadline
        from datetime import date

        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        # 現在の請求期間を取得
        current_year, current_month = MonthlyBillingDeadline.get_current_billing_period(tenant_id)
        current_period = (current_year, current_month)

        # start_dateがある場合は、それから正しい請求期間を計算して編集可否をチェック
        if instance.start_date:
            calc_year, calc_month = MonthlyBillingDeadline.get_billing_month_for_date(instance.start_date)
            calculated_period = (calc_year, calc_month)
            if calculated_period >= current_period:
                # 開始日ベースで現在以降の請求期間なので編集可能
                return

        # created_atがある場合もチェック（最近作成されたアイテムは編集可能）
        if hasattr(instance, 'created_at') and instance.created_at:
            created_date = instance.created_at.date() if hasattr(instance.created_at, 'date') else instance.created_at
            created_year, created_month = MonthlyBillingDeadline.get_billing_month_for_date(created_date)
            created_period = (created_year, created_month)
            if created_period >= current_period:
                # 作成日ベースで現在以降の請求期間なので編集可能
                return

        # billing_monthから請求期間を取得
        year, month = None, None
        if instance.billing_month:
            if '-' in instance.billing_month:
                parts = instance.billing_month.split('-')
                year, month = int(parts[0]), int(parts[1])
            elif len(instance.billing_month) == 6:
                year = int(instance.billing_month[:4])
                month = int(instance.billing_month[4:])

        if not year or not month:
            # billing_monthがない場合は編集可能（請求対象外の可能性）
            return

        item_period = (year, month)

        if item_period >= current_period:
            # 現在または将来の請求期間なので編集可能
            return

        # 過去の請求期間の場合は締め日チェック
        deadline = MonthlyBillingDeadline.objects.filter(
            tenant_id=tenant_id,
            year=year,
            month=month
        ).first()

        if not deadline:
            return

        # 確定済みチェック
        if deadline.is_closed:
            raise PermissionDenied(
                f"{year}年{month}月分は確定済みのため{action}できません"
            )

        # 確認中チェック
        if deadline.is_under_review:
            if not deadline.can_edit_by_user(self.request.user):
                raise PermissionDenied(
                    f"{year}年{month}月分は確認中のため、経理担当者のみ{action}できます"
                )

    def perform_update(self, serializer):
        """更新時に権限チェック"""
        instance = serializer.instance
        self._check_billing_permission(instance, '編集')
        serializer.save()

    def perform_destroy(self, instance):
        """削除時に権限チェック"""
        self._check_billing_permission(instance, '削除')
        instance.deleted_at = timezone.now()
        instance.save()


class StudentDiscountViewSet(CSVMixin, viewsets.ModelViewSet):
    """生徒割引ビューセット"""
    serializer_class = StudentDiscountSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = AdminResultsSetPagination

    csv_filename_prefix = 'student_discounts'

    def get_queryset(self):
        from apps.core.permissions import is_admin_user
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = StudentDiscount.objects.filter(
            deleted_at__isnull=True
        ).select_related('student', 'guardian', 'contract', 'brand', 'student_item')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(guardian_id=guardian_id)

        contract_id = self.request.query_params.get('contract_id')
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        # 年月フィルタ（start_dateまたはcreated_atでフィルタ）
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        if year:
            queryset = queryset.filter(
                models.Q(start_date__year=int(year)) | models.Q(created_at__year=int(year))
            )
        if month:
            queryset = queryset.filter(
                models.Q(start_date__month=int(month)) | models.Q(created_at__month=int(month))
            )

        return queryset.order_by('-created_at')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

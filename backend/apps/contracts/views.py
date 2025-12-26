"""
Contracts Views - シンプル版
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from apps.core.pagination import AdminResultsSetPagination
from .models import (
    Product, Discount, Course, CourseItem,
    Pack, PackCourse,
    Seminar, Certification,
    Contract, StudentItem, StudentDiscount, SeminarEnrollment, CertificationEnrollment,
    DiscountOperationLog
)
from .serializers import (
    ProductListSerializer, ProductDetailSerializer,
    DiscountListSerializer, DiscountDetailSerializer,
    CourseListSerializer, CourseDetailSerializer,
    PackListSerializer, PackDetailSerializer,
    SeminarListSerializer, SeminarDetailSerializer,
    CertificationListSerializer, CertificationDetailSerializer,
    StudentItemSerializer, StudentDiscountSerializer,
    ContractListSerializer, ContractDetailSerializer, ContractCreateSerializer,
    MyContractSerializer, MyStudentItemSerializer,
    SeminarEnrollmentListSerializer, SeminarEnrollmentDetailSerializer,
    CertificationEnrollmentListSerializer, CertificationEnrollmentDetailSerializer,
)


class ProductViewSet(CSVMixin, viewsets.ModelViewSet):
    """商品ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'products'
    csv_export_fields = [
        'product_code', 'product_name', 'product_name_short', 'item_type',
        'brand.brand_code', 'brand.brand_name',
        'base_price', 'tax_rate', 'is_tax_included',
        'prorate_first_month', 'is_one_time',
        'description', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'product_code': '商品コード',
        'product_name': '商品名',
        'product_name_short': '商品名略称',
        'item_type': '商品種別',
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'base_price': '基本価格',
        'tax_rate': '税率',
        'is_tax_included': '税込',
        'prorate_first_month': '初月日割り',
        'is_one_time': '一回きり',
        'description': '説明',
        'sort_order': '表示順',
        'is_active': '有効',
    }
    csv_import_mapping = {
        '商品コード': 'product_code',
        '商品名': 'product_name',
        '商品名略称': 'product_name_short',
        '商品種別': 'item_type',
        '基本価格': 'base_price',
        '税率': 'tax_rate',
        '税込': 'is_tax_included',
        '初月日割り': 'prorate_first_month',
        '一回きり': 'is_one_time',
        '説明': 'description',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['商品コード', '商品名']
    csv_unique_fields = ['product_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Product.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('brand', 'school', 'grade')

        item_type = self.request.query_params.get('item_type')
        if item_type:
            queryset = queryset.filter(item_type=item_type)

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['get'])
    def export(self, request):
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        return self.get_csv_template(request)


class DiscountViewSet(CSVMixin, viewsets.ModelViewSet):
    """割引ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'discounts'
    csv_export_fields = [
        'discount_code', 'discount_name', 'discount_type', 'calculation_type',
        'value', 'valid_from', 'valid_until', 'is_active'
    ]
    csv_export_headers = {
        'discount_code': '割引コード',
        'discount_name': '割引名',
        'discount_type': '割引種別',
        'calculation_type': '計算方法',
        'value': '割引値',
        'valid_from': '有効開始日',
        'valid_until': '有効終了日',
        'is_active': '有効',
    }
    csv_import_mapping = {
        '割引コード': 'discount_code',
        '割引名': 'discount_name',
        '割引種別': 'discount_type',
        '計算方法': 'calculation_type',
        '割引値': 'value',
        '有効開始日': 'valid_from',
        '有効終了日': 'valid_until',
        '有効': 'is_active',
    }
    csv_required_fields = ['割引コード', '割引名']
    csv_unique_fields = ['discount_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Discount.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        discount_type = self.request.query_params.get('discount_type')
        if discount_type:
            queryset = queryset.filter(discount_type=discount_type)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return DiscountListSerializer
        return DiscountDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['get'])
    def export(self, request):
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        return self.get_csv_template(request)


class CourseViewSet(CSVMixin, viewsets.ModelViewSet):
    """コースビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'courses'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Course.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('brand', 'school', 'grade').prefetch_related('course_items__product')

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()


class PackViewSet(CSVMixin, viewsets.ModelViewSet):
    """パックビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'packs'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Pack.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('brand').prefetch_related('pack_courses__course')

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return PackListSerializer
        return PackDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()


class SeminarViewSet(CSVMixin, viewsets.ModelViewSet):
    """講習ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'seminars'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Seminar.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('brand', 'grade')

        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(year=year)

        seminar_type = self.request.query_params.get('seminar_type')
        if seminar_type:
            queryset = queryset.filter(seminar_type=seminar_type)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return SeminarListSerializer
        return SeminarDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()


class CertificationViewSet(CSVMixin, viewsets.ModelViewSet):
    """検定ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'certifications'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Certification.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('brand')

        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(year=year)

        certification_type = self.request.query_params.get('certification_type')
        if certification_type:
            queryset = queryset.filter(certification_type=certification_type)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return CertificationListSerializer
        return CertificationDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()


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


class ContractViewSet(CSVMixin, viewsets.ModelViewSet):
    """契約ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    pagination_class = AdminResultsSetPagination

    csv_filename_prefix = 'contracts'
    csv_export_fields = [
        'contract_no', 'student.student_no', 'student.full_name',
        'guardian.guardian_no', 'guardian.full_name',
        'school.school_code', 'school.school_name',
        'brand.brand_code', 'brand.brand_name',
        'course.course_code', 'course.course_name',
        'status', 'contract_date', 'start_date', 'end_date',
        'monthly_total', 'notes'
    ]
    csv_export_headers = {
        'contract_no': '契約番号',
        'student.student_no': '生徒番号',
        'student.full_name': '生徒名',
        'guardian.guardian_no': '保護者番号',
        'guardian.full_name': '保護者名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'status': 'ステータス',
        'contract_date': '契約日',
        'start_date': '契約開始日',
        'end_date': '契約終了日',
        'monthly_total': '月額合計',
        'notes': '備考',
    }
    csv_import_mapping = {
        '契約番号': 'contract_no',
        'ステータス': 'status',
        '契約日': 'contract_date',
        '契約開始日': 'start_date',
        '契約終了日': 'end_date',
        '月額合計': 'monthly_total',
        '備考': 'notes',
    }
    csv_required_fields = ['契約番号', '生徒番号']
    csv_unique_fields = ['contract_no']

    def get_queryset(self):
        from apps.core.permissions import is_admin_user
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Contract.objects.filter(
            deleted_at__isnull=True
        ).select_related('student', 'guardian', 'school', 'brand', 'course')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        # 年月フィルタ（start_dateでフィルタ）
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        if year:
            queryset = queryset.filter(start_date__year=int(year))
        if month:
            queryset = queryset.filter(start_date__month=int(month))

        return queryset.order_by('-start_date', '-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            # student_idが指定されている場合は詳細版を使用（生徒詳細画面用）
            student_id = self.request.query_params.get('student_id')
            if student_id:
                return ContractListSerializer
            # それ以外は高速版を使用
            from .serializers import ContractSimpleListSerializer
            return ContractSimpleListSerializer
        elif self.action == 'create':
            return ContractCreateSerializer
        return ContractDetailSerializer

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_update(self, serializer):
        """更新時に締め済みチェック"""
        instance = serializer.instance
        if instance.start_date:
            from apps.billing.models import MonthlyBillingDeadline
            tenant_id = getattr(self.request, 'tenant_id', None)
            if not tenant_id:
                from apps.tenants.models import Tenant
                default_tenant = Tenant.objects.first()
                if default_tenant:
                    tenant_id = default_tenant.id
            if not MonthlyBillingDeadline.is_month_editable(
                tenant_id,
                instance.start_date.year,
                instance.start_date.month
            ):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(
                    f"{instance.start_date.year}年{instance.start_date.month}月分は締め済みのため編集できません"
                )
        serializer.save()

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    def get_object(self):
        """オブジェクト取得をオーバーライド

        change-class, change-school, request-suspension, request-cancellation
        アクションではStudentItem IDが使用されるため、それらのアクションでは
        get_object()を呼ばずに直接pkを返す（実際のオブジェクト取得はアクション内で行う）
        """
        # カスタムアクションの場合はNoneを返す（アクション内で独自に処理）
        if self.action in ['change_class', 'change_school', 'request_suspension', 'request_cancellation']:
            return None
        # 通常のCRUD操作の場合は親クラスのget_objectを呼ぶ
        return super().get_object()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """契約有効化"""
        contract = self.get_object()
        contract.status = Contract.Status.ACTIVE
        contract.save()
        return Response(ContractDetailSerializer(contract).data)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """契約休止"""
        contract = self.get_object()
        contract.status = Contract.Status.PAUSED
        contract.save()
        return Response(ContractDetailSerializer(contract).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """契約解約"""
        contract = self.get_object()
        contract.status = Contract.Status.CANCELLED
        contract.end_date = request.data.get('end_date', timezone.now().date())
        contract.save()
        return Response(ContractDetailSerializer(contract).data)

    @action(detail=True, methods=['post'], url_path='update-textbooks')
    def update_textbooks(self, request, pk=None):
        """契約の選択教材を更新

        Request body:
        {
            "selected_textbook_ids": ["product-uuid-1", "product-uuid-2"]
        }
        """
        contract = self.get_object()
        textbook_ids = request.data.get('selected_textbook_ids', [])

        # 教材商品のみ許可（item_type=textbook）
        from .models import Product
        valid_textbooks = Product.objects.filter(
            id__in=textbook_ids,
            item_type=Product.ItemType.TEXTBOOK
        )

        # 選択教材を更新
        contract.selected_textbooks.set(valid_textbooks)

        # monthly_totalを再計算
        self._recalculate_monthly_total(contract)

        return Response({
            'success': True,
            'selected_textbook_ids': [str(p.id) for p in contract.selected_textbooks.all()]
        })

    def _recalculate_monthly_total(self, contract):
        """月額合計を再計算（選択教材のみ含む）"""
        if not contract.course:
            return

        from .models import Product
        from decimal import Decimal

        total = Decimal('0')
        selected_textbook_ids = set(contract.selected_textbooks.values_list('id', flat=True))

        for ci in contract.course.course_items.filter(is_active=True):
            if not ci.product:
                continue

            # 教材費の場合は選択されているもののみ
            if ci.product.item_type == Product.ItemType.TEXTBOOK:
                if ci.product_id not in selected_textbook_ids:
                    continue

            total += ci.get_price() * ci.quantity

        contract.monthly_total = total
        contract.save()

    @action(detail=True, methods=['get', 'post'])
    def items(self, request, pk=None):
        """契約の生徒商品一覧/追加"""
        contract = self.get_object()

        if request.method == 'GET':
            items = contract.student_items.all()
            serializer = StudentItemSerializer(items, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = StudentItemSerializer(data={
                **request.data,
                'contract': contract.id,
                'student': contract.student_id
            })
            serializer.is_valid(raise_exception=True)
            serializer.save(tenant_id=request.tenant_id, contract=contract, student=contract.student)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='update-discounts')
    def update_discounts(self, request, pk=None):
        """契約の割引を更新（明細単位の割引に対応）

        Request body:
        {
            "item_discounts": [
                {
                    "id": "existing-uuid",  // 既存の割引（更新用）
                    "student_item_id": "item-uuid",  // 明細ID（optional）
                    "discount_name": "社割_正社員",
                    "amount": 1990,
                    "discount_unit": "yen",
                    "is_deleted": false  // trueの場合は削除
                },
                {
                    "student_item_id": "item-uuid",  // 明細ID（optional）
                    "discount_name": "マイル割引",  // idなしは新規作成
                    "amount": 500,
                    "discount_unit": "yen",
                    "is_new": true
                }
            ],
            "notes": "契約メモ"
        }
        """
        contract = Contract.objects.filter(
            pk=pk,
            deleted_at__isnull=True
        ).select_related('student', 'brand', 'school', 'course').first()

        if not contract:
            return Response(
                {'error': '契約が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = request.tenant_id
        user = request.user
        # item_discounts を優先、後方互換性のため discounts もサポート
        discounts_data = request.data.get('item_discounts', request.data.get('discounts', []))
        notes = request.data.get('notes')

        # 割引Max取得（契約に紐づくコースまたは商品から）
        discount_max = 0
        if contract.course:
            # コースの商品から割引Maxを取得
            course_items = contract.course.course_items.filter(is_active=True).select_related('product')
            for ci in course_items:
                if ci.product and ci.product.discount_max:
                    discount_max = max(discount_max, ci.product.discount_max)
        # StudentItemから商品の割引Maxも確認
        student_items = StudentItem.objects.filter(
            student_id=contract.student_id,
            contract_id=contract.id
        ).select_related('product')
        for si in student_items:
            if si.product and si.product.discount_max:
                discount_max = max(discount_max, si.product.discount_max)

        # 操作前の合計割引額を計算
        existing_discounts = StudentDiscount.objects.filter(
            student_id=contract.student_id,
            is_active=True,
        ).filter(
            models.Q(brand_id__isnull=True) | models.Q(brand_id=contract.brand_id)
        )
        total_discount_before = sum(d.amount or 0 for d in existing_discounts)

        # 備考を更新
        if notes is not None:
            contract.notes = notes
            contract.save(update_fields=['notes', 'updated_at'])

        created_count = 0
        updated_count = 0
        deleted_count = 0
        operation_logs = []

        # IPアドレス取得
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')

        for discount_data in discounts_data:
            discount_id = discount_data.get('id')
            is_deleted = discount_data.get('is_deleted', False)
            is_new = discount_data.get('is_new', False)
            discount_name = discount_data.get('discount_name', '')
            discount_amount = discount_data.get('amount', 0)
            discount_unit = discount_data.get('discount_unit', 'yen')
            student_item_id = discount_data.get('student_item_id')
            # "default" は明細がない場合のデフォルト値なので None に変換
            if student_item_id == 'default':
                student_item_id = None

            if is_deleted and discount_id and not discount_id.startswith('new-'):
                # 既存の割引を削除（soft delete）
                old_discount = StudentDiscount.objects.filter(id=discount_id, tenant_id=tenant_id).first()
                if old_discount:
                    old_amount = old_discount.amount or 0
                    StudentDiscount.objects.filter(id=discount_id, tenant_id=tenant_id).update(is_active=False)
                    deleted_count += 1

                    # 操作ログを記録
                    total_after = total_discount_before - old_amount
                    log = DiscountOperationLog.log_operation(
                        contract=contract,
                        operation_type='delete',
                        discount_name=old_discount.discount_name,
                        discount_amount=old_amount,
                        discount_unit=old_discount.discount_unit,
                        discount_max=discount_max,
                        total_before=total_discount_before,
                        total_after=total_after,
                        user=user,
                        school=contract.school,
                        brand=contract.brand,
                        student_discount=old_discount,
                        ip_address=ip_address,
                        notes=f'割引削除: {old_discount.discount_name}'
                    )
                    operation_logs.append(log)
                    total_discount_before = total_after

            elif is_new or (discount_id and discount_id.startswith('new-')):
                # 新規割引を作成
                new_discount = StudentDiscount.objects.create(
                    tenant_id=tenant_id,
                    student_id=contract.student_id,
                    contract_id=contract.id,
                    student_item_id=student_item_id,  # 明細IDを保存
                    brand_id=contract.brand_id,
                    discount_name=discount_name,
                    amount=discount_amount,
                    discount_unit=discount_unit,
                    is_active=True,
                    is_recurring=True,
                )
                created_count += 1

                # 操作ログを記録
                total_after = total_discount_before + discount_amount
                log = DiscountOperationLog.log_operation(
                    contract=contract,
                    operation_type='add',
                    discount_name=discount_name,
                    discount_amount=discount_amount,
                    discount_unit=discount_unit,
                    discount_max=discount_max,
                    total_before=total_discount_before,
                    total_after=total_after,
                    user=user,
                    school=contract.school,
                    brand=contract.brand,
                    student_discount=new_discount,
                    ip_address=ip_address,
                    notes=f'割引追加: {discount_name}'
                )
                operation_logs.append(log)
                total_discount_before = total_after

            elif discount_id:
                # 既存の割引を更新
                old_discount = StudentDiscount.objects.filter(id=discount_id, tenant_id=tenant_id).first()
                if old_discount:
                    old_amount = old_discount.amount or 0
                    StudentDiscount.objects.filter(id=discount_id, tenant_id=tenant_id).update(
                        discount_name=discount_name,
                        amount=discount_amount,
                        discount_unit=discount_unit,
                    )
                    updated_count += 1

                    # 操作ログを記録
                    amount_diff = discount_amount - old_amount
                    total_after = total_discount_before + amount_diff
                    log = DiscountOperationLog.log_operation(
                        contract=contract,
                        operation_type='update',
                        discount_name=discount_name,
                        discount_amount=discount_amount,
                        discount_unit=discount_unit,
                        discount_max=discount_max,
                        total_before=total_discount_before,
                        total_after=total_after,
                        user=user,
                        school=contract.school,
                        brand=contract.brand,
                        student_discount=old_discount,
                        ip_address=ip_address,
                        notes=f'割引変更: {old_discount.discount_name} → {discount_name} ({old_amount}→{discount_amount})'
                    )
                    operation_logs.append(log)
                    total_discount_before = total_after

        # 操作ログの情報を返す
        logs_data = [{
            'id': str(log.id),
            'operation_type': log.operation_type,
            'discount_name': log.discount_name,
            'discount_amount': log.discount_amount,
            'discount_max': log.discount_max,
            'total_discount_after': log.total_discount_after,
            'excess_amount': log.excess_amount,
            'operated_by_name': log.operated_by_name,
            'created_at': log.created_at.isoformat(),
        } for log in operation_logs]

        return Response({
            'success': True,
            'created': created_count,
            'updated': updated_count,
            'deleted': deleted_count,
            'discount_max': discount_max,
            'operation_logs': logs_data,
            'contract': ContractDetailSerializer(contract).data
        })

    @action(detail=True, methods=['get'], url_path='discount-logs')
    def discount_logs(self, request, pk=None):
        """契約の割引操作履歴を取得"""
        contract = Contract.objects.filter(
            pk=pk,
            deleted_at__isnull=True
        ).first()

        if not contract:
            return Response(
                {'error': '契約が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        logs = DiscountOperationLog.objects.filter(
            contract_id=contract.id
        ).select_related('operated_by', 'school').order_by('-created_at')[:50]

        logs_data = [{
            'id': str(log.id),
            'operation_type': log.operation_type,
            'operation_type_display': log.get_operation_type_display(),
            'discount_name': log.discount_name,
            'discount_amount': log.discount_amount,
            'discount_unit': log.discount_unit,
            'discount_max': log.discount_max,
            'total_discount_before': log.total_discount_before,
            'total_discount_after': log.total_discount_after,
            'excess_amount': log.excess_amount,
            'school_name': log.school.school_name if log.school else '',
            'operated_by_name': log.operated_by_name,
            'notes': log.notes,
            'created_at': log.created_at.isoformat(),
        } for log in logs]

        return Response({
            'logs': logs_data,
            'total_count': len(logs_data)
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """契約統計"""
        queryset = self.get_queryset()
        stats = {
            'total': queryset.count(),
            'by_status': {},
            'monthly_revenue': queryset.filter(
                status=Contract.Status.ACTIVE
            ).aggregate(total=Sum('monthly_total'))['total'] or 0
        }

        for status_choice in Contract.Status.choices:
            stats['by_status'][status_choice[0]] = queryset.filter(
                status=status_choice[0]
            ).count()

        return Response(stats)

    @action(detail=False, methods=['get'], url_path='my-contracts', permission_classes=[IsAuthenticated])
    def my_contracts(self, request):
        """顧客用：ログインユーザーの子どもの受講コース一覧

        保護者としてログインしている場合、その保護者に紐づく生徒の受講中コース（StudentItem）を返す
        ContractモデルではなくStudentItemモデルをベースにデータを取得
        """
        from apps.students.models import Student, Guardian, StudentGuardian

        user = request.user
        request_tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得（tenant_idがNoneの場合はtenant_id条件なしで検索）
        try:
            if request_tenant_id:
                guardian = Guardian.objects.get(user=user, tenant_id=request_tenant_id, deleted_at__isnull=True)
            else:
                guardian = Guardian.objects.filter(user=user, deleted_at__isnull=True).first()
                if not guardian:
                    raise Guardian.DoesNotExist()
        except Guardian.DoesNotExist:
            return Response({'contracts': [], 'students': []})

        # Guardianが見つかったらそのtenant_idを使用
        tenant_id = guardian.tenant_id

        # 保護者に紐づく生徒を取得
        # 1. StudentGuardian中間テーブル経由
        student_ids_from_sg = set(StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id
        ).values_list('student_id', flat=True))

        # 2. Student.guardian直接参照（主保護者）
        student_ids_from_direct = set(Student.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).values_list('id', flat=True))

        # 両方を統合
        all_student_ids = student_ids_from_sg | student_ids_from_direct

        students = Student.objects.filter(
            id__in=all_student_ids,
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        # 生徒のStudentItem（受講コース）を取得
        # course, brandのいずれかが設定されているものを対象とする
        from django.db.models import Q
        student_items = StudentItem.objects.filter(
            student__in=students,
            tenant_id=tenant_id,
            deleted_at__isnull=True,
        ).filter(
            Q(course__isnull=False) | Q(brand__isnull=False)
        ).select_related(
            'student', 'student__grade',
            'school', 'brand', 'course'
        ).order_by('student__last_name', 'student__first_name', '-created_at')

        # 重複を排除（同じ生徒・コース・校舎の組み合わせは1つにまとめる）
        seen = set()
        unique_items = []
        for item in student_items:
            key = (item.student_id, item.course_id, item.school_id)
            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        from apps.students.serializers import StudentListSerializer

        return Response({
            'students': StudentListSerializer(students, many=True).data,
            'contracts': MyStudentItemSerializer(unique_items, many=True).data
        })

    @action(detail=True, methods=['post'], url_path='change-class', permission_classes=[IsAuthenticated])
    def change_class(self, request, pk=None):
        """クラス変更（曜日・時間変更）

        翌週から適用。空席があれば即時OK
        my_contractsが返すStudentItemのIDを使って処理
        """
        from apps.schools.models import ClassSchedule
        from datetime import timedelta
        from apps.students.models import Guardian, StudentGuardian

        # StudentItemを取得（my_contractsはStudentItemを返すため）
        user = request.user
        request_tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得
        try:
            if request_tenant_id:
                guardian = Guardian.objects.get(user=user, tenant_id=request_tenant_id, deleted_at__isnull=True)
            else:
                guardian = Guardian.objects.filter(user=user, deleted_at__isnull=True).first()
                if not guardian:
                    raise Guardian.DoesNotExist()
        except Guardian.DoesNotExist:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = guardian.tenant_id

        # 保護者に紐づく生徒を取得
        student_ids = StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id
        ).values_list('student_id', flat=True)

        # StudentItemを取得（自分の子供のものか確認）
        try:
            student_item = StudentItem.objects.get(
                id=pk,
                student_id__in=student_ids,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except StudentItem.DoesNotExist:
            return Response(
                {'error': '指定された受講情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # リクエストデータ
        new_day_of_week = request.data.get('new_day_of_week')
        new_start_time = request.data.get('new_start_time')
        new_class_schedule_id = request.data.get('new_class_schedule_id')

        if not all([new_day_of_week is not None, new_start_time, new_class_schedule_id]):
            return Response(
                {'error': '曜日、開始時間、クラススケジュールIDは必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # クラススケジュールを取得して検証
        try:
            class_schedule = ClassSchedule.objects.get(
                id=new_class_schedule_id,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except ClassSchedule.DoesNotExist:
            return Response(
                {'error': '指定されたクラススケジュールが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 同じ校舎かチェック
        if class_schedule.school_id != student_item.school_id:
            return Response(
                {'error': '校舎が異なります。校舎変更は別のAPIをご利用ください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # TODO: 空席確認のロジック（将来実装）
        # 今は常にOKとする

        # 翌週の開始日を計算
        today = timezone.now().date()
        days_until_next_week = 7 - today.weekday()  # 次の月曜日まで
        next_monday = today + timedelta(days=days_until_next_week)
        effective_date = request.data.get('effective_date', next_monday.isoformat())

        # StudentItemを更新
        student_item.day_of_week = int(new_day_of_week)
        student_item.start_time = new_start_time
        if hasattr(class_schedule, 'end_time'):
            student_item.end_time = class_schedule.end_time
        student_item.save()

        # StudentEnrollment（受講履歴）を作成
        # クラス変更の履歴として新しいレコードを作成
        from apps.students.models import StudentEnrollment
        from datetime import datetime

        # effective_dateをdate型に変換
        if isinstance(effective_date, str):
            effective_date_obj = datetime.strptime(effective_date, '%Y-%m-%d').date()
        else:
            effective_date_obj = effective_date

        if student_item.school and student_item.brand:
            StudentEnrollment.create_enrollment(
                student=student_item.student,
                school=student_item.school,
                brand=student_item.brand,
                class_schedule=class_schedule,
                change_type=StudentEnrollment.ChangeType.CLASS_CHANGE,
                effective_date=effective_date_obj,
                student_item=student_item,
                notes=f'クラス変更: {class_schedule}',
            )

        return Response({
            'success': True,
            'message': f'{effective_date}からクラスが変更されます',
            'contract': MyStudentItemSerializer(student_item).data,
            'effective_date': effective_date
        })

    @action(detail=True, methods=['post'], url_path='change-school', permission_classes=[IsAuthenticated])
    def change_school(self, request, pk=None):
        """校舎変更

        翌週から適用
        my_contractsが返すStudentItemのIDを使って処理
        """
        from apps.schools.models import School, ClassSchedule
        from datetime import timedelta
        from apps.students.models import Guardian, StudentGuardian

        # StudentItemを取得（my_contractsはStudentItemを返すため）
        user = request.user
        request_tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得
        try:
            if request_tenant_id:
                guardian = Guardian.objects.get(user=user, tenant_id=request_tenant_id, deleted_at__isnull=True)
            else:
                guardian = Guardian.objects.filter(user=user, deleted_at__isnull=True).first()
                if not guardian:
                    raise Guardian.DoesNotExist()
        except Guardian.DoesNotExist:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = guardian.tenant_id

        # 保護者に紐づく生徒を取得
        student_ids = StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id
        ).values_list('student_id', flat=True)

        # StudentItemを取得（自分の子供のものか確認）
        try:
            student_item = StudentItem.objects.get(
                id=pk,
                student_id__in=student_ids,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except StudentItem.DoesNotExist:
            return Response(
                {'error': '指定された受講情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # リクエストデータ
        new_school_id = request.data.get('new_school_id')
        new_day_of_week = request.data.get('new_day_of_week')
        new_start_time = request.data.get('new_start_time')
        new_class_schedule_id = request.data.get('new_class_schedule_id')

        if not all([new_school_id, new_day_of_week is not None, new_start_time]):
            return Response(
                {'error': '校舎ID、曜日、開始時間は必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 校舎を取得して検証
        try:
            new_school = School.objects.get(
                id=new_school_id,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except School.DoesNotExist:
            return Response(
                {'error': '指定された校舎が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 翌週の開始日を計算
        today = timezone.now().date()
        days_until_next_week = 7 - today.weekday()
        next_monday = today + timedelta(days=days_until_next_week)
        effective_date = request.data.get('effective_date', next_monday.isoformat())

        # StudentItemを更新
        student_item.school = new_school
        student_item.day_of_week = int(new_day_of_week)
        student_item.start_time = new_start_time
        student_item.save()

        return Response({
            'success': True,
            'message': f'{effective_date}から校舎が{new_school.school_name}に変更されます',
            'contract': MyStudentItemSerializer(student_item).data,
            'effective_date': effective_date
        })

    @action(detail=True, methods=['post'], url_path='request-suspension', permission_classes=[IsAuthenticated])
    def request_suspension(self, request, pk=None):
        """休会申請

        保護者からの休会申請を受け付ける
        my_contractsが返すStudentItemのIDを使って処理
        """
        from .models import ContractChangeRequest
        from datetime import datetime
        from apps.students.models import Guardian, StudentGuardian

        # StudentItemを取得（my_contractsはStudentItemを返すため）
        user = request.user
        request_tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得
        try:
            if request_tenant_id:
                guardian = Guardian.objects.get(user=user, tenant_id=request_tenant_id, deleted_at__isnull=True)
            else:
                guardian = Guardian.objects.filter(user=user, deleted_at__isnull=True).first()
                if not guardian:
                    raise Guardian.DoesNotExist()
        except Guardian.DoesNotExist:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = guardian.tenant_id

        # 保護者に紐づく生徒を取得
        student_ids = StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id
        ).values_list('student_id', flat=True)

        # StudentItemを取得（自分の子供のものか確認）
        try:
            student_item = StudentItem.objects.get(
                id=pk,
                student_id__in=student_ids,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except StudentItem.DoesNotExist:
            return Response(
                {'error': '指定された受講情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # StudentItemに関連するContractを取得
        contract = student_item.contract
        if not contract:
            return Response(
                {'error': 'この受講情報には契約が紐づいていないため、休会申請できません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # リクエストデータ
        suspend_from = request.data.get('suspend_from')
        suspend_until = request.data.get('suspend_until')
        keep_seat = request.data.get('keep_seat', False)
        reason = request.data.get('reason', '')

        if not suspend_from:
            return Response(
                {'error': '休会開始日は必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 既存の申請中をチェック
        existing = ContractChangeRequest.objects.filter(
            tenant_id=tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.SUSPENSION,
            status=ContractChangeRequest.Status.PENDING
        ).exists()

        if existing:
            return Response(
                {'error': 'すでに申請中の休会申請があります'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 申請を作成
        change_request = ContractChangeRequest.objects.create(
            tenant_id=tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.SUSPENSION,
            status=ContractChangeRequest.Status.PENDING,
            suspend_from=suspend_from,
            suspend_until=suspend_until if suspend_until else None,
            keep_seat=keep_seat,
            reason=reason,
            requested_by=request.user
        )

        seat_fee_message = ''
        if keep_seat:
            seat_fee_message = '座席保持料（月額800円）が発生します。'

        return Response({
            'success': True,
            'message': f'休会申請を受け付けました。{seat_fee_message}スタッフの承認後に確定します。',
            'request_id': str(change_request.id),
            'suspend_from': suspend_from,
            'suspend_until': suspend_until,
            'keep_seat': keep_seat
        })

    @action(detail=True, methods=['post'], url_path='request-cancellation', permission_classes=[IsAuthenticated])
    def request_cancellation(self, request, pk=None):
        """退会申請

        保護者からの退会申請を受け付ける
        my_contractsが返すStudentItemのIDを使って処理
        """
        from .models import ContractChangeRequest
        from datetime import datetime, date
        from decimal import Decimal
        from apps.students.models import Guardian, StudentGuardian

        # StudentItemを取得（my_contractsはStudentItemを返すため）
        user = request.user
        request_tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得
        try:
            if request_tenant_id:
                guardian = Guardian.objects.get(user=user, tenant_id=request_tenant_id, deleted_at__isnull=True)
            else:
                guardian = Guardian.objects.filter(user=user, deleted_at__isnull=True).first()
                if not guardian:
                    raise Guardian.DoesNotExist()
        except Guardian.DoesNotExist:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = guardian.tenant_id

        # 保護者に紐づく生徒を取得
        student_ids = StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id
        ).values_list('student_id', flat=True)

        # StudentItemを取得（自分の子供のものか確認）
        try:
            student_item = StudentItem.objects.get(
                id=pk,
                student_id__in=student_ids,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except StudentItem.DoesNotExist:
            return Response(
                {'error': '指定された受講情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # StudentItemに関連するContractを取得
        contract = student_item.contract
        if not contract:
            return Response(
                {'error': 'この受講情報には契約が紐づいていないため、退会申請できません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # リクエストデータ
        cancel_date = request.data.get('cancel_date')
        reason = request.data.get('reason', '')

        if not cancel_date:
            return Response(
                {'error': '退会日は必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 既存の申請中をチェック
        existing = ContractChangeRequest.objects.filter(
            tenant_id=tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.CANCELLATION,
            status=ContractChangeRequest.Status.PENDING
        ).exists()

        if existing:
            return Response(
                {'error': 'すでに申請中の退会申請があります'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 相殺金額を計算（当月退会の場合）
        cancel_date_obj = datetime.strptime(cancel_date, '%Y-%m-%d').date()
        today = date.today()
        refund_amount = None

        if cancel_date_obj.year == today.year and cancel_date_obj.month == today.month:
            # 当月退会の場合、日割り計算の目安を表示
            days_in_month = 30
            remaining_days = days_in_month - cancel_date_obj.day
            monthly_fee = getattr(contract, 'monthly_fee', None) or Decimal('0')
            refund_amount = (monthly_fee / days_in_month * remaining_days).quantize(Decimal('1'))

        # 申請を作成
        change_request = ContractChangeRequest.objects.create(
            tenant_id=tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.CANCELLATION,
            status=ContractChangeRequest.Status.PENDING,
            cancel_date=cancel_date,
            refund_amount=refund_amount,
            reason=reason,
            requested_by=request.user
        )

        refund_message = ''
        if refund_amount:
            refund_message = f'相殺金額（目安）: {refund_amount:,}円'

        return Response({
            'success': True,
            'message': f'退会申請を受け付けました。{refund_message}スタッフの承認後に確定します。',
            'request_id': str(change_request.id),
            'cancel_date': cancel_date,
            'refund_amount': str(refund_amount) if refund_amount else None
        })

    @action(detail=False, methods=['get'])
    def export(self, request):
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        return self.get_csv_template(request)


class SeminarEnrollmentViewSet(CSVMixin, viewsets.ModelViewSet):
    """講習申込ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'seminar_enrollments'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = SeminarEnrollment.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'seminar')

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        seminar_id = self.request.query_params.get('seminar_id')
        if seminar_id:
            queryset = queryset.filter(seminar_id=seminar_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return SeminarEnrollmentListSerializer
        return SeminarEnrollmentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """申込確定"""
        enrollment = self.get_object()
        enrollment.status = SeminarEnrollment.Status.CONFIRMED
        enrollment.save()
        return Response(SeminarEnrollmentDetailSerializer(enrollment).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """申込キャンセル"""
        enrollment = self.get_object()
        enrollment.status = SeminarEnrollment.Status.CANCELLED
        enrollment.save()
        return Response(SeminarEnrollmentDetailSerializer(enrollment).data)


class CertificationEnrollmentViewSet(CSVMixin, viewsets.ModelViewSet):
    """検定申込ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'certification_enrollments'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = CertificationEnrollment.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'certification')

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        certification_id = self.request.query_params.get('certification_id')
        if certification_id:
            queryset = queryset.filter(certification_id=certification_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return CertificationEnrollmentListSerializer
        return CertificationEnrollmentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """申込確定"""
        enrollment = self.get_object()
        enrollment.status = CertificationEnrollment.Status.CONFIRMED
        enrollment.save()
        return Response(CertificationEnrollmentDetailSerializer(enrollment).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """申込キャンセル"""
        enrollment = self.get_object()
        enrollment.status = CertificationEnrollment.Status.CANCELLED
        enrollment.save()
        return Response(CertificationEnrollmentDetailSerializer(enrollment).data)

    @action(detail=True, methods=['post'])
    def record_result(self, request, pk=None):
        """結果記録"""
        enrollment = self.get_object()
        result = request.data.get('result')  # 'passed' or 'failed'
        score = request.data.get('score')

        if result == 'passed':
            enrollment.status = CertificationEnrollment.Status.PASSED
        elif result == 'failed':
            enrollment.status = CertificationEnrollment.Status.FAILED

        if score is not None:
            enrollment.score = score

        enrollment.save()
        return Response(CertificationEnrollmentDetailSerializer(enrollment).data)


# =============================================================================
# 公開API（認証不要・顧客向け）
# =============================================================================
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .serializers import PublicCourseSerializer, PublicPackSerializer, PublicBrandSerializer


class PublicBrandListView(APIView):
    """公開ブランド一覧API（認証不要・顧客向け）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        有効なブランド一覧を返す
        コース/パック購入時のブランド選択用
        """
        from apps.schools.models import Brand

        queryset = Brand.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).select_related('category').order_by('category__sort_order', 'sort_order', 'brand_name')

        serializer = PublicBrandSerializer(queryset, many=True)
        return Response(serializer.data)


class PublicCourseListView(APIView):
    """公開コース一覧API（認証不要・顧客向け）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        有効なコース一覧を返す
        ?brand_id=xxx でブランドフィルタリング（UUIDまたはブランドコード）
        ?school_id=xxx で校舎フィルタリング（UUIDまたは校舎コード）
        ?grade_name=xxx で学年フィルタリング
        """
        queryset = Course.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).select_related('brand', 'school', 'grade').prefetch_related('course_items__product', 'course_tickets__ticket')

        # ブランドでフィルタリング（UUIDまたはブランドコード）
        brand_id = request.query_params.get('brand_id')
        if brand_id:
            # UUIDかブランドコードかを判定
            try:
                import uuid
                uuid.UUID(brand_id)
                queryset = queryset.filter(brand_id=brand_id)
            except ValueError:
                # ブランドコードとして処理
                queryset = queryset.filter(brand__brand_code=brand_id)

        # 校舎でフィルタリング（UUIDまたは校舎コード）
        # school_id=NULLのコース（ブランド全体で利用可能）も含める
        school_id = request.query_params.get('school_id')
        if school_id:
            from django.db.models import Q
            try:
                import uuid
                uuid.UUID(school_id)
                queryset = queryset.filter(Q(school_id=school_id) | Q(school_id__isnull=True))
            except ValueError:
                # 校舎コードとして処理
                queryset = queryset.filter(Q(school__school_code=school_id) | Q(school_id__isnull=True))

        # 学年でフィルタリング
        grade_name = request.query_params.get('grade_name')
        if grade_name:
            queryset = queryset.filter(grade__grade_name__icontains=grade_name)

        queryset = queryset.order_by('sort_order', 'course_name')
        serializer = PublicCourseSerializer(queryset, many=True)
        return Response(serializer.data)


class PublicCourseDetailView(APIView):
    """公開コース詳細API（認証不要・顧客向け）"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        """コース詳細を返す"""
        try:
            course = Course.objects.select_related(
                'brand', 'school', 'grade'
            ).prefetch_related('course_items__product', 'course_tickets__ticket').get(
                id=pk,
                is_active=True,
                deleted_at__isnull=True
            )
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PublicCourseSerializer(course)
        return Response(serializer.data)


class PublicPackListView(APIView):
    """公開パック一覧API（認証不要・顧客向け）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        有効なパック一覧を返す
        ?brand_id=xxx でブランドフィルタリング（UUIDまたはブランドコード）
        ?school_id=xxx で校舎フィルタリング（UUIDまたは校舎コード）
        ?grade_name=xxx で学年フィルタリング
        """
        queryset = Pack.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).select_related('brand', 'school', 'grade').prefetch_related('pack_courses__course', 'pack_tickets__ticket')

        # ブランドでフィルタリング（UUIDまたはブランドコード）
        brand_id = request.query_params.get('brand_id')
        if brand_id:
            try:
                import uuid
                uuid.UUID(brand_id)
                queryset = queryset.filter(brand_id=brand_id)
            except ValueError:
                # ブランドコードとして処理
                queryset = queryset.filter(brand__brand_code=brand_id)

        # 校舎でフィルタリング（UUIDまたは校舎コード）
        # school_id=NULLのパック（ブランド全体で利用可能）も含める
        school_id = request.query_params.get('school_id')
        if school_id:
            from django.db.models import Q
            try:
                import uuid
                uuid.UUID(school_id)
                queryset = queryset.filter(Q(school_id=school_id) | Q(school_id__isnull=True))
            except ValueError:
                # 校舎コードとして処理
                queryset = queryset.filter(Q(school__school_code=school_id) | Q(school_id__isnull=True))

        # 学年でフィルタリング
        grade_name = request.query_params.get('grade_name')
        if grade_name:
            queryset = queryset.filter(grade__grade_name__icontains=grade_name)

        queryset = queryset.order_by('sort_order', 'pack_name')
        serializer = PublicPackSerializer(queryset, many=True)
        return Response(serializer.data)


class PublicPackDetailView(APIView):
    """公開パック詳細API（認証不要・顧客向け）"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        """パック詳細を返す"""
        try:
            pack = Pack.objects.select_related(
                'brand', 'school', 'grade'
            ).prefetch_related('pack_courses__course', 'pack_tickets__ticket').get(
                id=pk,
                is_active=True,
                deleted_at__isnull=True
            )
        except Pack.DoesNotExist:
            return Response({'error': 'Pack not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PublicPackSerializer(pack)
        return Response(serializer.data)


# =============================================================================
# 操作履歴 (Operation History)
# =============================================================================
class OperationHistoryViewSet(viewsets.ViewSet):
    """操作履歴ビューセット

    契約履歴、割引操作ログ、引落結果などを統合して返す。
    """
    permission_classes = [IsAuthenticated, IsTenantUser]
    pagination_class = AdminResultsSetPagination

    def list(self, request):
        """操作履歴一覧を取得"""
        from apps.billing.models import DirectDebitResult
        from .models import ContractHistory, DiscountOperationLog

        tenant_id = getattr(request, 'tenant_id', None)
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        limit = int(request.query_params.get('limit', 100))

        results = []

        # 日付フィルター用のクエリ作成
        date_filter = {}
        if year and year != 'all':
            date_filter['created_at__year'] = int(year)
        if month and month != 'all':
            date_filter['created_at__month'] = int(month)

        # 1. 契約履歴
        contract_histories = ContractHistory.objects.filter(
            tenant_id=tenant_id,
            **date_filter
        ).select_related('contract', 'contract__student', 'changed_by').order_by('-created_at')[:limit]

        for h in contract_histories:
            results.append({
                'id': str(h.id),
                'date': h.created_at.strftime('%Y-%m-%d') if h.created_at else None,
                'type': f'contract_{h.action_type}',
                'type_display': h.get_action_type_display(),
                'student_id': str(h.contract.student.id) if h.contract and h.contract.student else None,
                'student_name': h.contract.student.full_name if h.contract and h.contract.student else None,
                'guardian_id': None,
                'guardian_name': None,
                'content': h.change_summary,
                'status': None,
                'status_display': None,
                'amount': float(h.amount_after) if h.amount_after else None,
                'operator': h.changed_by.get_full_name() if h.changed_by else None,
                'created_at': h.created_at.isoformat() if h.created_at else None,
            })

        # 2. 割引操作ログ
        discount_logs = DiscountOperationLog.objects.filter(
            tenant_id=tenant_id,
            **date_filter
        ).select_related('student', 'operated_by').order_by('-created_at')[:limit]

        for d in discount_logs:
            results.append({
                'id': str(d.id),
                'date': d.created_at.strftime('%Y-%m-%d') if d.created_at else None,
                'type': f'discount_{d.operation_type}',
                'type_display': d.get_operation_type_display(),
                'student_id': str(d.student.id) if d.student else None,
                'student_name': d.student.full_name if d.student else None,
                'guardian_id': None,
                'guardian_name': None,
                'content': f'{d.discount_name} ¥{int(d.discount_amount):,}',
                'status': None,
                'status_display': None,
                'amount': float(d.discount_amount) if d.discount_amount else None,
                'operator': d.operated_by.get_full_name() if d.operated_by else None,
                'created_at': d.created_at.isoformat() if d.created_at else None,
            })

        # 3. 引落結果
        debit_results = DirectDebitResult.objects.filter(
            tenant_id=tenant_id,
            **date_filter
        ).select_related('guardian', 'invoice').order_by('-created_at')[:limit]

        for dr in debit_results:
            status_map = {
                'success': ('success', '成功'),
                'failed': ('failed', '失敗'),
                'pending': ('pending', '処理中'),
            }
            status_info = status_map.get(dr.result_status, (dr.result_status, dr.result_status))

            results.append({
                'id': str(dr.id),
                'date': dr.created_at.strftime('%Y-%m-%d') if dr.created_at else None,
                'type': f'debit_{dr.result_status}',
                'type_display': f'口座振替{status_info[1]}',
                'student_id': None,
                'student_name': None,
                'guardian_id': str(dr.guardian.id) if dr.guardian else None,
                'guardian_name': dr.guardian.full_name if dr.guardian else None,
                'content': f'{dr.billing_month}分 ¥{int(dr.amount):,}' if dr.amount else '',
                'status': status_info[0],
                'status_display': status_info[1],
                'amount': float(dr.amount) if dr.amount else None,
                'operator': None,
                'created_at': dr.created_at.isoformat() if dr.created_at else None,
            })

        # 日時でソート
        results.sort(key=lambda x: x['created_at'] or '', reverse=True)

        # limitを適用
        results = results[:limit]

        return Response({
            'data': results,
            'meta': {
                'total': len(results),
                'page': 1,
                'limit': limit,
                'total_pages': 1,
            }
        })

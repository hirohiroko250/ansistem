"""
Contract Base Mixin - CSV設定・コアメソッド
ContractCSVMixin
"""
from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from apps.core.csv_utils import CSVMixin
from apps.core.pagination import AdminResultsSetPagination
from apps.contracts.models import Contract, StudentItem, Product
from apps.contracts.serializers import (
    ContractListSerializer, ContractDetailSerializer, ContractCreateSerializer,
    StudentItemSerializer,
)


class ContractCSVMixin(CSVMixin):
    """CSV設定・コアメソッドMixin"""

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
        ).select_related(
            'student', 'student__grade', 'guardian',
            'school', 'brand', 'course'
        ).prefetch_related(
            'student_items', 'student_items__product',
            'selected_textbooks'
        )

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
            from apps.contracts.serializers import ContractSimpleListSerializer
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
        """契約の選択教材を更新"""
        contract = self.get_object()
        textbook_ids = request.data.get('selected_textbook_ids', [])

        # 教材商品のみ許可（item_type=textbook）
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

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """契約統計"""
        from django.db.models import Sum
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

    @action(detail=False, methods=['get'])
    def export(self, request):
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        return self.get_csv_template(request)

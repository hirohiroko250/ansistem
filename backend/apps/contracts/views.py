"""
Contracts Views - シンプル版
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Sum
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from .models import (
    Product, Discount, Course, CourseItem,
    Pack, PackCourse,
    Seminar, Certification,
    Contract, StudentItem, SeminarEnrollment, CertificationEnrollment
)
from .serializers import (
    ProductListSerializer, ProductDetailSerializer,
    DiscountListSerializer, DiscountDetailSerializer,
    CourseListSerializer, CourseDetailSerializer,
    PackListSerializer, PackDetailSerializer,
    SeminarListSerializer, SeminarDetailSerializer,
    CertificationListSerializer, CertificationDetailSerializer,
    StudentItemSerializer,
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

    csv_filename_prefix = 'student_items'

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = StudentItem.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'contract', 'product')

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        billing_month = self.request.query_params.get('billing_month')
        if billing_month:
            queryset = queryset.filter(billing_month=billing_month)

        contract_id = self.request.query_params.get('contract_id')
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)

        return queryset

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class ContractViewSet(CSVMixin, viewsets.ModelViewSet):
    """契約ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

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
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Contract.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'guardian', 'school', 'brand', 'course')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ContractListSerializer
        elif self.action == 'create':
            return ContractCreateSerializer
        return ContractDetailSerializer

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

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
        from apps.students.models import Student, Guardian

        user = request.user
        tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得
        try:
            guardian = Guardian.objects.get(user=user, tenant_id=tenant_id, deleted_at__isnull=True)
        except Guardian.DoesNotExist:
            return Response({'contracts': [], 'students': []})

        # 保護者に紐づく生徒を取得（children経由）
        students = guardian.children.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        # 生徒のStudentItem（受講コース）を取得
        # courseがNULLでないものを受講コースとみなす
        student_items = StudentItem.objects.filter(
            student__in=students,
            tenant_id=tenant_id,
            deleted_at__isnull=True,
            course__isnull=False  # コースが紐づいているもののみ
        ).select_related(
            'student', 'student__grade',
            'school', 'brand', 'course'
        ).order_by('student__last_name', 'student__first_name', 'course__course_name')

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
        """
        from apps.schools.models import ClassSchedule
        from datetime import timedelta

        contract = self.get_object()

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
                tenant_id=request.tenant_id,
                deleted_at__isnull=True
            )
        except ClassSchedule.DoesNotExist:
            return Response(
                {'error': '指定されたクラススケジュールが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 同じ校舎・ブランドかチェック
        if class_schedule.school_id != contract.school_id:
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

        # 契約を更新
        contract.day_of_week = int(new_day_of_week)
        contract.start_time = new_start_time
        if hasattr(class_schedule, 'end_time'):
            contract.end_time = class_schedule.end_time
        contract.save()

        return Response({
            'success': True,
            'message': f'{effective_date}からクラスが変更されます',
            'contract': ContractDetailSerializer(contract).data,
            'effective_date': effective_date
        })

    @action(detail=True, methods=['post'], url_path='change-school', permission_classes=[IsAuthenticated])
    def change_school(self, request, pk=None):
        """校舎変更

        翌週から適用
        """
        from apps.schools.models import School, ClassSchedule
        from datetime import timedelta

        contract = self.get_object()

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
                tenant_id=request.tenant_id,
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

        # 契約を更新
        contract.school = new_school
        contract.day_of_week = int(new_day_of_week)
        contract.start_time = new_start_time
        contract.save()

        return Response({
            'success': True,
            'message': f'{effective_date}から校舎が{new_school.school_name}に変更されます',
            'contract': ContractDetailSerializer(contract).data,
            'effective_date': effective_date
        })

    @action(detail=True, methods=['post'], url_path='request-suspension', permission_classes=[IsAuthenticated])
    def request_suspension(self, request, pk=None):
        """休会申請

        保護者からの休会申請を受け付ける
        """
        from .models import ContractChangeRequest
        from datetime import datetime

        contract = self.get_object()

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
            tenant_id=request.tenant_id,
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
            tenant_id=request.tenant_id,
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
        """
        from .models import ContractChangeRequest
        from datetime import datetime, date
        from decimal import Decimal

        contract = self.get_object()

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
            tenant_id=request.tenant_id,
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
            monthly_fee = contract.monthly_fee or Decimal('0')
            refund_amount = (monthly_fee / days_in_month * remaining_days).quantize(Decimal('1'))

        # 申請を作成
        change_request = ContractChangeRequest.objects.create(
            tenant_id=request.tenant_id,
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

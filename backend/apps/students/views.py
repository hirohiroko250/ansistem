"""
Students Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Q
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVExporter, CSVImporter, CSVMixin
from .models import Student, Guardian, StudentSchool, StudentGuardian, SuspensionRequest, WithdrawalRequest, BankAccount, BankAccountChangeRequest
from .serializers import (
    StudentListSerializer, StudentDetailSerializer,
    StudentCreateSerializer, StudentUpdateSerializer,
    GuardianListSerializer, GuardianDetailSerializer, GuardianCreateUpdateSerializer,
    GuardianPaymentSerializer, GuardianPaymentUpdateSerializer,
    StudentSchoolSerializer, StudentGuardianSerializer,
    StudentWithGuardiansSerializer,
    SuspensionRequestSerializer, SuspensionRequestCreateSerializer,
    WithdrawalRequestSerializer, WithdrawalRequestCreateSerializer,
    BankAccountSerializer, BankAccountChangeRequestSerializer, BankAccountChangeRequestCreateSerializer,
)


class StudentViewSet(CSVMixin, viewsets.ModelViewSet):
    """生徒ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'students'
    csv_export_fields = [
        'student_no', 'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
        'email', 'phone', 'line_id', 'birth_date', 'gender',
        'school_name', 'school_type', 'grade.grade_name',
        'primary_school.school_name', 'primary_brand.brand_name',
        'status', 'enrollment_date', 'withdrawal_date',
        'notes', 'tenant_id'
    ]
    csv_export_headers = {
        'student_no': '生徒番号',
        'last_name': '姓',
        'first_name': '名',
        'last_name_kana': '姓（カナ）',
        'first_name_kana': '名（カナ）',
        'email': 'メールアドレス',
        'phone': '電話番号',
        'line_id': 'LINE ID',
        'birth_date': '生年月日',
        'gender': '性別',
        'school_name': '在籍学校名',
        'school_type': '学校種別',
        'grade.grade_name': '学年',
        'primary_school.school_name': '主所属校舎',
        'primary_brand.brand_name': '主所属ブランド',
        'status': 'ステータス',
        'enrollment_date': '入塾日',
        'withdrawal_date': '退塾日',
        'notes': '備考',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '生徒番号': 'student_no',
        '姓': 'last_name',
        '名': 'first_name',
        '姓（カナ）': 'last_name_kana',
        '名（カナ）': 'first_name_kana',
        'メールアドレス': 'email',
        '電話番号': 'phone',
        'LINE ID': 'line_id',
        '生年月日': 'birth_date',
        '性別': 'gender',
        '在籍学校名': 'school_name',
        '学校種別': 'school_type',
        'ステータス': 'status',
        '入塾日': 'enrollment_date',
        '退塾日': 'withdrawal_date',
        '備考': 'notes',
    }
    csv_required_fields = ['生徒番号', '姓', '名']
    csv_unique_fields = ['student_no']

    def get_queryset(self):
        from apps.core.permissions import is_admin_user

        # request.tenant_id または request.user.tenant_id からテナントIDを取得
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = Student.objects.filter(
            deleted_at__isnull=True
        ).select_related('grade', 'primary_school', 'primary_brand', 'guardian')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        # ログインユーザーが保護者の場合、その保護者に紐づく子供だけを返す
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(guardian=guardian)

        # フィルタリング
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        school_id = self.request.query_params.get('school_id') or self.request.query_params.get('primary_school_id')
        if school_id:
            # primary_schoolまたはStudentSchoolで紐づいている生徒を取得
            queryset = queryset.filter(
                Q(primary_school_id=school_id) |
                Q(school_enrollments__school_id=school_id, school_enrollments__enrollment_status='active', school_enrollments__deleted_at__isnull=True)
            ).distinct()

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            # primary_brandまたはStudentSchool、またはbrandsで紐づいている生徒を取得
            queryset = queryset.filter(
                Q(primary_brand_id=brand_id) |
                Q(brands__id=brand_id) |
                Q(school_enrollments__brand_id=brand_id, school_enrollments__enrollment_status='active', school_enrollments__deleted_at__isnull=True)
            ).distinct()

        # ブランドカテゴリ（会社）でフィルタ
        brand_category_id = self.request.query_params.get('brand_category_id')
        if brand_category_id:
            queryset = queryset.filter(primary_brand__brand_category_id=brand_category_id)

        grade_id = self.request.query_params.get('grade_id')
        if grade_id:
            queryset = queryset.filter(grade_id=grade_id)

        # 保護者IDでフィルタ（兄弟検索用）
        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(guardian_id=guardian_id)

        # 検索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(student_no__icontains=search) |
                Q(last_name__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name_kana__icontains=search) |
                Q(first_name_kana__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(phone2__icontains=search) |
                Q(guardian__phone__icontains=search) |
                Q(guardian__phone_mobile__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return StudentListSerializer
        elif self.action == 'create':
            return StudentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return StudentUpdateSerializer
        elif self.action == 'with_guardians':
            return StudentWithGuardiansSerializer
        return StudentDetailSerializer

    def perform_create(self, serializer):
        # ログインユーザーが保護者の場合、自動的に紐付け
        guardian = None
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile

        # tenant_idを取得（request.tenant_idまたは保護者プロファイルから）
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and guardian:
            tenant_id = guardian.tenant_id

        student = serializer.save(tenant_id=tenant_id, guardian=guardian)

        # 作業一覧にタスクを作成
        from apps.tasks.models import Task
        Task.objects.create(
            tenant_id=tenant_id,
            task_type='student_registration',
            title=f'生徒登録: {student.full_name}',
            description=f'生徒「{student.full_name}」が登録されました。確認をお願いします。',
            status='new',
            priority='normal',
            student=student,
            guardian=guardian,
            source_type='student',
            source_id=student.id,
        )

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['get'])
    def export(self, request):
        """CSVエクスポート"""
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """CSVインポート"""
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        """CSVテンプレートダウンロード"""
        return self.get_csv_template(request)

    @action(detail=False, methods=['get'])
    def with_guardians(self, request):
        """保護者情報付き生徒一覧"""
        queryset = self.get_queryset().prefetch_related(
            'guardian_relations__guardian'
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def guardians(self, request, pk=None):
        """生徒の保護者一覧"""
        student = self.get_object()
        relations = student.guardian_relations.select_related('guardian').all()
        serializer = StudentGuardianSerializer(relations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_guardian(self, request, pk=None):
        """保護者追加"""
        student = self.get_object()
        serializer = StudentGuardianSerializer(data={
            **request.data,
            'student': student.id
        })
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.tenant_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def schools(self, request, pk=None):
        """生徒の所属校舎一覧"""
        student = self.get_object()
        enrollments = student.school_enrollments.select_related('school', 'brand').all()
        serializer = StudentSchoolSerializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """ステータス変更"""
        student = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(Student.Status.choices):
            return Response(
                {'error': '無効なステータスです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        student.status = new_status
        if new_status == Student.Status.WITHDRAWN:
            student.withdrawal_date = request.data.get('withdrawal_date', timezone.now().date())
            student.withdrawal_reason = request.data.get('withdrawal_reason', '')

        student.save()
        return Response(StudentDetailSerializer(student).data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """生徒統計"""
        queryset = self.get_queryset()
        stats = {
            'total': queryset.count(),
            'by_status': {},
            'by_grade': {},
        }

        for status_choice in Student.Status.choices:
            stats['by_status'][status_choice[0]] = queryset.filter(
                status=status_choice[0]
            ).count()

        return Response(stats)

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """生徒の購入アイテム（StudentItem）一覧を取得"""
        from apps.contracts.models import StudentItem

        student = self.get_object()
        items = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True
        ).select_related('product', 'product__brand', 'contract', 'contract__school')

        billing_month = request.query_params.get('billing_month')
        if billing_month:
            items = items.filter(billing_month=billing_month)

        result = []
        for item in items:
            result.append({
                'id': str(item.id),
                'productId': str(item.product.id) if item.product else None,
                'productName': item.product.product_name if item.product else '',
                'productType': item.product.item_type if item.product else '',
                'brandName': item.product.brand.brand_name if item.product and item.product.brand else '',
                'brandCode': item.product.brand.brand_code if item.product and item.product.brand else '',
                'schoolName': item.contract.school.school_name if item.contract and item.contract.school else '',
                'billingMonth': item.billing_month,
                'quantity': item.quantity,
                'unitPrice': int(item.unit_price),
                'discountAmount': int(item.discount_amount),
                'finalPrice': int(item.final_price),
                'notes': item.notes,
                'createdAt': item.created_at.isoformat() if item.created_at else None,
            })

        return Response(result)

    @action(detail=True, methods=['get'])
    def tickets(self, request, pk=None):
        """生徒のチケット残高を取得"""
        from apps.contracts.models import StudentItem
        from decimal import Decimal

        student = self.get_object()

        # チケット系のアイテム（item_type='ticket'）を集計
        items = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True
        ).select_related('product', 'product__brand')

        # ブランドごとにチケット残高を集計
        ticket_balances = {}
        total_tickets = Decimal('0')

        for item in items:
            if item.product and item.product.item_type == 'ticket':
                brand_name = item.product.brand.brand_name if item.product.brand else '未分類'
                if brand_name not in ticket_balances:
                    ticket_balances[brand_name] = {
                        'brandName': brand_name,
                        'totalTickets': Decimal('0'),
                        'usedTickets': Decimal('0'),
                        'remainingTickets': Decimal('0'),
                    }
                # 購入チケット数を加算（quantityがチケット枚数）
                ticket_balances[brand_name]['totalTickets'] += item.quantity
                ticket_balances[brand_name]['remainingTickets'] += item.quantity
                total_tickets += item.quantity

        # 辞書をリストに変換
        balances_list = list(ticket_balances.values())
        for balance in balances_list:
            balance['totalTickets'] = int(balance['totalTickets'])
            balance['usedTickets'] = int(balance['usedTickets'])
            balance['remainingTickets'] = int(balance['remainingTickets'])

        return Response({
            'studentId': str(student.id),
            'studentName': f'{student.last_name}{student.first_name}',
            'totalTickets': int(total_tickets),
            'usedTickets': 0,
            'remainingTickets': int(total_tickets),
            'balancesByBrand': balances_list,
        })

    @action(detail=True, methods=['get'], url_path='tickets/history')
    def tickets_history(self, request, pk=None):
        """生徒のチケット履歴を取得"""
        from apps.contracts.models import StudentItem

        student = self.get_object()

        # チケット系のアイテム（item_type='ticket'）を取得
        items = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True
        ).select_related('product', 'product__brand').order_by('-created_at')

        # フィルタリング
        brand_id = request.query_params.get('brand_id')
        if brand_id:
            items = items.filter(product__brand_id=brand_id)

        history = []
        for item in items:
            if item.product and item.product.item_type == 'ticket':
                history.append({
                    'id': str(item.id),
                    'date': item.created_at.isoformat() if item.created_at else None,
                    'type': 'purchase',
                    'description': f'{item.product.product_name} 購入',
                    'amount': item.quantity,
                    'brandName': item.product.brand.brand_name if item.product.brand else '',
                    'billingMonth': item.billing_month,
                })

        return Response(history)

    @action(detail=False, methods=['get'])
    def all_items(self, request):
        """保護者の全子どもの購入アイテム一覧を取得"""
        from apps.contracts.models import StudentItem
        from apps.schools.models import Brand

        # 保護者に紐づく全子どもの購入アイテムを取得
        students = self.get_queryset()
        student_ids = list(students.values_list('id', flat=True))

        items = StudentItem.objects.filter(
            student_id__in=student_ids,
            deleted_at__isnull=True
        ).select_related(
            'student', 'product', 'product__brand',
            'contract', 'contract__school', 'contract__course', 'contract__course__brand',
            'brand', 'school', 'course'  # StudentItemに直接保存された情報
        )

        billing_month = request.query_params.get('billing_month')
        if billing_month:
            items = items.filter(billing_month=billing_month)

        # ブランド名からブランドIDを取得するためのマッピングをキャッシュ
        brand_cache = {}
        for brand in Brand.objects.all():
            brand_cache[brand.brand_name] = {
                'id': str(brand.id),
                'code': brand.brand_code,
                'name': brand.brand_name
            }

        result = []
        for item in items:
            # コース名とブランド名の取得
            course_name = ''
            brand_name = ''
            brand_code = ''
            brand_id = None
            school_name = ''
            school_id = None
            start_date = None

            # 1. StudentItemに直接保存された情報を優先
            if item.brand:
                brand_name = item.brand.brand_name or ''
                brand_code = item.brand.brand_code or ''
                brand_id = str(item.brand.id)

            if item.school:
                school_name = item.school.school_name or ''
                school_id = str(item.school.id)

            if item.course:
                course_name = item.course.course_name or ''
                # コースからブランドを取得（StudentItemにbrandが設定されていない場合）
                if not brand_id and item.course.brand:
                    brand_name = item.course.brand.brand_name or ''
                    brand_code = item.course.brand.brand_code or ''
                    brand_id = str(item.course.brand.id)

            if item.start_date:
                start_date = item.start_date.isoformat()

            # 2. fallback: contractからcourseを取得してコース名・ブランド名を取得
            if not course_name and item.contract and item.contract.course:
                course_name = item.contract.course.course_name or ''
                if not brand_id and item.contract.course.brand:
                    brand_name = item.contract.course.brand.brand_name or ''
                    brand_code = item.contract.course.brand.brand_code or ''
                    brand_id = str(item.contract.course.brand.id)

            # 3. fallback: productから取得
            if not brand_id and item.product and item.product.brand:
                brand_name = item.product.brand.brand_name or ''
                brand_code = item.product.brand.brand_code or ''
                brand_id = str(item.product.brand.id)

            # 4. fallback: 商品名からブランドを推測
            if not brand_id and item.product:
                product_name = item.product.product_name or ''
                for bn, binfo in brand_cache.items():
                    if product_name.startswith(bn):
                        brand_name = bn
                        brand_code = binfo['code']
                        brand_id = binfo['id']
                        break

            # 5. fallback: contractからschoolを取得
            if not school_id and item.contract and item.contract.school:
                school_name = item.contract.school.school_name or ''
                school_id = str(item.contract.school.id)

            # 6. fallback: 生徒の主校舎から取得
            if not school_id and item.student and item.student.primary_school:
                school_name = item.student.primary_school.school_name or ''
                school_id = str(item.student.primary_school.id)

            result.append({
                'id': str(item.id),
                'studentId': str(item.student.id) if item.student else None,
                'studentName': f'{item.student.last_name}{item.student.first_name}' if item.student else '',
                'productId': str(item.product.id) if item.product else None,
                'productName': item.product.product_name if item.product else '',
                'productType': item.product.item_type if item.product else '',
                'courseName': course_name,
                'brandName': brand_name,
                'brandCode': brand_code,
                'brandId': brand_id,
                'schoolName': school_name,
                'schoolId': school_id,
                'startDate': start_date,  # 開始日を追加
                'billingMonth': item.billing_month,
                'quantity': item.quantity,
                'unitPrice': int(item.unit_price),
                'discountAmount': int(item.discount_amount),
                'finalPrice': int(item.final_price),
                'notes': item.notes,
                'createdAt': item.created_at.isoformat() if item.created_at else None,
            })

        return Response(result)


class GuardianViewSet(CSVMixin, viewsets.ModelViewSet):
    """保護者ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'guardians'
    csv_export_fields = [
        'guardian_no', 'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
        'email', 'phone', 'phone_mobile', 'line_id',
        'postal_code', 'prefecture', 'city', 'address1', 'address2',
        'workplace', 'workplace_phone', 'notes', 'tenant_id'
    ]
    csv_export_headers = {
        'guardian_no': '保護者番号',
        'last_name': '姓',
        'first_name': '名',
        'last_name_kana': '姓（カナ）',
        'first_name_kana': '名（カナ）',
        'email': 'メールアドレス',
        'phone': '電話番号',
        'phone_mobile': '携帯電話',
        'line_id': 'LINE ID',
        'postal_code': '郵便番号',
        'prefecture': '都道府県',
        'city': '市区町村',
        'address1': '住所1',
        'address2': '住所2',
        'workplace': '勤務先',
        'workplace_phone': '勤務先電話番号',
        'notes': '備考',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '保護者番号': 'guardian_no',
        '姓': 'last_name',
        '名': 'first_name',
        '姓（カナ）': 'last_name_kana',
        '名（カナ）': 'first_name_kana',
        'メールアドレス': 'email',
        '電話番号': 'phone',
        '携帯電話': 'phone_mobile',
        'LINE ID': 'line_id',
        '郵便番号': 'postal_code',
        '都道府県': 'prefecture',
        '市区町村': 'city',
        '住所1': 'address1',
        '住所2': 'address2',
        '勤務先': 'workplace',
        '勤務先電話番号': 'workplace_phone',
        '備考': 'notes',
    }
    csv_required_fields = ['姓', '名']
    csv_unique_fields = ['guardian_no']

    def get_queryset(self):
        # request.tenant_id または request.user.tenant_id からテナントIDを取得
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = Guardian.objects.filter(
            deleted_at__isnull=True
        )

        # tenant_idがある場合のみフィルタ
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        if self.action == 'list':
            queryset = queryset.annotate(
                student_count=Count('student_relations')
            )

        # 検索
        search = self.request.query_params.get('search')
        if search:
            # スペースで区切られた検索ワードを分割
            search_terms = search.replace('　', ' ').split()

            if len(search_terms) >= 2:
                # 2つ以上のワードがある場合：姓名検索
                q = Q()
                for term in search_terms:
                    q &= (
                        Q(last_name__icontains=term) |
                        Q(first_name__icontains=term) |
                        Q(last_name_kana__icontains=term) |
                        Q(first_name_kana__icontains=term)
                    )
                queryset = queryset.filter(q)
            else:
                # 1つのワード：姓または名、または姓名結合に部分一致
                from django.db.models.functions import Concat
                from django.db.models import Value
                queryset = queryset.annotate(
                    full_name=Concat('last_name', 'first_name'),
                    full_name_kana=Concat('last_name_kana', 'first_name_kana'),
                ).filter(
                    Q(guardian_no__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(first_name__icontains=search) |
                    Q(last_name_kana__icontains=search) |
                    Q(first_name_kana__icontains=search) |
                    Q(full_name__icontains=search) |
                    Q(full_name_kana__icontains=search) |
                    Q(email__icontains=search) |
                    Q(phone__icontains=search) |
                    Q(phone_mobile__icontains=search)
                )

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return GuardianListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return GuardianCreateUpdateSerializer
        return GuardianDetailSerializer

    def perform_create(self, serializer):
        guardian = serializer.save(tenant_id=self.request.tenant_id)

        # 作業一覧にタスクを作成
        from apps.tasks.models import Task
        Task.objects.create(
            tenant_id=self.request.tenant_id,
            task_type='guardian_registration',
            title=f'保護者登録: {guardian.last_name} {guardian.first_name}',
            description=f'保護者「{guardian.last_name} {guardian.first_name}」が登録されました。確認をお願いします。',
            status='new',
            priority='normal',
            guardian=guardian,
            source_type='guardian',
            source_id=guardian.id,
        )

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['get'])
    def export(self, request):
        """CSVエクスポート"""
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """CSVインポート"""
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        """CSVテンプレートダウンロード"""
        return self.get_csv_template(request)

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """保護者の生徒一覧"""
        guardian = self.get_object()
        relations = guardian.student_relations.select_related('student').all()
        serializer = StudentGuardianSerializer(relations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def payment(self, request, pk=None):
        """保護者の支払い情報取得"""
        guardian = self.get_object()
        serializer = GuardianPaymentSerializer(guardian)
        return Response(serializer.data)

    @action(detail=True, methods=['put', 'patch'])
    def payment_update(self, request, pk=None):
        """保護者の支払い情報更新"""
        guardian = self.get_object()
        serializer = GuardianPaymentUpdateSerializer(guardian, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # 更新後のデータを返す
        return Response(GuardianPaymentSerializer(guardian).data)

    @action(detail=False, methods=['get'])
    def my_payment(self, request):
        """ログイン中の保護者の支払い情報取得"""
        if not hasattr(request.user, 'guardian_profile') or not request.user.guardian_profile:
            return Response(
                {'error': '保護者プロファイルが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        guardian = request.user.guardian_profile
        serializer = GuardianPaymentSerializer(guardian)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def my_payment_update(self, request):
        """ログイン中の保護者の支払い情報更新"""
        if not hasattr(request.user, 'guardian_profile') or not request.user.guardian_profile:
            return Response(
                {'error': '保護者プロファイルが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        guardian = request.user.guardian_profile
        serializer = GuardianPaymentUpdateSerializer(guardian, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(GuardianPaymentSerializer(guardian).data)


class StudentGuardianViewSet(CSVMixin, viewsets.ModelViewSet):
    """生徒保護者関連ビューセット"""
    serializer_class = StudentGuardianSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'student_guardians'
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'guardian.guardian_no', 'guardian.last_name', 'guardian.first_name',
        'relationship', 'is_primary', 'is_emergency_contact', 'is_billing_target',
        'contact_priority', 'notes', 'tenant_id'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'guardian.guardian_no': '保護者番号',
        'guardian.last_name': '保護者姓',
        'guardian.first_name': '保護者名',
        'relationship': '続柄',
        'is_primary': '主保護者',
        'is_emergency_contact': '緊急連絡先',
        'is_billing_target': '請求先',
        'contact_priority': '連絡優先順位',
        'notes': '備考',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '生徒番号': 'student_no',
        '保護者番号': 'guardian_no',
        '続柄': 'relationship',
        '主保護者': 'is_primary',
        '緊急連絡先': 'is_emergency_contact',
        '請求先': 'is_billing_target',
        '連絡優先順位': 'contact_priority',
        '備考': 'notes',
    }
    csv_required_fields = ['生徒番号', '保護者番号']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return StudentGuardian.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'guardian')

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """CSVエクスポート"""
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """CSVインポート（生徒番号・保護者番号で紐付け）"""
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response(
                {'error': 'CSVファイルが指定されていません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tenant_id = getattr(request, 'tenant_id', None)
        import csv
        import io

        content = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))

        created_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            student_no = row.get('生徒番号', '').strip()
            guardian_no = row.get('保護者番号', '').strip()

            if not student_no or not guardian_no:
                errors.append({'row': row_num, 'message': '生徒番号または保護者番号が空です'})
                continue

            try:
                student = Student.objects.get(tenant_id=tenant_id, student_no=student_no)
                guardian = Guardian.objects.get(tenant_id=tenant_id, guardian_no=guardian_no)

                relation, created = StudentGuardian.objects.update_or_create(
                    tenant_id=tenant_id,
                    student=student,
                    guardian=guardian,
                    defaults={
                        'relationship': row.get('続柄', 'other'),
                        'is_primary': row.get('主保護者', '').lower() in ('true', '1', 'yes', 'はい'),
                        'is_emergency_contact': row.get('緊急連絡先', '').lower() in ('true', '1', 'yes', 'はい'),
                        'is_billing_target': row.get('請求先', '').lower() in ('true', '1', 'yes', 'はい'),
                        'contact_priority': int(row.get('連絡優先順位', 1) or 1),
                        'notes': row.get('備考', ''),
                    }
                )
                if created:
                    created_count += 1

            except Student.DoesNotExist:
                errors.append({'row': row_num, 'message': f'生徒番号 {student_no} が見つかりません'})
            except Guardian.DoesNotExist:
                errors.append({'row': row_num, 'message': f'保護者番号 {guardian_no} が見つかりません'})
            except Exception as e:
                errors.append({'row': row_num, 'message': str(e)})

        return Response({
            'success': len(errors) == 0,
            'created': created_count,
            'errors': errors
        })

    @action(detail=False, methods=['get'])
    def template(self, request):
        """CSVテンプレートダウンロード"""
        return self.get_csv_template(request)


class StudentSchoolViewSet(CSVMixin, viewsets.ModelViewSet):
    """生徒所属ビューセット"""
    serializer_class = StudentSchoolSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'student_schools'
    csv_export_fields = [
        'student.student_no', 'school.school_code', 'brand.brand_code',
        'enrollment_status', 'start_date', 'end_date', 'is_primary',
        'day_of_week', 'start_time', 'end_time', 'notes', 'tenant_id'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'school.school_code': '校舎コード',
        'brand.brand_code': 'ブランドコード',
        'enrollment_status': '在籍状況',
        'start_date': '開始日',
        'end_date': '終了日',
        'is_primary': '主所属',
        'day_of_week': '曜日',
        'start_time': '開始時間',
        'end_time': '終了時間',
        'notes': '備考',
        'tenant_id': 'テナントID',
    }

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return StudentSchool.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'school', 'brand', 'class_schedule')

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """CSVエクスポート"""
        return self.export_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        """CSVテンプレートダウンロード"""
        return self.get_csv_template(request)


# =====================================
# 休会・退会申請用ViewSet
# =====================================

class SuspensionRequestViewSet(viewsets.ModelViewSet):
    """休会申請ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = SuspensionRequest.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'brand', 'school', 'requested_by', 'processed_by')

        # 保護者の場合は自分の子供の申請のみ
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(student__guardian=guardian)

        # フィルタリング
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-requested_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return SuspensionRequestCreateSerializer
        return SuspensionRequestSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            tenant_id = self.request.user.guardian_profile.tenant_id

        # 生徒情報から自動的にブランド・校舎を設定
        student = serializer.validated_data.get('student')
        brand = serializer.validated_data.get('brand') or student.primary_brand
        school = serializer.validated_data.get('school') or student.primary_school

        instance = serializer.save(
            tenant_id=tenant_id,
            brand=brand,
            school=school,
            requested_by=self.request.user,
            status='pending'
        )

        # 作業一覧にタスクを作成
        from apps.tasks.models import Task
        Task.objects.create(
            tenant_id=tenant_id,
            task_type='suspension_request',
            title=f'休会申請: {instance.student.full_name}',
            description=f'{instance.student.full_name}さんの休会申請が提出されました。休会開始日: {instance.suspend_from}',
            status='new',
            priority='normal',
            student=instance.student,
            source_type='suspension_request',
            source_id=instance.id,
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """申請キャンセル"""
        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみキャンセルできます'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.status = 'cancelled'
        instance.save()
        return Response(SuspensionRequestSerializer(instance).data)


class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    """退会申請ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = WithdrawalRequest.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'brand', 'school', 'requested_by', 'processed_by')

        # 保護者の場合は自分の子供の申請のみ
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(student__guardian=guardian)

        # フィルタリング
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-requested_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return WithdrawalRequestCreateSerializer
        return WithdrawalRequestSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            tenant_id = self.request.user.guardian_profile.tenant_id

        # 生徒情報から自動的にブランド・校舎を設定
        student = serializer.validated_data.get('student')
        brand = serializer.validated_data.get('brand') or student.primary_brand
        school = serializer.validated_data.get('school') or student.primary_school

        # 残チケット数を計算
        from apps.contracts.models import StudentItem
        remaining_tickets = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True,
            product__item_type='ticket'
        ).aggregate(total=Count('id'))['total'] or 0

        instance = serializer.save(
            tenant_id=tenant_id,
            brand=brand,
            school=school,
            requested_by=self.request.user,
            status='pending',
            remaining_tickets=remaining_tickets
        )

        # 作業一覧にタスクを作成
        from apps.tasks.models import Task
        Task.objects.create(
            tenant_id=tenant_id,
            task_type='withdrawal_request',
            title=f'退会申請: {instance.student.full_name}',
            description=f'{instance.student.full_name}さんの退会申請が提出されました。退会希望日: {instance.withdrawal_date}',
            status='new',
            priority='high',
            student=instance.student,
            source_type='withdrawal_request',
            source_id=instance.id,
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """申請キャンセル"""
        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみキャンセルできます'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.status = 'cancelled'
        instance.save()
        return Response(WithdrawalRequestSerializer(instance).data)


# =====================================
# 銀行口座管理用ViewSet
# =====================================

class BankAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """銀行口座ビューセット（読み取り専用）"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = BankAccount.objects.filter(
            tenant_id=tenant_id,
            is_active=True
        ).select_related('guardian')

        # 保護者の場合は自分の口座のみ
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(guardian=guardian)

        return queryset.order_by('-is_primary', '-created_at')

    @action(detail=False, methods=['get'])
    def my_accounts(self, request):
        """ログイン中の保護者の銀行口座一覧"""
        if not hasattr(request.user, 'guardian_profile') or not request.user.guardian_profile:
            return Response(
                {'error': '保護者プロファイルが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        guardian = request.user.guardian_profile
        accounts = BankAccount.objects.filter(
            guardian=guardian,
            is_active=True
        ).order_by('-is_primary', '-created_at')
        serializer = BankAccountSerializer(accounts, many=True)
        return Response(serializer.data)


class BankAccountChangeRequestViewSet(viewsets.ModelViewSet):
    """銀行口座変更申請ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = BankAccountChangeRequest.objects.filter(
            tenant_id=tenant_id
        ).select_related('guardian', 'existing_account', 'requested_by', 'processed_by')

        # 保護者の場合は自分の申請のみ
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(guardian=guardian)

        # フィルタリング
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-requested_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return BankAccountChangeRequestCreateSerializer
        return BankAccountChangeRequestSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        guardian = None

        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            if not tenant_id:
                tenant_id = guardian.tenant_id

        instance = serializer.save(
            tenant_id=tenant_id,
            guardian=guardian,
            requested_by=self.request.user,
            status='pending'
        )

        # 作業一覧にタスクを作成
        from apps.tasks.models import Task
        request_type_display = dict(BankAccountChangeRequest.RequestType.choices).get(
            instance.request_type, instance.request_type
        )
        Task.objects.create(
            tenant_id=tenant_id,
            task_type='bank_account_request',
            title=f'銀行口座{request_type_display}: {guardian.full_name if guardian else "不明"}',
            description=f'{guardian.full_name if guardian else "不明"}さんから銀行口座の{request_type_display}申請が提出されました。',
            status='new',
            priority='normal',
            guardian=guardian,
            source_type='bank_account_request',
            source_id=instance.id,
        )

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """ログイン中の保護者の申請一覧"""
        if not hasattr(request.user, 'guardian_profile') or not request.user.guardian_profile:
            return Response(
                {'error': '保護者プロファイルが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        guardian = request.user.guardian_profile
        requests = BankAccountChangeRequest.objects.filter(
            guardian=guardian
        ).order_by('-requested_at')
        serializer = BankAccountChangeRequestSerializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """申請キャンセル"""
        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみキャンセルできます'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.status = 'cancelled'
        instance.save()
        return Response(BankAccountChangeRequestSerializer(instance).data)

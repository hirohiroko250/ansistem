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
            from django.db.models.functions import Concat
            from django.db.models import Exists, OuterRef

            # スペースで区切られた検索ワードを分割
            search_terms = search.replace('　', ' ').split()

            # 子供の名前検索用のサブクエリを構築
            # Note: Guardian.children is the related_name for Student.guardian
            def build_student_subquery(term):
                """指定された検索語にマッチする子供を持つかどうかのサブクエリ"""
                return Student.objects.filter(
                    guardian_id=OuterRef('pk'),
                    deleted_at__isnull=True
                ).annotate(
                    student_full_name=Concat('last_name', 'first_name'),
                    student_full_name_kana=Concat('last_name_kana', 'first_name_kana'),
                ).filter(
                    Q(last_name__icontains=term) |
                    Q(first_name__icontains=term) |
                    Q(last_name_kana__icontains=term) |
                    Q(first_name_kana__icontains=term) |
                    Q(student_full_name__icontains=term) |
                    Q(student_full_name_kana__icontains=term) |
                    Q(student_no__icontains=term)
                )

            if len(search_terms) >= 2:
                # 2つ以上のワードがある場合：姓名検索
                q = Q()
                for term in search_terms:
                    q &= (
                        Q(last_name__icontains=term) |
                        Q(first_name__icontains=term) |
                        Q(last_name_kana__icontains=term) |
                        Q(first_name_kana__icontains=term) |
                        # 子供の名前でも検索
                        Exists(build_student_subquery(term))
                    )
                queryset = queryset.filter(q).distinct()
            else:
                # 1つのワード：姓または名、または姓名結合に部分一致
                queryset = queryset.annotate(
                    guardian_full_name=Concat('last_name', 'first_name'),
                    guardian_full_name_kana=Concat('last_name_kana', 'first_name_kana'),
                ).filter(
                    Q(guardian_no__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(first_name__icontains=search) |
                    Q(last_name_kana__icontains=search) |
                    Q(first_name_kana__icontains=search) |
                    Q(guardian_full_name__icontains=search) |
                    Q(guardian_full_name_kana__icontains=search) |
                    Q(email__icontains=search) |
                    Q(phone__icontains=search) |
                    Q(phone_mobile__icontains=search) |
                    # 子供の名前でも検索（姓名連結も含む）
                    Exists(build_student_subquery(search))
                ).distinct()

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
        """保護者の生徒一覧（生徒詳細情報付き）"""
        guardian = self.get_object()
        # 直接参照（guardian FK）で紐づいている生徒を取得
        children = guardian.children.filter(deleted_at__isnull=True).select_related('grade', 'primary_school', 'primary_brand')
        serializer = StudentListSerializer(children, many=True)
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

    @action(detail=True, methods=['get'])
    def billing_summary(self, request, pk=None):
        """保護者の請求サマリー（全子供の料金・割引含む）"""
        from apps.contracts.models import StudentItem, StudentDiscount
        from apps.billing.models import Invoice
        from decimal import Decimal
        from django.utils import timezone

        guardian = self.get_object()

        # 支払い状態の確認（滞納があるか）
        overdue_invoices = 0
        unpaid_amount = 0
        payment_method = 'direct_debit'
        payment_method_display = '口座引落'
        account_balance = 0  # 残高（プラス=不足、マイナス=過払い）
        invoice_history = []  # 請求履歴
        payment_history = []  # 入金履歴

        try:
            overdue_invoices = Invoice.objects.filter(
                guardian=guardian,
                status='overdue'
            ).count()

            unpaid_invoices = Invoice.objects.filter(
                guardian=guardian,
                status__in=['issued', 'partial']
            )
            unpaid_amount = sum(inv.balance_due or 0 for inv in unpaid_invoices)

            # 最新の請求書から支払い方法を取得
            latest_invoice = Invoice.objects.filter(
                guardian=guardian
            ).order_by('-billing_year', '-billing_month').first()

            if latest_invoice:
                payment_method = latest_invoice.payment_method
                payment_method_display = latest_invoice.get_payment_method_display()

            # 全請求書から残高を計算
            all_invoices = Invoice.objects.filter(guardian=guardian).order_by('-billing_year', '-billing_month')
            total_billed = Decimal('0')
            total_paid = Decimal('0')

            for inv in all_invoices[:24]:  # 直近2年分
                billed = inv.total_amount or Decimal('0')
                paid = inv.paid_amount or Decimal('0')
                total_billed += billed
                total_paid += paid

                # 請求履歴を収集
                invoice_history.append({
                    'id': str(inv.id),
                    'invoiceNo': inv.invoice_no or '',
                    'billingYear': inv.billing_year,
                    'billingMonth': inv.billing_month,
                    'billingLabel': f"{inv.billing_year}年{inv.billing_month}月",
                    'totalAmount': int(billed),
                    'paidAmount': int(paid),
                    'balanceDue': int(inv.balance_due or 0),
                    'status': inv.status,
                    'statusDisplay': inv.get_status_display() if hasattr(inv, 'get_status_display') else inv.status,
                    'paymentMethod': inv.payment_method or 'direct_debit',
                    'paidAt': inv.paid_at.isoformat() if inv.paid_at else None,
                    'dueDate': inv.due_date.isoformat() if inv.due_date else None,
                    'issuedAt': inv.issued_at.isoformat() if inv.issued_at else None,
                })

            # 残高計算（プラス=不足、マイナス=過払い）
            account_balance = int(total_billed - total_paid)

            # 入金履歴を取得（Paymentモデルがあれば）
            try:
                from apps.billing.models import Payment
                payments = Payment.objects.filter(
                    guardian=guardian
                ).order_by('-payment_date', '-created_at')[:20]

                for pmt in payments:
                    payment_history.append({
                        'id': str(pmt.id),
                        'paymentDate': pmt.payment_date.isoformat() if pmt.payment_date else None,
                        'amount': int(pmt.amount or 0),
                        'paymentMethod': pmt.payment_method or '',
                        'paymentMethodDisplay': pmt.get_payment_method_display() if hasattr(pmt, 'get_payment_method_display') else pmt.payment_method,
                        'status': pmt.status if hasattr(pmt, 'status') else 'completed',
                        'notes': pmt.notes or '',
                    })
            except Exception:
                # Paymentモデルが存在しない場合はスキップ
                pass

        except Exception:
            # テーブルが存在しない場合などはスキップ
            pass

        # 子供一覧
        children = guardian.children.filter(deleted_at__isnull=True).select_related('grade', 'primary_school', 'primary_brand')

        # 子供ごとの料金明細を取得
        children_billing = []
        total_amount = Decimal('0')
        total_discount = Decimal('0')

        # 曜日変換
        day_of_week_map = {
            1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'
        }

        for child in children:
            child_name = f"{child.last_name}{child.first_name}"

            # StudentItem（月謝等）を取得
            items = StudentItem.objects.filter(
                student=child,
                deleted_at__isnull=True
            ).select_related('product', 'product__brand', 'contract', 'contract__school', 'class_schedule')

            child_items = []
            child_total = Decimal('0')
            enrollments = []  # 在籍情報（ブランド・曜日・時間）

            for item in items:
                unit_price = item.unit_price or Decimal('0')
                discount_amount = item.discount_amount or Decimal('0')
                final_price = item.final_price or (unit_price - discount_amount)
                child_total += final_price

                # スケジュール情報
                day_display = day_of_week_map.get(item.day_of_week, '') if item.day_of_week else ''
                time_display = item.start_time.strftime('%H:%M') if item.start_time else ''
                class_name = item.class_schedule.class_name if item.class_schedule else ''

                child_items.append({
                    'id': str(item.id),
                    'productName': item.product.product_name if item.product else '',
                    'brandName': item.product.brand.brand_name if item.product and item.product.brand else '',
                    'brandCode': item.product.brand.brand_code if item.product and item.product.brand else '',
                    'schoolName': item.contract.school.school_name if item.contract and item.contract.school else '',
                    'billingMonth': item.billing_month,
                    'unitPrice': int(unit_price),
                    'discountAmount': int(discount_amount),
                    'finalPrice': int(final_price),
                    # スケジュール情報
                    'dayOfWeek': item.day_of_week,
                    'dayDisplay': day_display,
                    'startTime': time_display,
                    'className': class_name,
                })

                # 在籍情報を集約（月謝アイテムのみ）
                if item.product and item.product.item_type == 'monthly' and item.day_of_week:
                    brand_name = item.product.brand.brand_name if item.product.brand else ''
                    enrollment_key = f"{brand_name}_{item.day_of_week}_{time_display}"
                    if enrollment_key not in [e.get('key') for e in enrollments]:
                        enrollments.append({
                            'key': enrollment_key,
                            'brandName': brand_name,
                            'brandCode': item.product.brand.brand_code if item.product.brand else '',
                            'dayOfWeek': item.day_of_week,
                            'dayDisplay': day_display,
                            'startTime': time_display,
                            'className': class_name,
                            'schoolName': item.contract.school.school_name if item.contract and item.contract.school else '',
                        })

            # 生徒割引
            child_discounts = StudentDiscount.objects.filter(
                student=child,
                deleted_at__isnull=True,
                is_active=True
            ).select_related('brand')

            discount_list = []
            for disc in child_discounts:
                amount = disc.amount or Decimal('0')
                total_discount += abs(amount)
                discount_list.append({
                    'id': str(disc.id),
                    'discountName': disc.discount_name,
                    'amount': int(amount),
                    'discountUnit': disc.discount_unit,
                    'brandName': disc.brand.brand_name if disc.brand else '',
                    'startDate': disc.start_date.isoformat() if disc.start_date else None,
                    'endDate': disc.end_date.isoformat() if disc.end_date else None,
                })

            total_amount += child_total

            children_billing.append({
                'studentId': str(child.id),
                'studentName': child_name,
                'studentNo': child.student_no,
                'status': child.status,
                'gradeText': child.grade_text or (child.grade.grade_name if child.grade else ''),
                'items': child_items,
                'discounts': discount_list,
                'subtotal': int(child_total),
                'enrollments': enrollments,  # 在籍情報（ブランド・曜日・時間）
            })

        # 保護者レベルの割引（兄弟割引など）
        guardian_discounts = StudentDiscount.objects.filter(
            guardian=guardian,
            student__isnull=True,
            deleted_at__isnull=True,
            is_active=True
        ).select_related('brand')

        guardian_discount_list = []
        for disc in guardian_discounts:
            amount = disc.amount or Decimal('0')
            total_discount += abs(amount)
            guardian_discount_list.append({
                'id': str(disc.id),
                'discountName': disc.discount_name,
                'amount': int(amount),
                'discountUnit': disc.discount_unit,
                'brandName': disc.brand.brand_name if disc.brand else '',
                'startDate': disc.start_date.isoformat() if disc.start_date else None,
                'endDate': disc.end_date.isoformat() if disc.end_date else None,
            })

        # FS割引（友達紹介割引）
        fs_discount_list = []
        try:
            fs_discounts = guardian.fs_discounts.filter(status='active')
            for fs in fs_discounts:
                fs_discount_list.append({
                    'id': str(fs.id),
                    'discountType': fs.discount_type,
                    'discountTypeDisplay': fs.get_discount_type_display(),
                    'discountValue': int(fs.discount_value),
                    'status': fs.status,
                    'validFrom': fs.valid_from.isoformat() if fs.valid_from else None,
                    'validUntil': fs.valid_until.isoformat() if fs.valid_until else None,
                })
        except Exception:
            # テーブルが存在しない場合などはスキップ
            pass

        # 口座種別の日本語変換
        account_type_map = {
            'ordinary': '普通',
            'current': '当座',
            'savings': '貯蓄',
        }

        return Response({
            'guardianId': str(guardian.id),
            'guardianName': f"{guardian.last_name}{guardian.first_name}",
            'children': children_billing,
            'guardianDiscounts': guardian_discount_list,
            'fsDiscounts': fs_discount_list,
            'totalAmount': int(total_amount),
            'totalDiscount': int(total_discount),
            'netAmount': int(total_amount - total_discount),
            # 支払い状態
            'paymentMethod': payment_method,
            'paymentMethodDisplay': payment_method_display,
            'isOverdue': overdue_invoices > 0,
            'overdueCount': overdue_invoices,
            'unpaidAmount': int(unpaid_amount),
            # 残高情報（プラス=不足、マイナス=過払い）
            'accountBalance': account_balance,
            'accountBalanceLabel': '過払い' if account_balance < 0 else '不足' if account_balance > 0 else '精算済',
            # 請求・入金履歴
            'invoiceHistory': invoice_history,
            'paymentHistory': payment_history,
            # 銀行口座情報
            'bankAccount': {
                'bankName': guardian.bank_name or '',
                'bankCode': guardian.bank_code or '',
                'branchName': guardian.branch_name or '',
                'branchCode': guardian.branch_code or '',
                'accountType': guardian.account_type or 'ordinary',
                'accountTypeDisplay': account_type_map.get(guardian.account_type, '普通'),
                'accountNumber': guardian.account_number or '',
                'accountHolder': guardian.account_holder or '',
                'accountHolderKana': guardian.account_holder_kana or '',
                'isRegistered': guardian.payment_registered,
                'withdrawalDay': guardian.withdrawal_day,
            },
        })


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

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """休会申請を承認"""
        from apps.contracts.models import StudentItem, Product
        from decimal import Decimal
        from calendar import monthrange

        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみ承認できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 休会日を月末に設定
        suspend_date = instance.suspend_from
        last_day = monthrange(suspend_date.year, suspend_date.month)[1]
        suspend_date = suspend_date.replace(day=last_day)
        instance.suspend_from = suspend_date

        # 生徒のステータスを休会中に変更
        student = instance.student
        student.status = 'suspended'
        student.suspended_date = suspend_date
        student.save()

        # 座席保持の場合は休会費（800円）をStudentItemに追加
        if instance.keep_seat:
            # 休会費用の商品を取得または作成
            suspension_product, _ = Product.objects.get_or_create(
                product_code='SUSPENSION_FEE',
                defaults={
                    'tenant_id': instance.tenant_id,
                    'product_name': '休会費',
                    'item_type': 'other',
                    'price': Decimal('800'),
                    'is_recurring': True,
                }
            )

            # 休会費のStudentItemを作成
            StudentItem.objects.create(
                tenant_id=instance.tenant_id,
                student=student,
                product=suspension_product,
                brand=instance.brand,
                school=instance.school,
                billing_month=instance.suspend_from.strftime('%Y-%m'),
                quantity=1,
                unit_price=Decimal('800'),
                discount_amount=Decimal('0'),
                final_price=Decimal('800'),
                notes=f'休会費（{instance.suspend_from}〜）',
            )
            instance.monthly_fee_during_suspension = Decimal('800')

        # 通常の授業料・教材費を停止（StudentSchoolの終了日は設定しない＝籍は残す）
        # ※請求処理側で休会中の生徒は除外する必要あり

        instance.status = 'approved'
        instance.processed_by = request.user
        instance.processed_at = timezone.now()
        instance.save()

        return Response(SuspensionRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """休会申請を却下"""
        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみ却下できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.status = 'rejected'
        instance.processed_by = request.user
        instance.processed_at = timezone.now()
        instance.rejection_reason = request.data.get('reason', '')
        instance.save()

        return Response(SuspensionRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """休会から復会"""
        instance = self.get_object()
        if instance.status != 'approved':
            return Response(
                {'error': '承認済みの休会のみ復会できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 生徒のステータスを在籍中に戻す
        student = instance.student
        student.status = 'enrolled'
        student.save()

        instance.status = 'resumed'
        instance.suspend_until = timezone.now().date()
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

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """退会申請を承認"""
        from calendar import monthrange

        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみ承認できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 退会日を月末に設定
        withdrawal_date = instance.withdrawal_date
        last_day = monthrange(withdrawal_date.year, withdrawal_date.month)[1]
        withdrawal_date = withdrawal_date.replace(day=last_day)
        instance.withdrawal_date = withdrawal_date

        student = instance.student

        # 生徒のステータスを退会に変更
        student.status = 'withdrawn'
        student.withdrawal_date = withdrawal_date
        student.withdrawal_reason = instance.reason_detail or instance.get_reason_display()
        student.save()

        # StudentSchoolの終了日を設定
        StudentSchool.objects.filter(
            student=student,
            brand=instance.brand,
            school=instance.school,
            deleted_at__isnull=True,
            end_date__isnull=True  # まだ終了日が設定されていないもの
        ).update(end_date=instance.withdrawal_date)

        # StudentEnrollmentも終了
        StudentEnrollment.objects.filter(
            student=student,
            brand=instance.brand,
            school=instance.school,
            deleted_at__isnull=True,
            end_date__isnull=True
        ).update(
            end_date=instance.withdrawal_date,
            status='withdrawn',
            change_type='withdraw'
        )

        instance.status = 'approved'
        instance.processed_by = request.user
        instance.processed_at = timezone.now()
        instance.save()

        return Response(WithdrawalRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """退会申請を却下"""
        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみ却下できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.status = 'rejected'
        instance.processed_by = request.user
        instance.processed_at = timezone.now()
        instance.rejection_reason = request.data.get('reason', '')
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
    # TODO: 本番では IsAuthenticated, IsTenantUser に戻す
    from rest_framework.permissions import AllowAny
    permission_classes = [AllowAny]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        # TODO: 本番ではテナントフィルタを有効にする
        queryset = BankAccountChangeRequest.objects.select_related(
            'guardian', 'existing_account', 'requested_by', 'processed_by'
        )

        # テナントフィルタ（tenant_idがある場合のみ）
        # TODO: 本番環境で有効にする。開発中は全テナントのデータを表示
        # if tenant_id:
        #     queryset = queryset.filter(tenant_id=tenant_id)

        # 保護者の場合は自分の申請のみ
        if hasattr(self.request, 'user') and hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(guardian=guardian)

        # フィルタリング
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 検索
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(guardian__last_name__icontains=search) |
                Q(guardian__first_name__icontains=search) |
                Q(guardian__guardian_no__icontains=search) |
                Q(bank_name__icontains=search) |
                Q(account_holder__icontains=search)
            )

        # リクエストタイプフィルタ
        request_type = self.request.query_params.get('request_type')
        if request_type:
            queryset = queryset.filter(request_type=request_type)

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

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """申請承認 - 古い口座を履歴に保存し、新しい口座をGuardianに反映"""
        from django.utils import timezone

        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみ承認できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        guardian = instance.guardian
        if not guardian:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 古い口座情報をBankAccountテーブルに保存（履歴として）
        if guardian.bank_name and guardian.account_number:
            BankAccount.objects.create(
                tenant_id=guardian.tenant_id,
                tenant_ref_id=guardian.tenant_ref_id,
                guardian=guardian,
                bank_name=guardian.bank_name,
                bank_code=guardian.bank_code or '',
                branch_name=guardian.branch_name or '',
                branch_code=guardian.branch_code or '',
                account_type=guardian.account_type or 'ordinary',
                account_number=guardian.account_number,
                account_holder=guardian.account_holder or '',
                account_holder_kana=guardian.account_holder_kana or '',
                is_primary=False,  # 履歴なのでプライマリではない
                is_active=False,   # 旧口座なので無効
                notes=f'口座変更申請承認により退避 ({timezone.now().strftime("%Y-%m-%d %H:%M")})'
            )

        # 新しい口座情報をGuardianに反映
        if instance.request_type in ('new', 'update'):
            guardian.bank_name = instance.bank_name
            guardian.bank_code = instance.bank_code or ''
            guardian.branch_name = instance.branch_name or ''
            guardian.branch_code = instance.branch_code or ''
            guardian.account_type = instance.account_type or 'ordinary'
            guardian.account_number = instance.account_number
            guardian.account_holder = instance.account_holder or f"{guardian.last_name} {guardian.first_name}"
            guardian.account_holder_kana = instance.account_holder_kana or ''
            guardian.save()
        elif instance.request_type == 'delete':
            # 削除の場合は口座情報をクリア
            guardian.bank_name = ''
            guardian.bank_code = ''
            guardian.branch_name = ''
            guardian.branch_code = ''
            guardian.account_type = ''
            guardian.account_number = ''
            guardian.account_holder = ''
            guardian.account_holder_kana = ''
            guardian.save()

        # 申請を承認済みに
        instance.status = 'approved'
        instance.processed_by = request.user
        instance.processed_at = timezone.now()
        instance.save()

        # 関連タスクを完了に
        from apps.tasks.models import Task
        Task.objects.filter(
            source_type='bank_account_request',
            source_id=instance.id
        ).update(status='completed', completed_at=timezone.now())

        return Response(BankAccountChangeRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """申請却下"""
        from django.utils import timezone

        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみ却下できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.status = 'rejected'
        instance.processed_by = request.user
        instance.processed_at = timezone.now()
        instance.process_notes = request.data.get('reason', '')
        instance.save()

        # 関連タスクを完了に
        from apps.tasks.models import Task
        Task.objects.filter(
            source_type='bank_account_request',
            source_id=instance.id
        ).update(status='completed', completed_at=timezone.now())

        return Response(BankAccountChangeRequestSerializer(instance).data)

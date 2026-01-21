"""
Guardian ViewSet - 保護者管理ViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Q, Exists, OuterRef
from django.db.models.functions import Concat
from django.utils import timezone

from apps.core.permissions import IsTenantUser
from apps.core.csv_utils import CSVMixin
from apps.students.models import Student, Guardian
from apps.students.serializers import (
    GuardianListSerializer, GuardianDetailSerializer, GuardianCreateUpdateSerializer,
    StudentListSerializer,
)
from .mixins import PaymentActionsMixin, BillingActionsMixin, AccountActionsMixin


class GuardianViewSet(
    PaymentActionsMixin,
    BillingActionsMixin,
    AccountActionsMixin,
    CSVMixin,
    viewsets.ModelViewSet
):
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
        ).prefetch_related(
            'children', 'children__primary_school', 'children__primary_brand',
            'contracts', 'contracts__course'
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
            queryset = self._apply_search_filter(queryset, search)

        return queryset

    def _apply_search_filter(self, queryset, search):
        """検索フィルターを適用"""
        # スペースで区切られた検索ワードを分割
        search_terms = search.replace('　', ' ').split()

        # 子供の名前検索用のサブクエリを構築
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
        # タスクはsignalsで自動作成される

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

"""
School Views - 校舎関連
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.db.models import Count
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.exceptions import ValidationException
from apps.core.csv_utils import CSVMixin
from ..models import School
from ..serializers import (
    SchoolListSerializer, SchoolDetailSerializer, SchoolCreateUpdateSerializer,
    ClassroomListSerializer, PublicSchoolSerializer,
)


class SchoolViewSet(CSVMixin, viewsets.ModelViewSet):
    """校舎ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'schools'
    csv_export_fields = [
        'id', 'school_code', 'school_name', 'school_name_short', 'school_type',
        'postal_code', 'prefecture', 'city', 'address1', 'address2',
        'phone', 'fax', 'email', 'latitude', 'longitude',
        'capacity', 'opening_date', 'closing_date',
        'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'id': 'ID',
        'school_code': '校舎コード',
        'school_name': '校舎名',
        'school_name_short': '校舎名略称',
        'school_type': '校舎種別',
        'postal_code': '郵便番号',
        'prefecture': '都道府県',
        'city': '市区町村',
        'address1': '住所1',
        'address2': '住所2',
        'phone': '電話番号',
        'fax': 'FAX番号',
        'email': 'メールアドレス',
        'latitude': '緯度',
        'longitude': '経度',
        'capacity': '定員',
        'opening_date': '開校日',
        'closing_date': '閉校日',
        'sort_order': '表示順',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        'ID': 'id',
        '校舎コード': 'school_code',
        '校舎名': 'school_name',
        '校舎名略称': 'school_name_short',
        '校舎種別': 'school_type',
        '郵便番号': 'postal_code',
        '都道府県': 'prefecture',
        '市区町村': 'city',
        '住所1': 'address1',
        '住所2': 'address2',
        '電話番号': 'phone',
        'FAX番号': 'fax',
        'メールアドレス': 'email',
        '緯度': 'latitude',
        '経度': 'longitude',
        '定員': 'capacity',
        '開校日': 'opening_date',
        '閉校日': 'closing_date',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['校舎コード', '校舎名']
    csv_unique_fields = ['school_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = School.objects.filter(
            deleted_at__isnull=True
        )

        # tenant_idがある場合のみフィルタリング（認証済みユーザー）
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        # フィルタリング（BrandSchool経由でブランドフィルタ）
        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_schools__brand_id=brand_id).distinct()

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return SchoolListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SchoolCreateUpdateSerializer
        return SchoolDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['get'])
    def classrooms(self, request, pk=None):
        """校舎の教室一覧"""
        school = self.get_object()
        classrooms = school.classrooms.filter(is_active=True)
        serializer = ClassroomListSerializer(classrooms, many=True)
        return Response(serializer.data)

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


class PublicSchoolListView(APIView):
    """公開校舎一覧API（認証不要・新規登録用）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        都道府県でフィルタリング可能な校舎一覧を返す
        ?prefecture=東京都
        """
        queryset = School.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        )

        # 都道府県でフィルタリング
        prefecture = request.query_params.get('prefecture')
        if prefecture:
            queryset = queryset.filter(prefecture=prefecture)

        # 市区町村でフィルタリング
        city = request.query_params.get('city')
        if city:
            queryset = queryset.filter(city=city)

        serializer = PublicSchoolSerializer(queryset, many=True)
        return Response(serializer.data)


class PublicPrefectureListView(APIView):
    """公開都道府県一覧API（認証不要・新規登録用）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """校舎が存在する都道府県一覧を返す"""
        prefectures = School.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).exclude(
            prefecture=''
        ).values_list('prefecture', flat=True).distinct().order_by('prefecture')

        return Response(list(prefectures))


class PublicAreaListView(APIView):
    """公開地域（市区町村）一覧API（認証不要・新規登録用）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """校舎が存在する市区町村一覧を返す"""
        queryset = School.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).exclude(city='')

        # 都道府県でフィルタリング
        prefecture = request.query_params.get('prefecture')
        if prefecture:
            queryset = queryset.filter(prefecture=prefecture)

        areas = queryset.values('city').annotate(
            school_count=Count('id')
        ).order_by('city')

        return Response([
            {
                'id': area['city'],
                'name': area['city'],
                'schoolCount': area['school_count'],
            }
            for area in areas
        ])


class PublicSchoolsByAreaView(APIView):
    """地域別校舎一覧API（認証不要・新規登録用）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        地域（市区町村）ごとに校舎一覧を返す
        ?city=渋谷区
        """
        city = request.query_params.get('city')
        if not city:
            raise ValidationException('city パラメータは必須です')

        queryset = School.objects.filter(
            is_active=True,
            deleted_at__isnull=True,
            city=city
        )

        schools = []
        for school in queryset:
            schools.append({
                'id': str(school.id),
                'name': school.school_name,
                'code': school.school_code,
                'address': f"{school.prefecture}{school.city}{school.address1}",
                'phone': school.phone,
            })

        return Response(schools)

"""
Brand Views - ブランド関連
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.db.models import Count
from django.utils import timezone

from django.db.models import Prefetch
from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from ..models import Brand, BrandCategory, BrandSchool
from ..serializers import (
    BrandListSerializer, BrandDetailSerializer, BrandCreateUpdateSerializer,
    PublicBrandCategorySerializer,
)


class BrandViewSet(CSVMixin, viewsets.ModelViewSet):
    """ブランドビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'brands'
    csv_export_fields = [
        'id', 'brand_code', 'brand_name', 'brand_name_short', 'brand_type',
        'description', 'logo_url', 'color_primary', 'color_secondary',
        'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'id': 'ID',
        'brand_code': 'ブランドコード',
        'brand_name': 'ブランド名',
        'brand_name_short': 'ブランド名略称',
        'brand_type': 'ブランド種別',
        'description': '説明',
        'logo_url': 'ロゴURL',
        'color_primary': 'プライマリカラー',
        'color_secondary': 'セカンダリカラー',
        'sort_order': '表示順',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        'ID': 'id',
        'ブランドコード': 'brand_code',
        'ブランド名': 'brand_name',
        'ブランド名略称': 'brand_name_short',
        'ブランド種別': 'brand_type',
        '説明': 'description',
        'ロゴURL': 'logo_url',
        'プライマリカラー': 'color_primary',
        'セカンダリカラー': 'color_secondary',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['ブランドコード', 'ブランド名']
    csv_unique_fields = ['brand_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Brand.objects.filter(deleted_at__isnull=True)

        # tenant_idがある場合のみフィルタリング（認証済みユーザー）
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        if self.action == 'list':
            queryset = queryset.annotate(school_count=Count('brand_schools'))

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return BrandListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return BrandCreateUpdateSerializer
        return BrandDetailSerializer

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


class PublicBrandCategoriesView(APIView):
    """公開ブランドカテゴリ一覧API（認証不要）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        ブランドカテゴリ一覧を返す（各カテゴリにブランドが含まれる）
        """
        active_brands = Brand.objects.filter(
            is_active=True, deleted_at__isnull=True
        ).order_by('sort_order')
        categories = BrandCategory.objects.filter(
            is_active=True
        ).prefetch_related(
            Prefetch('brands', queryset=active_brands, to_attr='active_brands')
        ).order_by('sort_order', 'category_code')

        serializer = PublicBrandCategorySerializer(categories, many=True)
        return Response({
            'data': serializer.data,
            'count': len(serializer.data)
        })


class PublicBrandSchoolsView(APIView):
    """ブランド開講校舎一覧API（認証不要・地図表示用）"""
    permission_classes = [AllowAny]

    def get(self, request, brand_id):
        """
        指定ブランドの開講校舎一覧を緯度・経度付きで返す
        """
        # ブランドコードでも検索可能にする
        brand_schools = BrandSchool.objects.filter(
            is_active=True
        ).select_related('school', 'brand')

        # brand_idがUUIDか文字列（ブランドコード）かを判定
        try:
            from uuid import UUID
            UUID(brand_id)
            brand_schools = brand_schools.filter(brand_id=brand_id)
        except (ValueError, TypeError):
            # UUIDでない場合はブランドコードとして検索
            brand_schools = brand_schools.filter(brand__brand_code__iexact=brand_id)

        schools_data = []
        for bs in brand_schools:
            school = bs.school
            if school.is_active:
                schools_data.append({
                    'id': str(school.id),
                    'name': school.school_name,
                    'nameShort': school.school_name_short or school.school_name[:3],  # 略称または先頭3文字
                    'code': school.school_code,
                    'address': f"{school.prefecture}{school.city}{school.address1}{school.address2}".strip(),
                    'phone': school.phone,
                    'latitude': float(school.latitude) if school.latitude else None,
                    'longitude': float(school.longitude) if school.longitude else None,
                    'isMain': bs.is_main,
                    'sortOrder': bs.sort_order,
                })

        return Response({
            'data': schools_data,
            'count': len(schools_data)
        })


class PublicCategorySchoolsView(APIView):
    """カテゴリ内全ブランドの開講校舎一括取得API（認証不要）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        カテゴリIDを指定して、カテゴリ内全ブランドの開講校舎を一括取得
        ?category_id=xxx でカテゴリフィルタリング
        レスポンス: { data: BrandSchool[], schoolBrandMap: { schoolId: brandId[] }, count: number }
        """
        category_id = request.query_params.get('category_id', '')
        if not category_id:
            return Response({'error': 'category_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # カテゴリに属するブランドの全BrandSchoolを1クエリで取得
        brand_schools = BrandSchool.objects.filter(
            is_active=True,
            brand__category_id=category_id,
            brand__is_active=True,
            brand__deleted_at__isnull=True,
            school__is_active=True,
        ).select_related('school', 'brand')

        # 校舎を重複除去し、校舎ID→ブランドIDマッピングも構築
        school_map = {}  # school_id -> school_data
        school_brand_map = {}  # school_id -> [brand_id, ...]

        for bs in brand_schools:
            school = bs.school
            school_id = str(school.id)
            brand_id = str(bs.brand_id)

            if school_id not in school_map:
                school_map[school_id] = {
                    'id': school_id,
                    'name': school.school_name,
                    'nameShort': school.school_name_short or school.school_name[:3],
                    'code': school.school_code,
                    'address': f"{school.prefecture}{school.city}{school.address1}{school.address2}".strip(),
                    'phone': school.phone,
                    'latitude': float(school.latitude) if school.latitude else None,
                    'longitude': float(school.longitude) if school.longitude else None,
                    'isMain': bs.is_main,
                    'sortOrder': bs.sort_order,
                }

            if school_id not in school_brand_map:
                school_brand_map[school_id] = []
            if brand_id not in school_brand_map[school_id]:
                school_brand_map[school_id].append(brand_id)

        schools_data = sorted(school_map.values(), key=lambda s: (s['sortOrder'] if s['sortOrder'] is not None else 9999, s['name']))

        return Response({
            'data': schools_data,
            'schoolBrandMap': school_brand_map,
            'count': len(schools_data)
        })

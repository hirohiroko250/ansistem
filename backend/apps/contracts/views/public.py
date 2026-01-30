"""
Public Views - 公開API（認証不要・顧客向け）
PublicBrandListView, PublicCourseListView, PublicCourseDetailView, PublicPackListView, PublicPackDetailView
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db.models import Q
from django.core.cache import cache

from ..models import Course, Pack
from apps.core.exceptions import NotFoundError
from ..serializers import PublicCourseSerializer, PublicPackSerializer, PublicBrandSerializer

# キャッシュ有効期間（5分）
CACHE_TTL = 60 * 5


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
        ?brand_ids=xxx,yyy,zzz で複数ブランドフィルタリング（カンマ区切りUUID）
        ?school_id=xxx で校舎フィルタリング（UUIDまたは校舎コード）
        ?grade_name=xxx で学年フィルタリング
        ?limit=xxx で結果を制限（デフォルト500）
        """
        import uuid as uuid_module

        # キャッシュキー生成
        brand_id = request.query_params.get('brand_id', '')
        brand_ids = request.query_params.get('brand_ids', '')
        school_id = request.query_params.get('school_id', '')
        grade_name = request.query_params.get('grade_name', '')
        limit = request.query_params.get('limit', '500')
        try:
            limit = min(int(limit), 1000)  # 最大1000件
        except ValueError:
            limit = 500
        cache_key = f"public_courses:{brand_id}:{brand_ids}:{school_id}:{grade_name}:{limit}"

        # キャッシュから取得
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        # 基本クエリ - 必要なフィールドのみ選択
        queryset = Course.objects.filter(
            is_active=True,
            is_visible=True,  # 保護者に表示するコースのみ
            deleted_at__isnull=True
        ).select_related('brand', 'school', 'grade').prefetch_related(
            'course_items__product__prices',
            'course_tickets__ticket'
        )

        # 複数ブランドでフィルタリング（優先）
        if brand_ids:
            brand_id_list = [bid.strip() for bid in brand_ids.split(',') if bid.strip()]
            if brand_id_list:
                queryset = queryset.filter(brand_id__in=brand_id_list)
        # 単一ブランドでフィルタリング
        elif brand_id:
            # UUIDかブランドコードかを判定
            try:
                uuid_module.UUID(brand_id)
                queryset = queryset.filter(brand_id=brand_id)
            except ValueError:
                # ブランドコードとして処理
                queryset = queryset.filter(brand__brand_code=brand_id)

        # 校舎でフィルタリング（UUIDまたは校舎コード）
        # school_id=NULLのコース（ブランド全体で利用可能）も含める
        if school_id:
            try:
                uuid_module.UUID(school_id)
                queryset = queryset.filter(Q(school_id=school_id) | Q(school_id__isnull=True))
            except ValueError:
                # 校舎コードとして処理
                queryset = queryset.filter(Q(school__school_code=school_id) | Q(school_id__isnull=True))

        # 学年でフィルタリング
        # grade_idがNULLのコース（学年不問）も含める
        # コース名に学年が含まれている場合も対象にする
        if grade_name:
            queryset = queryset.filter(
                Q(grade__grade_name__icontains=grade_name) |
                Q(grade_id__isnull=True, course_name__icontains=grade_name)
            )

        # ソートしてリミット適用
        queryset = queryset.order_by('sort_order', 'course_name')[:limit]
        serializer = PublicCourseSerializer(queryset, many=True)

        # キャッシュに保存
        cache.set(cache_key, serializer.data, CACHE_TTL)

        return Response(serializer.data)


class PublicCourseDetailView(APIView):
    """公開コース詳細API（認証不要・顧客向け）"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        """コース詳細を返す"""
        try:
            course = Course.objects.select_related(
                'brand', 'school', 'grade'
            ).prefetch_related(
                'course_items__product__prices',
                'course_tickets__ticket'
            ).get(
                id=pk,
                is_active=True,
                deleted_at__isnull=True
            )
        except Course.DoesNotExist:
            raise NotFoundError('コースが見つかりません')

        serializer = PublicCourseSerializer(course)
        return Response(serializer.data)


class PublicPackListView(APIView):
    """公開パック一覧API（認証不要・顧客向け）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        有効なパック一覧を返す
        ?brand_id=xxx でブランドフィルタリング（UUIDまたはブランドコード）
        ?brand_ids=xxx,yyy,zzz で複数ブランドフィルタリング（カンマ区切りUUID）
        ?school_id=xxx で校舎フィルタリング（UUIDまたは校舎コード）
        ?grade_name=xxx で学年フィルタリング
        ?limit=xxx で結果を制限（デフォルト500）
        """
        import uuid as uuid_module

        # キャッシュキー生成
        brand_id = request.query_params.get('brand_id', '')
        brand_ids = request.query_params.get('brand_ids', '')
        school_id = request.query_params.get('school_id', '')
        grade_name = request.query_params.get('grade_name', '')
        limit = request.query_params.get('limit', '500')
        try:
            limit = min(int(limit), 1000)  # 最大1000件
        except ValueError:
            limit = 500
        cache_key = f"public_packs:{brand_id}:{brand_ids}:{school_id}:{grade_name}:{limit}"

        # キャッシュから取得
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        queryset = Pack.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).select_related('brand', 'school', 'grade').prefetch_related(
            'pack_courses__course__course_items__product',
            'pack_courses__course__course_tickets__ticket',
            'pack_tickets__ticket'
        )

        # 複数ブランドでフィルタリング（優先）
        if brand_ids:
            brand_id_list = [bid.strip() for bid in brand_ids.split(',') if bid.strip()]
            if brand_id_list:
                queryset = queryset.filter(brand_id__in=brand_id_list)
        # 単一ブランドでフィルタリング
        elif brand_id:
            try:
                uuid_module.UUID(brand_id)
                queryset = queryset.filter(brand_id=brand_id)
            except ValueError:
                # ブランドコードとして処理
                queryset = queryset.filter(brand__brand_code=brand_id)

        # 校舎でフィルタリング（UUIDまたは校舎コード）
        # school_id=NULLのパック（ブランド全体で利用可能）も含める
        if school_id:
            try:
                uuid_module.UUID(school_id)
                queryset = queryset.filter(Q(school_id=school_id) | Q(school_id__isnull=True))
            except ValueError:
                # 校舎コードとして処理
                queryset = queryset.filter(Q(school__school_code=school_id) | Q(school_id__isnull=True))

        # 学年でフィルタリング
        # grade_idがNULLのパック（学年不問）も含める
        # パック名に学年が含まれている場合も対象にする
        if grade_name:
            queryset = queryset.filter(
                Q(grade__grade_name__icontains=grade_name) |
                Q(grade_id__isnull=True, pack_name__icontains=grade_name)
            )

        # ソートしてリミット適用
        queryset = queryset.order_by('sort_order', 'pack_name')[:limit]
        serializer = PublicPackSerializer(queryset, many=True)

        # キャッシュに保存
        cache.set(cache_key, serializer.data, CACHE_TTL)

        return Response(serializer.data)


class PublicPackDetailView(APIView):
    """公開パック詳細API（認証不要・顧客向け）"""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        """パック詳細を返す"""
        try:
            pack = Pack.objects.select_related(
                'brand', 'school', 'grade'
            ).prefetch_related(
                'pack_courses__course__course_items__product',
                'pack_courses__course__course_tickets__ticket',
                'pack_tickets__ticket'
            ).get(
                id=pk,
                is_active=True,
                deleted_at__isnull=True
            )
        except Pack.DoesNotExist:
            raise NotFoundError('パックが見つかりません')

        serializer = PublicPackSerializer(pack)
        return Response(serializer.data)

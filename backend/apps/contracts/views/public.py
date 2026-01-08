"""
Public Views - 公開API（認証不要・顧客向け）
PublicBrandListView, PublicCourseListView, PublicCourseDetailView, PublicPackListView, PublicPackDetailView
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db.models import Q

from ..models import Course, Pack
from ..serializers import PublicCourseSerializer, PublicPackSerializer, PublicBrandSerializer


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
        ).select_related('brand', 'school', 'grade').prefetch_related(
            'course_items__product__prices',
            'course_tickets__ticket'
        )

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
            ).prefetch_related(
                'course_items__product__prices',
                'course_tickets__ticket'
            ).get(
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
        ).select_related('brand', 'school', 'grade').prefetch_related(
            'pack_courses__course__course_items__product',
            'pack_courses__course__course_tickets__ticket',
            'pack_tickets__ticket'
        )

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
            return Response({'error': 'Pack not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PublicPackSerializer(pack)
        return Response(serializer.data)

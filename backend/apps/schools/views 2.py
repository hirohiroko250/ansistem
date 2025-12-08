"""
Schools Views
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
from apps.core.csv_utils import CSVMixin
from .models import Brand, School, Grade, Subject, Classroom, TimeSlot, SchoolSchedule, SchoolCourse, SchoolClosure
from .serializers import (
    BrandListSerializer, BrandDetailSerializer, BrandCreateUpdateSerializer,
    SchoolListSerializer, SchoolDetailSerializer, SchoolCreateUpdateSerializer,
    GradeSerializer, SubjectSerializer,
    ClassroomListSerializer, ClassroomDetailSerializer,
    PublicSchoolSerializer,
    TimeSlotSerializer,
    SchoolScheduleListSerializer, SchoolScheduleDetailSerializer, SchoolScheduleCreateUpdateSerializer,
    SchoolCourseListSerializer, SchoolCourseDetailSerializer,
    SchoolClosureListSerializer, SchoolClosureDetailSerializer, SchoolClosureCreateUpdateSerializer,
)


class BrandViewSet(CSVMixin, viewsets.ModelViewSet):
    """ブランドビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'brands'
    csv_export_fields = [
        'brand_code', 'brand_name', 'brand_name_short', 'brand_type',
        'description', 'logo_url', 'color_primary', 'color_secondary',
        'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
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
        queryset = Brand.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)

        if self.action == 'list':
            queryset = queryset.annotate(school_count=Count('schools'))

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return BrandListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return BrandCreateUpdateSerializer
        return BrandDetailSerializer

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


class SchoolViewSet(CSVMixin, viewsets.ModelViewSet):
    """校舎ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'schools'
    csv_export_fields = [
        'school_code', 'school_name', 'school_name_short', 'school_type',
        'brand.brand_code', 'brand.brand_name',
        'postal_code', 'prefecture', 'city', 'address1', 'address2',
        'phone', 'fax', 'email', 'latitude', 'longitude',
        'capacity', 'opening_date', 'closing_date',
        'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'school_code': '校舎コード',
        'school_name': '校舎名',
        'school_name_short': '校舎名略称',
        'school_type': '校舎種別',
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
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
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('brand')

        # フィルタリング
        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

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


class GradeViewSet(CSVMixin, viewsets.ModelViewSet):
    """学年ビューセット"""
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'grades'
    csv_export_fields = [
        'grade_code', 'grade_name', 'grade_name_short', 'category',
        'school_year', 'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'grade_code': '学年コード',
        'grade_name': '学年名',
        'grade_name_short': '学年名略称',
        'category': 'カテゴリ',
        'school_year': '学校学年',
        'sort_order': '表示順',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '学年コード': 'grade_code',
        '学年名': 'grade_name',
        '学年名略称': 'grade_name_short',
        'カテゴリ': 'category',
        '学校学年': 'school_year',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['学年コード', '学年名']
    csv_unique_fields = ['grade_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Grade.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset

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


class SubjectViewSet(CSVMixin, viewsets.ModelViewSet):
    """教科ビューセット"""
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'subjects'
    csv_export_fields = [
        'subject_code', 'subject_name', 'subject_name_short', 'category',
        'color', 'icon', 'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'subject_code': '教科コード',
        'subject_name': '教科名',
        'subject_name_short': '教科名略称',
        'category': 'カテゴリ',
        'color': '表示色',
        'icon': 'アイコン',
        'sort_order': '表示順',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '教科コード': 'subject_code',
        '教科名': 'subject_name',
        '教科名略称': 'subject_name_short',
        'カテゴリ': 'category',
        '表示色': 'color',
        'アイコン': 'icon',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['教科コード', '教科名']
    csv_unique_fields = ['subject_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Subject.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset

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
        ).select_related('brand')

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
            return Response({'error': 'city parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = School.objects.filter(
            is_active=True,
            deleted_at__isnull=True,
            city=city
        ).prefetch_related('brands')

        schools = []
        for school in queryset:
            brand_names = [b.brand_name for b in school.brands.all()]
            schools.append({
                'id': str(school.id),
                'name': school.school_name,
                'code': school.school_code,
                'address': f"{school.prefecture}{school.city}{school.address1}",
                'phone': school.phone,
                'brands': brand_names,
            })

        return Response(schools)


class ClassroomViewSet(CSVMixin, viewsets.ModelViewSet):
    """教室ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'classrooms'
    csv_export_fields = [
        'classroom_code', 'classroom_name', 'school.school_code', 'school.school_name',
        'capacity', 'floor', 'room_type', 'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'classroom_code': '教室コード',
        'classroom_name': '教室名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'capacity': '定員',
        'floor': '階数',
        'room_type': '教室種別',
        'sort_order': '表示順',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '教室コード': 'classroom_code',
        '教室名': 'classroom_name',
        '定員': 'capacity',
        '階数': 'floor',
        '教室種別': 'room_type',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['教室コード', '教室名']
    csv_unique_fields = ['classroom_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Classroom.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('school')

        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ClassroomListSerializer
        return ClassroomDetailSerializer

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


# ========================================
# TimeSlot（時間帯）
# ========================================
class TimeSlotViewSet(CSVMixin, viewsets.ModelViewSet):
    """時間帯ビューセット"""
    serializer_class = TimeSlotSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'time_slots'
    csv_export_fields = [
        'slot_code', 'slot_name', 'start_time', 'end_time',
        'duration_minutes', 'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'slot_code': '時間帯コード',
        'slot_name': '時間帯名',
        'start_time': '開始時刻',
        'end_time': '終了時刻',
        'duration_minutes': '時間（分）',
        'sort_order': '表示順',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '時間帯コード': 'slot_code',
        '時間帯名': 'slot_name',
        '開始時刻': 'start_time',
        '終了時刻': 'end_time',
        '時間（分）': 'duration_minutes',
        '表示順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['時間帯コード', '時間帯名', '開始時刻', '終了時刻']
    csv_unique_fields = ['slot_code']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return TimeSlot.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)

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
    def import_csv_data(self, request):
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def csv_template(self, request):
        return self.get_csv_template(request)


# ========================================
# SchoolSchedule（校舎開講スケジュール）
# ========================================
class SchoolScheduleViewSet(CSVMixin, viewsets.ModelViewSet):
    """校舎開講スケジュールビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'school_schedules'
    csv_export_fields = [
        'brand.brand_code', 'brand.brand_name',
        'school.school_code', 'school.school_name',
        'day_of_week', 'time_slot.slot_code', 'time_slot.slot_name',
        'capacity', 'reserved_seats', 'valid_from', 'valid_until',
        'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'day_of_week': '曜日（1=月〜7=日）',
        'time_slot.slot_code': '時間帯コード',
        'time_slot.slot_name': '時間帯名',
        'capacity': '定員（席数）',
        'reserved_seats': '予約済み席数',
        'valid_from': '有効開始日',
        'valid_until': '有効終了日',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        'ブランドコード': 'brand_code',
        '校舎コード': 'school_code',
        '曜日（1=月〜7=日）': 'day_of_week',
        '時間帯コード': 'time_slot_code',
        '定員（席数）': 'capacity',
        '予約済み席数': 'reserved_seats',
        '有効開始日': 'valid_from',
        '有効終了日': 'valid_until',
        '有効': 'is_active',
    }
    csv_required_fields = ['ブランドコード', '校舎コード', '曜日（1=月〜7=日）', '時間帯コード']
    csv_unique_fields = []

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = SchoolSchedule.objects.filter(
            tenant_id=tenant_id, deleted_at__isnull=True
        ).select_related('brand', 'school', 'time_slot')

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        day_of_week = self.request.query_params.get('day_of_week')
        if day_of_week:
            queryset = queryset.filter(day_of_week=day_of_week)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return SchoolScheduleListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SchoolScheduleCreateUpdateSerializer
        return SchoolScheduleDetailSerializer

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
    def import_csv_data(self, request):
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def csv_template(self, request):
        return self.get_csv_template(request)


# ========================================
# SchoolCourse（校舎別コース）
# ========================================
class SchoolCourseViewSet(CSVMixin, viewsets.ModelViewSet):
    """校舎別コースビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'school_courses'
    csv_export_fields = [
        'school.school_code', 'school.school_name',
        'course.course_code', 'course.course_name',
        'capacity_override', 'valid_from', 'valid_until',
        'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'course.course_code': 'コースコード',
        'course.course_name': 'コース名',
        'capacity_override': '席数上書き',
        'valid_from': '開講開始日',
        'valid_until': '開講終了日',
        'is_active': '有効',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '校舎コード': 'school_code',
        'コースコード': 'course_code',
        '席数上書き': 'capacity_override',
        '開講開始日': 'valid_from',
        '開講終了日': 'valid_until',
        '有効': 'is_active',
    }
    csv_required_fields = ['校舎コード', 'コースコード']
    csv_unique_fields = []

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = SchoolCourse.objects.filter(
            tenant_id=tenant_id, deleted_at__isnull=True
        ).select_related('school', 'course', 'schedule')

        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return SchoolCourseListSerializer
        return SchoolCourseDetailSerializer

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
    def import_csv_data(self, request):
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def csv_template(self, request):
        return self.get_csv_template(request)


# ========================================
# SchoolClosure（休講）
# ========================================
class SchoolClosureViewSet(CSVMixin, viewsets.ModelViewSet):
    """休講ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [MultiPartParser, FormParser]

    csv_filename_prefix = 'school_closures'
    csv_export_fields = [
        'school.school_code', 'school.school_name',
        'brand.brand_code', 'brand.brand_name',
        'closure_date', 'closure_type',
        'has_makeup', 'makeup_date', 'reason', 'tenant_id'
    ]
    csv_export_headers = {
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'closure_date': '休講日',
        'closure_type': '休講種別',
        'has_makeup': '振替あり',
        'makeup_date': '振替日',
        'reason': '休講理由',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '校舎コード': 'school_code',
        'ブランドコード': 'brand_code',
        '休講日': 'closure_date',
        '休講種別': 'closure_type',
        '振替あり': 'has_makeup',
        '振替日': 'makeup_date',
        '休講理由': 'reason',
    }
    csv_required_fields = ['休講日']
    csv_unique_fields = []

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = SchoolClosure.objects.filter(
            tenant_id=tenant_id, deleted_at__isnull=True
        ).select_related('school', 'brand', 'schedule')

        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(closure_date__gte=date_from)
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(closure_date__lte=date_to)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return SchoolClosureListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SchoolClosureCreateUpdateSerializer
        return SchoolClosureDetailSerializer

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
    def import_csv_data(self, request):
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def csv_template(self, request):
        return self.get_csv_template(request)

    @action(detail=False, methods=['get'])
    def check(self, request):
        """指定日時が休講かどうかチェック"""
        from datetime import datetime

        school_id = request.query_params.get('school_id')
        brand_id = request.query_params.get('brand_id')
        date_str = request.query_params.get('date')
        time_slot_id = request.query_params.get('time_slot_id')

        if not all([school_id, brand_id, date_str]):
            return Response(
                {'error': 'school_id, brand_id, date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        school = School.objects.filter(id=school_id).first()
        brand = Brand.objects.filter(id=brand_id).first()
        time_slot = TimeSlot.objects.filter(id=time_slot_id).first() if time_slot_id else None

        if not school or not brand:
            return Response({'error': 'School or Brand not found'}, status=status.HTTP_404_NOT_FOUND)

        is_closed = SchoolClosure.is_closed(school, brand, check_date, time_slot)
        return Response({
            'is_closed': is_closed,
            'school': school.school_name,
            'brand': brand.brand_name,
            'date': date_str,
            'time_slot': time_slot.slot_name if time_slot else None
        })

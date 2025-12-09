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
from .models import Brand, BrandCategory, School, Grade, Subject, Classroom, TimeSlot, SchoolSchedule, SchoolCourse, SchoolClosure, BrandSchool, LessonCalendar
from .serializers import (
    BrandListSerializer, BrandDetailSerializer, BrandCreateUpdateSerializer,
    BrandCategorySerializer, PublicBrandCategorySerializer,
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
        'id', 'school_code', 'school_name', 'school_name_short', 'school_type',
        'brand.brand_code', 'brand.brand_name',
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
        'id', 'grade_code', 'grade_name', 'grade_name_short', 'category',
        'school_year', 'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'id': 'ID',
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
        'ID': 'id',
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
        'id', 'subject_code', 'subject_name', 'subject_name_short', 'category',
        'color', 'icon', 'sort_order', 'is_active', 'tenant_id'
    ]
    csv_export_headers = {
        'id': 'ID',
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
        'ID': 'id',
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


class PublicBrandCategoriesView(APIView):
    """公開ブランドカテゴリ一覧API（認証不要）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        ブランドカテゴリ一覧を返す（各カテゴリにブランドが含まれる）
        """
        categories = BrandCategory.objects.filter(
            is_active=True
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


class PublicLessonCalendarView(APIView):
    """開講カレンダーAPI（認証不要・保護者向け）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        指定月の開講カレンダーを返す
        ?brand_id=xxx&school_id=xxx&year=2024&month=12
        """
        from datetime import date
        import calendar as cal

        brand_id = request.query_params.get('brand_id')
        school_id = request.query_params.get('school_id')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not all([brand_id, school_id, year, month]):
            return Response(
                {'error': 'brand_id, school_id, year, month are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return Response(
                {'error': 'year and month must be integers'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 月の開始日と終了日
        first_day = date(year, month, 1)
        last_day = date(year, month, cal.monthrange(year, month)[1])

        calendars = LessonCalendar.objects.filter(
            brand_id=brand_id,
            school_id=school_id,
            lesson_date__gte=first_day,
            lesson_date__lte=last_day
        ).order_by('lesson_date')

        calendar_data = []
        for item in calendars:
            calendar_data.append({
                'date': item.lesson_date.isoformat(),
                'dayOfWeek': item.day_of_week,
                'isOpen': item.is_open,
                'lessonType': item.lesson_type,
                'displayLabel': item.display_label,
                'ticketType': item.ticket_type,
                'ticketSequence': item.ticket_sequence,
                'noticeMessage': item.notice_message,
                'holidayName': item.holiday_name,
                'isNativeDay': item.lesson_type == 'A',  # Aパターン = 外国人講師あり
                'isJapaneseOnly': item.lesson_type == 'B',  # Bパターン = 日本人講師のみ
            })

        return Response({
            'year': year,
            'month': month,
            'brandId': brand_id,
            'schoolId': school_id,
            'calendar': calendar_data
        })


class PublicTrialScheduleView(APIView):
    """体験授業スケジュールAPI（認証不要）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        指定ブランド・校舎の体験可能スケジュールを返す
        ?brand_id=xxx&school_id=xxx
        または
        ?school_id=xxx（全ブランド）
        """
        brand_id = request.query_params.get('brand_id')
        school_id = request.query_params.get('school_id')

        if not school_id:
            return Response(
                {'error': 'school_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # SchoolScheduleから曜日・時間帯を取得
        queryset = SchoolSchedule.objects.filter(
            school_id=school_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('brand', 'time_slot')

        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        # 曜日変換
        day_names = {1: '月曜日', 2: '火曜日', 3: '水曜日', 4: '木曜日', 5: '金曜日', 6: '土曜日', 7: '日曜日'}

        # 曜日ごとにグループ化
        schedule_by_day = {}
        for sched in queryset:
            day_name = day_names.get(sched.day_of_week, str(sched.day_of_week))
            if day_name not in schedule_by_day:
                schedule_by_day[day_name] = []

            time_str = f"{sched.time_slot.start_time.strftime('%H:%M')}-{sched.time_slot.end_time.strftime('%H:%M')}"

            # 体験受入可能数を確認
            available = sched.trial_capacity if sched.trial_capacity else 2  # デフォルト2名

            schedule_by_day[day_name].append({
                'id': str(sched.id),
                'time': time_str,
                'timeSlotId': str(sched.time_slot.id),
                'timeSlotName': sched.time_slot.slot_name,
                'capacity': sched.capacity,
                'trialCapacity': available,
                'brandId': str(sched.brand.id),
                'brandName': sched.brand.brand_name,
            })

        # レスポンス形式
        schedule_list = []
        for day, times in schedule_by_day.items():
            schedule_list.append({
                'day': day,
                'times': times
            })

        return Response({
            'schoolId': school_id,
            'brandId': brand_id,
            'schedule': schedule_list
        })


class PublicTrialAvailabilityView(APIView):
    """体験枠空き状況API（日付指定・認証不要）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        指定日の体験枠空き状況を返す
        ?school_id=xxx&brand_id=xxx&date=2024-12-25
        """
        from datetime import datetime
        from apps.students.models import TrialBooking

        school_id = request.query_params.get('school_id')
        brand_id = request.query_params.get('brand_id')
        date_str = request.query_params.get('date')

        if not all([school_id, brand_id, date_str]):
            return Response(
                {'error': 'school_id, brand_id, date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 曜日を取得（1=月曜日）
        day_of_week = target_date.isoweekday()

        # LessonCalendarで休校日かチェック
        calendar_entry = LessonCalendar.objects.filter(
            brand_id=brand_id,
            school_id=school_id,
            lesson_date=target_date
        ).first()

        if calendar_entry and not calendar_entry.is_open:
            return Response({
                'date': date_str,
                'isAvailable': False,
                'reason': 'closed',
                'holidayName': calendar_entry.holiday_name or '休講日',
                'slots': []
            })

        # SchoolScheduleから該当曜日のスケジュールを取得
        schedules = SchoolSchedule.objects.filter(
            school_id=school_id,
            brand_id=brand_id,
            day_of_week=day_of_week,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('time_slot')

        slots = []
        for sched in schedules:
            # 体験予約済み数を取得
            booked_count = TrialBooking.get_booked_count(sched.id, target_date)
            trial_capacity = sched.trial_capacity or 2
            available_count = max(0, trial_capacity - booked_count)

            time_str = f"{sched.time_slot.start_time.strftime('%H:%M')}-{sched.time_slot.end_time.strftime('%H:%M')}"

            slots.append({
                'scheduleId': str(sched.id),
                'timeSlotId': str(sched.time_slot.id),
                'timeSlotName': sched.time_slot.slot_name,
                'time': time_str,
                'trialCapacity': trial_capacity,
                'bookedCount': booked_count,
                'availableCount': available_count,
                'isAvailable': available_count > 0,
            })

        return Response({
            'date': date_str,
            'schoolId': school_id,
            'brandId': brand_id,
            'isAvailable': any(s['isAvailable'] for s in slots),
            'slots': slots
        })


class PublicTrialBookingView(APIView):
    """体験予約API（認証必要）"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        体験予約を作成
        {
            "student_id": "xxx",
            "school_id": "xxx",
            "brand_id": "xxx",
            "schedule_id": "xxx",
            "trial_date": "2024-12-25",
            "notes": "備考"
        }
        """
        from datetime import datetime
        from apps.students.models import Student, Guardian, TrialBooking
        from apps.tasks.models import Task

        student_id = request.data.get('student_id')
        school_id = request.data.get('school_id')
        brand_id = request.data.get('brand_id')
        schedule_id = request.data.get('schedule_id')
        date_str = request.data.get('trial_date')
        notes = request.data.get('notes', '')

        # バリデーション
        if not all([student_id, school_id, brand_id, schedule_id, date_str]):
            return Response(
                {'error': 'student_id, school_id, brand_id, schedule_id, trial_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            trial_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 生徒を取得（保護者のみアクセス可能）
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        # スケジュールを取得
        try:
            schedule = SchoolSchedule.objects.select_related('school', 'brand', 'time_slot').get(id=schedule_id)
        except SchoolSchedule.DoesNotExist:
            return Response({'error': 'Schedule not found'}, status=status.HTTP_404_NOT_FOUND)

        # LessonCalendarで休校日かチェック
        calendar_entry = LessonCalendar.objects.filter(
            brand_id=brand_id,
            school_id=school_id,
            lesson_date=trial_date
        ).first()

        if calendar_entry and not calendar_entry.is_open:
            return Response(
                {'error': f'{trial_date}は休講日です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 空き状況チェック
        trial_capacity = schedule.trial_capacity or 2
        if not TrialBooking.is_available(schedule_id, trial_date, trial_capacity):
            return Response(
                {'error': 'この日時は満席です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 既に予約済みかチェック
        existing = TrialBooking.objects.filter(
            student_id=student_id,
            trial_date=trial_date,
            schedule_id=schedule_id,
            status__in=[TrialBooking.Status.PENDING, TrialBooking.Status.CONFIRMED]
        ).exists()

        if existing:
            return Response(
                {'error': 'この日時は既に予約済みです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 保護者を取得
        guardian = None
        if hasattr(request.user, 'guardian_profile'):
            guardian = request.user.guardian_profile

        # テナントIDを取得
        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id and guardian:
            tenant_id = guardian.tenant_id
        if not tenant_id:
            tenant_id = student.tenant_id

        # 体験予約を作成
        booking = TrialBooking.objects.create(
            tenant_id=tenant_id,
            student=student,
            guardian=guardian,
            school=schedule.school,
            brand=schedule.brand,
            trial_date=trial_date,
            schedule=schedule,
            time_slot=schedule.time_slot,
            status=TrialBooking.Status.PENDING,
            notes=notes,
        )

        # 作業一覧にタスクを作成
        time_str = f"{schedule.time_slot.start_time.strftime('%H:%M')}-{schedule.time_slot.end_time.strftime('%H:%M')}"
        task = Task.objects.create(
            tenant_id=tenant_id,
            task_type='trial_registration',
            title=f'体験予約: {student.full_name} ({trial_date} {time_str})',
            description=f'生徒: {student.full_name}\n校舎: {schedule.school.school_name}\nブランド: {schedule.brand.brand_name}\n日時: {trial_date} {time_str}\n備考: {notes}',
            status='new',
            priority='normal',
            school=schedule.school,
            brand=schedule.brand,
            student=student,
            guardian=guardian,
            source_type='trial_booking',
            source_id=booking.id,
        )

        # 体験予約にタスクIDを保存
        booking.task_id_ref = task.id
        booking.save()

        # 生徒のステータスを「体験」に更新
        if student.status == Student.Status.REGISTERED:
            student.status = Student.Status.TRIAL
            student.trial_date = trial_date
            student.save()

        return Response({
            'id': str(booking.id),
            'studentId': str(student.id),
            'studentName': student.full_name,
            'schoolId': str(schedule.school.id),
            'schoolName': schedule.school.school_name,
            'brandId': str(schedule.brand.id),
            'brandName': schedule.brand.brand_name,
            'trialDate': trial_date.isoformat(),
            'time': time_str,
            'status': booking.status,
            'taskId': str(task.id),
            'message': '体験予約が完了しました'
        }, status=status.HTTP_201_CREATED)

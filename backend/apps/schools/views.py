"""
Schools Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.db.models import Count, Q
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.csv_utils import CSVMixin
from .models import Brand, BrandCategory, School, Grade, Subject, Classroom, TimeSlot, SchoolSchedule, SchoolCourse, SchoolClosure, BrandSchool, LessonCalendar, ClassSchedule, BankType, Bank, BankBranch
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
    BankTypeSerializer, BankSerializer, BankDetailSerializer, BankBranchSerializer,
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
            deleted_at__isnull=True
        )

        # tenant_idがある場合のみフィルタリング（認証済みユーザー）
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

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
    """体験授業スケジュールAPI（認証不要）

    機能:
    - 学年フィルター: birth_dateから学年を計算し、対象学年に合うクラスのみ返す
    - 外国人講師チェック: LessonCalendarでlesson_type='B'（日本人のみ）の日は除外
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        指定ブランド・校舎の体験可能スケジュールを返す
        ?brand_id=xxx&school_id=xxx
        ?birth_date=YYYY-MM-DD (オプション: 学年フィルター用)
        または
        ?school_id=xxx（全ブランド）
        """
        from datetime import datetime, date

        brand_id = request.query_params.get('brand_id')
        school_id = request.query_params.get('school_id')
        birth_date_str = request.query_params.get('birth_date')

        if not school_id:
            return Response(
                {'error': 'school_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 生年月日から学年コードを計算
        child_school_year = None
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                # ブランドの学年計算ロジックを使用
                brand = None
                if brand_id:
                    brand = Brand.objects.filter(id=brand_id).first()
                if brand:
                    child_school_year = brand.calculate_school_year(birth_date)
            except ValueError:
                pass  # 無効な日付形式は無視

        # ClassScheduleから曜日・時間帯を取得（実際のクラス開講情報）
        queryset = ClassSchedule.objects.filter(
            school_id=school_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('brand', 'grade')

        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        # 学年フィルター: 子供の学年が対象学年に含まれるクラスのみ
        if child_school_year:
            # gradeがNULLのスケジュールは全学年対象として扱う
            # gradeがある場合は、school_yearsに子供の学年が含まれるか確認
            filtered_schedules = []
            for sched in queryset:
                if sched.grade is None:
                    # 学年指定なし → 全学年対象
                    filtered_schedules.append(sched)
                else:
                    # 学年指定あり → 子供の学年が含まれるか確認
                    grade_school_years = sched.grade.school_years.all()
                    if child_school_year in grade_school_years:
                        filtered_schedules.append(sched)
            queryset = filtered_schedules
        else:
            queryset = list(queryset)

        # 曜日変換
        day_names = {1: '月曜日', 2: '火曜日', 3: '水曜日', 4: '木曜日', 5: '金曜日', 6: '土曜日', 7: '日曜日'}

        # 曜日ごとにグループ化（重複排除）
        schedule_by_day = {}
        seen_slots = set()  # 同じ曜日+時間帯の重複を排除

        for sched in queryset:
            day_name = day_names.get(sched.day_of_week, str(sched.day_of_week))
            time_key = f"{sched.day_of_week}_{sched.start_time}_{sched.end_time}_{sched.brand_id}"

            if time_key in seen_slots:
                continue
            seen_slots.add(time_key)

            if day_name not in schedule_by_day:
                schedule_by_day[day_name] = []

            time_str = f"{sched.start_time.strftime('%H:%M')}-{sched.end_time.strftime('%H:%M')}"

            # 体験受入可能数（定員 - 既存予約数）
            capacity = sched.max_students if hasattr(sched, 'max_students') and sched.max_students else 10
            trial_capacity = getattr(sched, 'trial_capacity', 2) or 2

            schedule_by_day[day_name].append({
                'id': str(sched.id),
                'time': time_str,
                'startTime': sched.start_time.strftime('%H:%M'),
                'endTime': sched.end_time.strftime('%H:%M'),
                'className': sched.class_name,
                'capacity': capacity,
                'trialCapacity': trial_capacity,
                'brandId': str(sched.brand.id),
                'brandName': sched.brand.brand_name,
                'gradeName': sched.grade.grade_name if sched.grade else None,
            })

        # レスポンス形式（曜日順にソート）
        day_order = {'月曜日': 1, '火曜日': 2, '水曜日': 3, '木曜日': 4, '金曜日': 5, '土曜日': 6, '日曜日': 7}
        schedule_list = []
        for day in sorted(schedule_by_day.keys(), key=lambda x: day_order.get(x, 99)):
            times = schedule_by_day[day]
            # 時間順にソート
            times.sort(key=lambda x: x['startTime'])
            schedule_list.append({
                'day': day,
                'times': times
            })

        return Response({
            'schoolId': school_id,
            'brandId': brand_id,
            'childSchoolYear': child_school_year.year_name if child_school_year else None,
            'schedule': schedule_list
        })


class PublicTrialAvailabilityView(APIView):
    """体験枠空き状況API（日付指定・認証不要）

    機能:
    - LessonCalendarで休講日チェック
    - 外国人講師チェック: lesson_type='B'（日本人のみ）の日は体験不可
    """
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

        # ClassScheduleからcalendar_patternを取得
        class_schedules = ClassSchedule.objects.filter(
            school_id=school_id,
            brand_id=brand_id,
            day_of_week=day_of_week,
            is_active=True,
            deleted_at__isnull=True
        )
        calendar_patterns = set(cs.calendar_pattern for cs in class_schedules if cs.calendar_pattern)

        # LessonCalendarで休校日・外国人講師チェック
        # calendar_patternがあればそれで、なければbrand+schoolで検索
        calendar_entry = None
        is_japanese_only = False

        if calendar_patterns:
            # カレンダーパターンでLessonCalendarを検索
            for pattern in calendar_patterns:
                entry = LessonCalendar.objects.filter(
                    calendar_code=pattern,
                    lesson_date=target_date
                ).first()
                if entry:
                    calendar_entry = entry
                    # 日本人講師のみの日かチェック（lesson_type='B'）
                    if entry.lesson_type == 'B':
                        is_japanese_only = True
                    break

        if not calendar_entry:
            # カレンダーパターンがない場合は従来通りbrand+schoolで検索
            calendar_entry = LessonCalendar.objects.filter(
                brand_id=brand_id,
                school_id=school_id,
                lesson_date=target_date
            ).first()
            if calendar_entry and calendar_entry.lesson_type == 'B':
                is_japanese_only = True

        # 休講日チェック
        if calendar_entry and not calendar_entry.is_open:
            return Response({
                'date': date_str,
                'isAvailable': False,
                'reason': 'closed',
                'holidayName': calendar_entry.holiday_name or '休講日',
                'slots': []
            })

        # 日本人講師のみの日は体験不可
        if is_japanese_only:
            return Response({
                'date': date_str,
                'isAvailable': False,
                'reason': 'japanese_only',
                'message': 'この日は日本人講師のみのため体験授業は受け付けておりません',
                'lessonType': 'B',
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
            'lessonType': calendar_entry.lesson_type if calendar_entry else None,
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


class PublicClassScheduleView(APIView):
    """開講時間割API（認証不要・保護者向け）
    
    校舎・ブランドごとの開講時間割を曜日・時限でグループ化して返す
    クラス選択画面やクラス登録画面で使用
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        指定校舎・ブランドの開講時間割を返す
        ?school_id=xxx&brand_id=xxx
        または
        ?school_id=xxx&brand_category_id=xxx（ブランドカテゴリで絞り込み）
        または
        ?school_id=xxx&ticket_id=xxx（チケットIDで絞り込み）
        """
        school_id = request.query_params.get('school_id')
        brand_id = request.query_params.get('brand_id')
        brand_category_id = request.query_params.get('brand_category_id')
        ticket_id = request.query_params.get('ticket_id')

        if not school_id:
            return Response(
                {'error': 'school_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ClassScheduleから開講時間割を取得
        queryset = ClassSchedule.objects.filter(
            school_id=school_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('brand', 'brand_category', 'school', 'room')

        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        if brand_category_id:
            queryset = queryset.filter(brand_category_id=brand_category_id)
        if ticket_id:
            # チケットIDから同じtransfer_groupのスケジュールを取得
            # まず指定チケットIDのtransfer_groupを取得
            ticket_schedule = ClassSchedule.objects.filter(ticket_id=ticket_id).first()
            if ticket_schedule and ticket_schedule.transfer_group:
                # transfer_groupでフィルタリング（同じクラスグループを表示）
                queryset = queryset.filter(transfer_group=ticket_schedule.transfer_group)
            else:
                # ClassScheduleにチケットがない場合、Ticketテーブルから名前を取得してtransfer_groupで検索
                from apps.contracts.models import Ticket
                ticket = Ticket.objects.filter(ticket_code=ticket_id).first()
                if ticket and ticket.ticket_name:
                    # チケット名からクラス名を抽出（例："Red ネイティブ" -> "Red"）
                    class_names = ['White', 'Yellow', 'Red', 'Purple', 'Kids', 'Jr', 'ジュニア', 'キッズ']
                    transfer_group = None
                    for name in class_names:
                        if name in ticket.ticket_name:
                            transfer_group = name
                            break
                    if transfer_group:
                        queryset = queryset.filter(transfer_group=transfer_group)
                    else:
                        # 見つからない場合は従来通りticket_idでフィルタリング
                        queryset = queryset.filter(ticket_id=ticket_id)
                else:
                    # Ticketも見つからない場合は従来通り
                    queryset = queryset.filter(ticket_id=ticket_id)

        # 曜日名マッピング
        day_names = {1: '月曜日', 2: '火曜日', 3: '水曜日', 4: '木曜日', 5: '金曜日', 6: '土曜日', 7: '日曜日'}
        day_short_names = {1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'}

        # 時間帯ごとにグループ化
        schedules_by_time = {}
        for sched in queryset.order_by('day_of_week', 'period', 'start_time'):
            start_hour = sched.start_time.strftime('%H:00') if sched.start_time else '00:00'
            
            if start_hour not in schedules_by_time:
                schedules_by_time[start_hour] = {day: [] for day in range(1, 8)}
            
            schedule_data = {
                'id': str(sched.id),
                'scheduleCode': sched.schedule_code,
                'className': sched.class_name,
                'classType': sched.class_type,
                'displayCourseName': sched.display_course_name,
                'displayPairName': sched.display_pair_name,
                'displayDescription': sched.display_description,
                'period': sched.period,
                'startTime': sched.start_time.strftime('%H:%M') if sched.start_time else None,
                'endTime': sched.end_time.strftime('%H:%M') if sched.end_time else None,
                'durationMinutes': sched.duration_minutes,
                'capacity': sched.capacity,
                'trialCapacity': sched.trial_capacity,
                'reservedSeats': sched.reserved_seats,
                'availableSeats': max(0, sched.capacity - sched.reserved_seats),
                'transferGroup': sched.transfer_group,
                'calendarPattern': sched.calendar_pattern,
                'approvalType': sched.approval_type,
                'roomName': sched.room.classroom_name if sched.room else sched.room_name,
                'brandId': str(sched.brand.id) if sched.brand else None,
                'brandName': sched.brand.brand_name if sched.brand else None,
                'brandCategoryId': str(sched.brand_category.id) if sched.brand_category else None,
                'brandCategoryName': sched.brand_category.category_name if sched.brand_category else None,
                'ticketName': sched.ticket_name,
                'ticketId': sched.ticket_id,
                'gradeCode': getattr(sched, 'grade', None) and sched.grade.grade_code if hasattr(sched, 'grade') and sched.grade else None,
                'gradeName': getattr(sched, 'grade', None) and sched.grade.grade_name if hasattr(sched, 'grade') and sched.grade else None,
            }
            schedules_by_time[start_hour][sched.day_of_week].append(schedule_data)

        # レスポンス形式に変換
        time_slots_response = []
        for time_key in sorted(schedules_by_time.keys()):
            day_schedules = schedules_by_time[time_key]
            # 曜日ごとの状況を計算
            days_availability = {}
            for day_num in range(1, 8):
                schedules_for_day = day_schedules[day_num]
                if not schedules_for_day:
                    days_availability[day_short_names[day_num]] = {
                        'status': 'none',  # 開講なし
                        'schedules': []
                    }
                else:
                    total_capacity = sum(s['capacity'] for s in schedules_for_day)
                    total_reserved = sum(s['reservedSeats'] for s in schedules_for_day)
                    available = total_capacity - total_reserved
                    
                    if available <= 0:
                        slot_status = 'full'  # 満席
                    elif available <= 2:
                        slot_status = 'few'  # 残りわずか
                    else:
                        slot_status = 'available'  # 空席あり
                    
                    days_availability[day_short_names[day_num]] = {
                        'status': slot_status,
                        'totalCapacity': total_capacity,
                        'totalReserved': total_reserved,
                        'availableSeats': available,
                        'schedules': schedules_for_day
                    }
            
            time_slots_response.append({
                'time': time_key,
                'days': days_availability
            })

        return Response({
            'schoolId': school_id,
            'brandId': brand_id,
            'brandCategoryId': brand_category_id,
            'timeSlots': time_slots_response,
            'dayLabels': ['月', '火', '水', '木', '金', '土', '日']
        })


class PublicSchoolsByTicketView(APIView):
    """チケットが開講している校舎一覧API（認証不要）

    特定のチケットIDに対して、開講時間割が存在する校舎の一覧を返す
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        ?ticket_id=Ti10000063 でチケットIDを指定
        ?brand_id=xxx でブランドフィルタリング（オプション）
        """
        ticket_id = request.query_params.get('ticket_id')
        brand_id = request.query_params.get('brand_id')

        if not ticket_id:
            return Response(
                {'error': 'ticket_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ClassScheduleから該当チケットが開講している校舎を取得
        queryset = ClassSchedule.objects.filter(
            ticket_id=ticket_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('school')

        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        # 校舎のユニーク取得
        school_ids = queryset.values_list('school_id', flat=True).distinct()
        schools = School.objects.filter(id__in=school_ids, deleted_at__isnull=True).order_by('school_name')

        result = []
        for school in schools:
            # 住所を結合
            address_parts = [
                school.prefecture or '',
                school.city or '',
                school.address1 or '',
                school.address2 or '',
                school.address3 or ''
            ]
            full_address = ''.join(part for part in address_parts if part)

            result.append({
                'id': str(school.id),
                'name': school.school_name,
                'code': school.school_code,
                'address': full_address,
                'phone': school.phone or '',
                'latitude': float(school.latitude) if school.latitude else None,
                'longitude': float(school.longitude) if school.longitude else None,
            })

        return Response(result)


class PublicTicketsBySchoolView(APIView):
    """校舎で開講しているチケット一覧API（認証不要）

    特定の校舎IDに対して、開講時間割が存在するチケットIDの一覧を返す
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        ?school_id=xxx で校舎IDを指定
        """
        school_id = request.query_params.get('school_id')

        if not school_id:
            return Response(
                {'error': 'school_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ClassScheduleから該当校舎で開講しているチケットを取得
        ticket_ids = ClassSchedule.objects.filter(
            school_id=school_id,
            is_active=True,
            deleted_at__isnull=True
        ).values_list('ticket_id', flat=True).distinct()

        # ticket_id形式（Ti10000063）からコード部分を抽出してリストで返す
        result = list(set(ticket_ids))

        return Response({
            'schoolId': school_id,
            'ticketIds': result
        })


class PublicTrialMonthlyAvailabilityView(APIView):
    """体験予約月間空き状況API（認証不要）

    指定月の各日の体験枠空き状況を返す
    カレンダー上で体験可能な日を表示するために使用
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        ?school_id=xxx&brand_id=xxx&year=2025&month=12
        """
        from datetime import date
        import calendar as cal
        from apps.students.models import TrialBooking

        school_id = request.query_params.get('school_id')
        brand_id = request.query_params.get('brand_id')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not all([school_id, brand_id, year, month]):
            return Response(
                {'error': 'school_id, brand_id, year, month are required'},
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

        # 校舎・ブランドのスケジュールを取得
        schedules = SchoolSchedule.objects.filter(
            school_id=school_id,
            brand_id=brand_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('time_slot')

        # 曜日ごとのスケジュールをまとめる
        schedules_by_day = {}
        for sched in schedules:
            if sched.day_of_week not in schedules_by_day:
                schedules_by_day[sched.day_of_week] = []
            schedules_by_day[sched.day_of_week].append(sched)

        # LessonCalendarで休講日を取得
        closures = LessonCalendar.objects.filter(
            brand_id=brand_id,
            school_id=school_id,
            lesson_date__gte=first_day,
            lesson_date__lte=last_day,
            is_open=False
        ).values_list('lesson_date', flat=True)
        closure_dates = set(closures)

        # 日付ごとの空き状況を計算
        daily_availability = []
        current_date = first_day
        while current_date <= last_day:
            day_of_week = current_date.isoweekday()  # 1=月曜日

            day_data = {
                'date': current_date.isoformat(),
                'dayOfWeek': day_of_week,
                'isOpen': True,
                'totalCapacity': 0,
                'bookedCount': 0,
                'availableCount': 0,
                'isAvailable': False,
            }

            # 休講日チェック
            if current_date in closure_dates:
                day_data['isOpen'] = False
                day_data['reason'] = 'closed'
                daily_availability.append(day_data)
                current_date = date(current_date.year, current_date.month, current_date.day + 1) if current_date.day < last_day.day else last_day
                if current_date > last_day:
                    break
                # 次の日に進む
                next_day = current_date.day + 1
                if next_day > cal.monthrange(year, month)[1]:
                    break
                current_date = date(year, month, next_day)
                continue

            # 当該曜日のスケジュールがあるか
            if day_of_week in schedules_by_day:
                day_schedules = schedules_by_day[day_of_week]
                total_capacity = 0
                total_booked = 0

                for sched in day_schedules:
                    trial_cap = sched.trial_capacity or 2
                    total_capacity += trial_cap
                    booked = TrialBooking.get_booked_count(sched.id, current_date)
                    total_booked += booked

                available = max(0, total_capacity - total_booked)
                day_data['totalCapacity'] = total_capacity
                day_data['bookedCount'] = total_booked
                day_data['availableCount'] = available
                day_data['isAvailable'] = available > 0
            else:
                # 開講曜日ではない
                day_data['isOpen'] = False
                day_data['reason'] = 'no_schedule'

            daily_availability.append(day_data)

            # 次の日に進む
            next_day = current_date.day + 1
            if next_day > cal.monthrange(year, month)[1]:
                break
            current_date = date(year, month, next_day)

        return Response({
            'year': year,
            'month': month,
            'schoolId': school_id,
            'brandId': brand_id,
            'days': daily_availability
        })


class PublicTrialStatsView(APIView):
    """体験予約統計API（認証不要）

    学年・ブランドカテゴリ・校舎ごとの体験予約人数を集計して返す
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        体験予約の統計情報を返す
        ?group_by=grade|brand_category|school (デフォルト: grade)
        ?year=2025&month=12 (オプション：期間指定)
        """
        from datetime import date
        import calendar as cal
        from django.db.models import Count, Q
        from apps.students.models import TrialBooking, Student

        group_by = request.query_params.get('group_by', 'grade')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        # 基本クエリ：キャンセル以外の体験予約
        queryset = TrialBooking.objects.exclude(
            status=TrialBooking.Status.CANCELLED
        ).select_related('student', 'school', 'brand')

        # 期間フィルタ
        if year and month:
            try:
                year = int(year)
                month = int(month)
                first_day = date(year, month, 1)
                last_day = date(year, month, cal.monthrange(year, month)[1])
                queryset = queryset.filter(trial_date__gte=first_day, trial_date__lte=last_day)
            except (ValueError, TypeError):
                pass

        result = []

        if group_by == 'grade':
            # 学年ごとに集計
            grades = Grade.objects.filter(is_active=True).order_by('sort_order')

            for grade in grades:
                # この学年の生徒の体験予約数
                count = queryset.filter(student__grade=grade).count()
                result.append({
                    'id': str(grade.id),
                    'code': grade.grade_code,
                    'name': grade.grade_name,
                    'shortName': grade.grade_name_short,
                    'category': grade.category,
                    'trialCount': count,
                })

            # 学年未設定の体験予約
            no_grade_count = queryset.filter(
                Q(student__grade__isnull=True) | Q(student__isnull=True)
            ).count()
            if no_grade_count > 0:
                result.append({
                    'id': None,
                    'code': 'none',
                    'name': '未設定',
                    'shortName': '未設定',
                    'category': None,
                    'trialCount': no_grade_count,
                })

        elif group_by == 'brand_category':
            # ブランドカテゴリごとに集計
            categories = BrandCategory.objects.filter(is_active=True).order_by('sort_order')

            for category in categories:
                # このカテゴリのブランドのIDを取得
                brand_ids = Brand.objects.filter(category=category).values_list('id', flat=True)
                count = queryset.filter(brand_id__in=brand_ids).count()
                result.append({
                    'id': str(category.id),
                    'code': category.category_code,
                    'name': category.category_name,
                    'trialCount': count,
                })

            # カテゴリなしブランドの体験予約
            no_category_brands = Brand.objects.filter(category__isnull=True).values_list('id', flat=True)
            no_category_count = queryset.filter(brand_id__in=no_category_brands).count()
            if no_category_count > 0:
                result.append({
                    'id': None,
                    'code': 'none',
                    'name': '未分類',
                    'trialCount': no_category_count,
                })

        elif group_by == 'school':
            # 校舎ごとに集計
            schools = School.objects.filter(is_active=True, deleted_at__isnull=True).order_by('school_name')

            for school in schools:
                count = queryset.filter(school=school).count()
                result.append({
                    'id': str(school.id),
                    'code': school.school_code,
                    'name': school.school_name,
                    'prefecture': school.prefecture,
                    'city': school.city,
                    'trialCount': count,
                })

        # 合計
        total_count = queryset.count()

        return Response({
            'groupBy': group_by,
            'year': year,
            'month': month,
            'totalCount': total_count,
            'stats': result
        })


class PublicCalendarSeatsView(APIView):
    """通常授業月間座席状況API（認証不要）

    指定月の各日の座席状況を返す
    受講生と残り席数を表示するために使用
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        ?school_id=xxx&brand_id=xxx&year=2025&month=12
        """
        from datetime import date
        import calendar as cal
        from apps.lessons.models import Attendance

        school_id = request.query_params.get('school_id')
        brand_id = request.query_params.get('brand_id')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not all([school_id, brand_id, year, month]):
            return Response(
                {'error': 'school_id, brand_id, year, month are required'},
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

        # ClassScheduleから校舎・ブランドの開講時間割を取得
        class_schedules = ClassSchedule.objects.filter(
            school_id=school_id,
            brand_id=brand_id,
            is_active=True,
            deleted_at__isnull=True
        )

        # 曜日ごとの時間割をまとめる
        schedules_by_day = {}
        for sched in class_schedules:
            if sched.day_of_week not in schedules_by_day:
                schedules_by_day[sched.day_of_week] = []
            schedules_by_day[sched.day_of_week].append(sched)

        # LessonCalendarで休講日を取得
        lesson_cal = LessonCalendar.objects.filter(
            brand_id=brand_id,
            school_id=school_id,
            lesson_date__gte=first_day,
            lesson_date__lte=last_day
        )
        lesson_cal_dict = {lc.lesson_date: lc for lc in lesson_cal}

        # 日付ごとの座席状況を計算
        daily_seats = []
        current_date = first_day
        while current_date <= last_day:
            day_of_week = current_date.isoweekday()  # 1=月曜日

            day_data = {
                'date': current_date.isoformat(),
                'dayOfWeek': day_of_week,
                'isOpen': True,
                'totalCapacity': 0,
                'enrolledCount': 0,
                'availableSeats': 0,
                'lessonType': None,
                'ticketType': None,
                'holidayName': None,
            }

            # LessonCalendarから授業情報を取得
            cal_entry = lesson_cal_dict.get(current_date)
            if cal_entry:
                day_data['isOpen'] = cal_entry.is_open
                day_data['lessonType'] = cal_entry.lesson_type
                day_data['ticketType'] = cal_entry.ticket_type
                day_data['holidayName'] = cal_entry.holiday_name

                if not cal_entry.is_open:
                    daily_seats.append(day_data)
                    next_day = current_date.day + 1
                    if next_day > cal.monthrange(year, month)[1]:
                        break
                    current_date = date(year, month, next_day)
                    continue

            # 当該曜日の時間割があるか
            if day_of_week in schedules_by_day:
                day_schedules = schedules_by_day[day_of_week]
                total_capacity = 0
                total_enrolled = 0

                for sched in day_schedules:
                    total_capacity += sched.capacity
                    total_enrolled += sched.reserved_seats or 0

                day_data['totalCapacity'] = total_capacity
                day_data['enrolledCount'] = total_enrolled
                day_data['availableSeats'] = max(0, total_capacity - total_enrolled)
            else:
                # 開講曜日ではない
                day_data['isOpen'] = False

            daily_seats.append(day_data)

            # 次の日に進む
            next_day = current_date.day + 1
            if next_day > cal.monthrange(year, month)[1]:
                break
            current_date = date(year, month, next_day)

        return Response({
            'year': year,
            'month': month,
            'schoolId': school_id,
            'brandId': brand_id,
            'days': daily_seats
        })


# ========================================
# Admin Calendar API（管理者用カレンダー）
# ========================================
class AdminCalendarView(APIView):
    """管理者用カレンダーAPI

    ClassSchedule（基本時間割）とLessonCalendar（日別情報）を
    組み合わせてカレンダーデータを返す。
    出欠情報、ABスワップ、休校日も含む。
    """
    permission_classes = [AllowAny]  # TODO: IsAuthenticated に変更

    def get(self, request):
        """
        指定月のカレンダーデータを返す
        ?school_id=xxx&year=2024&month=12
        ?brand_id=xxx (オプション)
        """
        from datetime import date, timedelta
        import calendar as cal
        from apps.lessons.models import Attendance
        from apps.students.models import StudentEnrollment

        school_id = request.query_params.get('school_id')
        brand_id = request.query_params.get('brand_id')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not all([school_id, year, month]):
            return Response(
                {'error': 'school_id, year, month are required'},
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

        first_day = date(year, month, 1)
        last_day = date(year, month, cal.monthrange(year, month)[1])

        # ClassScheduleを取得
        schedules_qs = ClassSchedule.objects.filter(
            school_id=school_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('brand', 'brand_category', 'room', 'grade')

        if brand_id:
            schedules_qs = schedules_qs.filter(brand_id=brand_id)

        # 曜日ごとにスケジュールをグループ化
        schedules_by_day = {}
        for sched in schedules_qs:
            if sched.day_of_week not in schedules_by_day:
                schedules_by_day[sched.day_of_week] = []
            schedules_by_day[sched.day_of_week].append(sched)

        # LessonCalendarを取得（calendar_patternごと）
        calendar_patterns = set(s.calendar_pattern for s in schedules_qs if s.calendar_pattern)
        lesson_calendars = LessonCalendar.objects.filter(
            lesson_date__gte=first_day,
            lesson_date__lte=last_day
        ).filter(
            Q(calendar_code__in=calendar_patterns) |
            Q(school_id=school_id)
        )
        lesson_cal_dict = {}
        for lc in lesson_calendars:
            key = (lc.lesson_date, lc.calendar_code or f"{lc.school_id}_{lc.brand_id}")
            lesson_cal_dict[key] = lc

        # SchoolClosureを取得
        closures = SchoolClosure.objects.filter(
            school_id=school_id,
            closure_date__gte=first_day,
            closure_date__lte=last_day,
            deleted_at__isnull=True
        )
        if brand_id:
            closures = closures.filter(Q(brand_id=brand_id) | Q(brand_id__isnull=True))
        closure_dates = {c.closure_date: c for c in closures}

        # StudentEnrollmentを取得（各クラスの受講者数）
        enrollments = StudentEnrollment.objects.filter(
            class_schedule__school_id=school_id,
            status='enrolled',
            deleted_at__isnull=True
        ).values('class_schedule_id').annotate(count=Count('id'))
        enrollment_counts = {e['class_schedule_id']: e['count'] for e in enrollments}

        # 日付ごとのカレンダーデータを生成
        calendar_data = []
        current_date = first_day
        day_names = {1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'}

        while current_date <= last_day:
            day_of_week = current_date.isoweekday()
            is_weekend = day_of_week in [6, 7]

            day_data = {
                'date': current_date.isoformat(),
                'day': current_date.day,
                'dayOfWeek': day_of_week,
                'dayName': day_names.get(day_of_week, ''),
                'isWeekend': is_weekend,
                'isClosed': False,
                'closureReason': None,
                'events': [],
            }

            # 休校日チェック
            closure = closure_dates.get(current_date)
            if closure:
                day_data['isClosed'] = True
                day_data['closureReason'] = closure.reason

            # 該当曜日のスケジュールを取得
            day_schedules = schedules_by_day.get(day_of_week, [])

            for sched in day_schedules:
                # LessonCalendarからlesson_type取得
                cal_key = (current_date, sched.calendar_pattern) if sched.calendar_pattern else None
                lesson_cal = lesson_cal_dict.get(cal_key) if cal_key else None

                # 開講チェック
                is_open = True
                lesson_type = 'A'  # デフォルト
                if lesson_cal:
                    is_open = lesson_cal.is_open
                    lesson_type = lesson_cal.lesson_type or 'A'
                if closure and not closure.schedule_id:
                    is_open = False

                if not is_open:
                    continue

                # 受講者数
                enrolled_count = enrollment_counts.get(sched.id, 0)

                event_data = {
                    'id': str(sched.id),
                    'scheduleCode': sched.schedule_code,
                    'className': sched.class_name,
                    'displayCourseName': sched.display_course_name,
                    'startTime': sched.start_time.strftime('%H:%M') if sched.start_time else None,
                    'endTime': sched.end_time.strftime('%H:%M') if sched.end_time else None,
                    'period': sched.period,
                    'brandId': str(sched.brand.id) if sched.brand else None,
                    'brandName': sched.brand.brand_name if sched.brand else None,
                    'brandColor': sched.brand.color_primary if sched.brand else None,
                    'lessonType': lesson_type,
                    'lessonTypeLabel': {
                        'A': '外国人あり',
                        'B': '日本人のみ',
                        'P': 'ペア',
                        'Y': 'インター',
                    }.get(lesson_type, lesson_type),
                    'capacity': sched.capacity,
                    'enrolledCount': enrolled_count,
                    'availableSeats': max(0, sched.capacity - enrolled_count),
                    'roomName': sched.room.classroom_name if sched.room else sched.room_name,
                    'calendarPattern': sched.calendar_pattern,
                    'ticketName': sched.ticket_name,
                }
                day_data['events'].append(event_data)

            # イベントを時間順にソート
            day_data['events'].sort(key=lambda x: x['startTime'] or '00:00')

            calendar_data.append(day_data)
            current_date += timedelta(days=1)

        return Response({
            'year': year,
            'month': month,
            'schoolId': school_id,
            'brandId': brand_id,
            'days': calendar_data
        })


class AdminCalendarEventDetailView(APIView):
    """管理者用カレンダーイベント詳細API

    特定のクラス×日付の詳細情報（受講者一覧、出欠状況）を返す。
    """
    permission_classes = [AllowAny]  # TODO: IsAuthenticated に変更

    def get(self, request):
        """
        ?schedule_id=xxx&date=2024-12-25
        """
        from datetime import datetime
        from apps.lessons.models import Attendance
        from apps.students.models import StudentEnrollment, Student

        schedule_id = request.query_params.get('schedule_id')
        date_str = request.query_params.get('date')

        if not all([schedule_id, date_str]):
            return Response(
                {'error': 'schedule_id and date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ClassScheduleを取得
        try:
            schedule = ClassSchedule.objects.select_related(
                'brand', 'school', 'room', 'grade'
            ).get(id=schedule_id)
        except ClassSchedule.DoesNotExist:
            return Response({'error': 'Schedule not found'}, status=status.HTTP_404_NOT_FOUND)

        # LessonCalendarからlesson_type取得
        lesson_cal = LessonCalendar.objects.filter(
            lesson_date=target_date,
            calendar_code=schedule.calendar_pattern
        ).first() if schedule.calendar_pattern else None

        lesson_type = lesson_cal.lesson_type if lesson_cal else 'A'

        # このクラスに登録されている生徒一覧（対象日時点で有効なenrollmentのみ）
        from django.db.models import Q
        enrollments = StudentEnrollment.objects.filter(
            class_schedule_id=schedule_id,
            status='enrolled',
            deleted_at__isnull=True,
            effective_date__lte=target_date,  # 適用開始日が対象日以前
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=target_date)  # 終了日が未設定または対象日以降
        ).select_related('student', 'student__guardian').order_by(
            'student__grade_text',  # 学年順
            'student__last_name_kana',  # 名前カナ順
            'student__first_name_kana'
        )

        # AbsenceTicketから欠席情報を取得
        from apps.lessons.models import AbsenceTicket
        absent_tickets = AbsenceTicket.objects.filter(
            class_schedule_id=schedule_id,
            absence_date=target_date,
            deleted_at__isnull=True
        ).values_list('student_id', flat=True)
        absent_student_ids = set(str(sid) for sid in absent_tickets)

        # 出欠記録を取得（当日分）
        attendance_dict = {}
        # AbsenceTicketがある生徒は欠席扱い

        students_list = []
        present_count = 0
        absent_count = 0

        for enrollment in enrollments:
            student = enrollment.student
            if not student:
                continue

            # AbsenceTicketで欠席判定
            student_id_str = str(student.id)
            if student_id_str in absent_student_ids:
                status_value = 'absent'
                absent_count += 1
            else:
                status_value = 'unknown'

            students_list.append({
                'id': str(student.id),
                'studentNo': student.student_no,
                'name': f"{student.last_name}{student.first_name}",
                'nameKana': f"{student.last_name_kana}{student.first_name_kana}",
                'grade': student.grade_text,
                'guardianName': f"{student.guardian.last_name}{student.guardian.first_name}" if student.guardian else None,
                'guardianPhone': student.guardian.phone if student.guardian else None,
                'enrollmentType': enrollment.change_type,  # change_typeを使用
                'attendanceStatus': status_value,
            })

        # StudentEnrollmentがない場合、StudentSchoolから生徒を取得（フォールバック）
        if not students_list and schedule.school_id and schedule.brand_id:
            from apps.students.models import StudentSchool
            student_schools = StudentSchool.objects.filter(
                school_id=schedule.school_id,
                brand_id=schedule.brand_id,
                enrollment_status='active',
                deleted_at__isnull=True
            ).select_related('student', 'student__guardian').order_by(
                'student__grade_text',  # 学年順
                'student__last_name_kana',  # 名前カナ順
                'student__first_name_kana'
            )

            # グレードでフィルタ（クラスにグレードが設定されている場合）
            if schedule.grade_id:
                student_schools = student_schools.filter(student__grade_id=schedule.grade_id)

            for ss in student_schools:
                student = ss.student
                if not student or student.status != 'enrolled':
                    continue

                # AbsenceTicketで欠席判定
                student_id_str = str(student.id)
                if student_id_str in absent_student_ids:
                    status_value = 'absent'
                    absent_count += 1
                else:
                    status_value = 'unknown'

                students_list.append({
                    'id': str(student.id),
                    'studentNo': student.student_no,
                    'name': f"{student.last_name}{student.first_name}",
                    'nameKana': f"{student.last_name_kana or ''}{student.first_name_kana or ''}",
                    'grade': student.grade_text,
                    'guardianName': f"{student.guardian.last_name}{student.guardian.first_name}" if student.guardian else None,
                    'guardianPhone': student.guardian.phone if student.guardian else None,
                    'enrollmentType': 'school_fallback',  # フォールバック識別用
                    'attendanceStatus': status_value,
                })

        return Response({
            'scheduleId': schedule_id,
            'date': date_str,
            'schedule': {
                'className': schedule.class_name,
                'displayCourseName': schedule.display_course_name,
                'startTime': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                'endTime': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                'brandName': schedule.brand.brand_name if schedule.brand else None,
                'schoolName': schedule.school.school_name if schedule.school else None,
                'roomName': schedule.room.classroom_name if schedule.room else schedule.room_name,
                'capacity': schedule.capacity,
                'lessonType': lesson_type,
                'lessonTypeLabel': {
                    'A': '外国人あり',
                    'B': '日本人のみ',
                    'P': 'ペア',
                    'Y': 'インター',
                }.get(lesson_type, lesson_type),
                'calendarPattern': schedule.calendar_pattern,
            },
            'summary': {
                'totalEnrolled': len(students_list),
                'presentCount': present_count,
                'absentCount': absent_count,
                'unknownCount': len(students_list) - present_count - absent_count,
            },
            'students': students_list
        })


class AdminMarkAttendanceView(APIView):
    """管理者用出欠登録API

    出席/欠席を登録する。
    欠席の場合はAbsenceTicketを作成する。
    """
    permission_classes = [AllowAny]  # TODO: IsAuthenticated に変更

    def post(self, request):
        from datetime import datetime as dt, timedelta
        from apps.students.models import Student
        from apps.lessons.models import AbsenceTicket
        from apps.contracts.models import Ticket

        student_id = request.data.get('student_id')
        schedule_id = request.data.get('schedule_id')
        date_str = request.data.get('date')
        status = request.data.get('status')  # 'present' or 'absent'
        reason = request.data.get('reason', '')

        if not all([student_id, schedule_id, date_str, status]):
            return Response(
                {'error': 'student_id, schedule_id, date, status are required'},
                status=400
            )

        if status not in ['present', 'absent']:
            return Response(
                {'error': 'status must be "present" or "absent"'},
                status=400
            )

        try:
            target_date = dt.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=400
            )

        # 生徒取得
        try:
            student = Student.objects.get(id=student_id, deleted_at__isnull=True)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=404)

        # ClassSchedule取得
        try:
            schedule = ClassSchedule.objects.get(id=schedule_id)
        except ClassSchedule.DoesNotExist:
            return Response({'error': 'Schedule not found'}, status=404)

        if status == 'absent':
            # 既存のAbsenceTicketを確認
            existing_ticket = AbsenceTicket.objects.filter(
                student=student,
                class_schedule_id=schedule_id,
                absence_date=target_date,
                deleted_at__isnull=True
            ).first()

            if existing_ticket:
                return Response({
                    'success': True,
                    'message': '既に欠席登録されています',
                    'absence_ticket_id': str(existing_ticket.id),
                })

            # ClassScheduleからticket_idで消化記号を取得
            consumption_symbol = ''
            original_ticket = None
            if schedule.ticket_id:
                try:
                    original_ticket = Ticket.objects.get(
                        ticket_code=schedule.ticket_id,
                        deleted_at__isnull=True
                    )
                    consumption_symbol = original_ticket.consumption_symbol or ''
                except Ticket.DoesNotExist:
                    pass

            # 有効期限: 欠席日から90日
            valid_until = target_date + timedelta(days=90)

            # AbsenceTicketを作成
            absence_ticket = AbsenceTicket.objects.create(
                tenant_id=student.tenant_id,
                student=student,
                original_ticket=original_ticket,
                consumption_symbol=consumption_symbol,
                absence_date=target_date,
                class_schedule=schedule,
                status='issued',
                valid_until=valid_until,
                notes=reason or '管理画面からの欠席登録',
            )

            return Response({
                'success': True,
                'message': '欠席を登録しました。欠席チケットが発行されました。',
                'absence_ticket_id': str(absence_ticket.id),
                'consumption_symbol': consumption_symbol,
                'valid_until': valid_until.isoformat(),
            })
        else:
            # 出席の場合は、既存のAbsenceTicketがあれば削除
            AbsenceTicket.objects.filter(
                student=student,
                class_schedule_id=schedule_id,
                absence_date=target_date,
                status='issued',
                deleted_at__isnull=True
            ).delete()

            return Response({
                'success': True,
                'message': '出席を登録しました。',
            })


class AdminAbsenceTicketListView(APIView):
    """管理者用欠席チケット一覧API

    特定日付・スケジュールの欠席チケットを取得する。
    """
    permission_classes = [AllowAny]  # TODO: IsAuthenticated に変更

    def get(self, request):
        from apps.lessons.models import AbsenceTicket

        schedule_id = request.query_params.get('schedule_id')
        date_str = request.query_params.get('date')
        student_ids = request.query_params.getlist('student_id')

        queryset = AbsenceTicket.objects.filter(deleted_at__isnull=True)

        if schedule_id:
            queryset = queryset.filter(class_schedule_id=schedule_id)

        if date_str:
            try:
                from datetime import datetime as dt
                target_date = dt.strptime(date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(absence_date=target_date)
            except ValueError:
                pass

        if student_ids:
            queryset = queryset.filter(student_id__in=student_ids)

        queryset = queryset.select_related('student', 'class_schedule')

        tickets = []
        for ticket in queryset:
            tickets.append({
                'id': str(ticket.id),
                'studentId': str(ticket.student_id),
                'studentName': f'{ticket.student.last_name}{ticket.student.first_name}' if ticket.student else '',
                'absenceDate': ticket.absence_date.isoformat() if ticket.absence_date else None,
                'status': ticket.status,
                'consumptionSymbol': ticket.consumption_symbol,
                'validUntil': ticket.valid_until.isoformat() if ticket.valid_until else None,
                'notes': ticket.notes,
                'createdAt': ticket.created_at.isoformat() if ticket.created_at else None,
            })

        return Response(tickets)


# ========================================
# Bank（金融機関）API
# ========================================
class PublicBankTypesView(APIView):
    """金融機関種別一覧API（認証不要）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """金融機関種別の一覧を返す"""
        bank_types = BankType.objects.filter(is_active=True).order_by('sort_order')
        serializer = BankTypeSerializer(bank_types, many=True)
        return Response(serializer.data)


class PublicBanksView(APIView):
    """金融機関一覧API（認証不要）

    フロントエンドのbank-selector.tsxから呼び出される。
    あいうえお行と金融機関種別でフィルタリング可能。
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        金融機関一覧を返す
        ?aiueo_row=あ (あいうえお行フィルター)
        ?bank_type_id=xxx (金融機関種別フィルター)
        """
        queryset = Bank.objects.filter(is_active=True).select_related('bank_type')

        # あいうえお行でフィルタリング
        aiueo_row = request.query_params.get('aiueo_row')
        if aiueo_row:
            queryset = queryset.filter(aiueo_row=aiueo_row)

        # 金融機関種別でフィルタリング
        bank_type_id = request.query_params.get('bank_type_id')
        if bank_type_id:
            queryset = queryset.filter(bank_type_id=bank_type_id)

        queryset = queryset.order_by('sort_order', 'bank_name_hiragana')
        serializer = BankSerializer(queryset, many=True)
        return Response(serializer.data)


class PublicBankDetailView(APIView):
    """金融機関詳細API（認証不要・支店一覧含む）"""
    permission_classes = [AllowAny]

    def get(self, request, bank_id):
        """
        金融機関の詳細と支店一覧を返す
        """
        try:
            bank = Bank.objects.select_related('bank_type').prefetch_related('branches').get(id=bank_id)
        except Bank.DoesNotExist:
            return Response({'error': 'Bank not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = BankDetailSerializer(bank)
        return Response(serializer.data)


class PublicBankBranchesView(APIView):
    """支店一覧API（認証不要）

    指定した金融機関の支店一覧を返す。
    あいうえお行でフィルタリング可能。
    """
    permission_classes = [AllowAny]

    def get(self, request, bank_id):
        """
        支店一覧を返す
        ?aiueo_row=あ (あいうえお行フィルター)
        """
        queryset = BankBranch.objects.filter(bank_id=bank_id, is_active=True)

        # あいうえお行でフィルタリング
        aiueo_row = request.query_params.get('aiueo_row')
        if aiueo_row:
            queryset = queryset.filter(aiueo_row=aiueo_row)

        queryset = queryset.order_by('sort_order', 'branch_name_hiragana')
        serializer = BankBranchSerializer(queryset, many=True)
        return Response(serializer.data)


# ========================================
# Google Calendar API
# ========================================
class AdminCalendarABSwapView(APIView):
    """ABスワップAPI

    指定した日付・カレンダーパターンのABタイプを切り替える。
    A -> B, B -> A のスワップを行う。
    """
    permission_classes = [AllowAny]  # TODO: IsAuthenticated に変更

    def post(self, request):
        """
        ABスワップを実行

        Body:
            calendar_pattern: カレンダーパターン (例: 1001_SKAEC_A)
            date: 日付 (YYYY-MM-DD)
            new_type: 新しいタイプ (A, B) - オプション、指定しない場合は自動切り替え
        """
        from datetime import datetime
        from .models import LessonCalendar, ClassSchedule

        calendar_pattern = request.data.get('calendar_pattern')
        date_str = request.data.get('date')
        new_type = request.data.get('new_type')

        if not all([calendar_pattern, date_str]):
            return Response(
                {'error': 'calendar_pattern and date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lesson_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # LessonCalendarを取得または作成
            lesson_calendar = LessonCalendar.objects.filter(
                calendar_code=calendar_pattern,
                lesson_date=lesson_date
            ).first()

            if not lesson_calendar:
                # ClassScheduleからschool, brand, tenant情報を取得
                class_schedule = ClassSchedule.objects.filter(
                    calendar_pattern=calendar_pattern,
                    deleted_at__isnull=True
                ).first()

                if not class_schedule:
                    return Response(
                        {'error': f'ClassSchedule not found for calendar_pattern: {calendar_pattern}'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # 新しいLessonCalendarを作成
                lesson_calendar = LessonCalendar.objects.create(
                    tenant_id=class_schedule.tenant_id,
                    calendar_code=calendar_pattern,
                    lesson_date=lesson_date,
                    school=class_schedule.school,
                    brand=class_schedule.brand,
                    lesson_type='A',  # デフォルト
                    is_open=True,
                )

            old_type = lesson_calendar.lesson_type or 'A'

            # 新しいタイプを決定
            if new_type:
                if new_type not in ['A', 'B', 'P', 'Y']:
                    return Response(
                        {'error': 'new_type must be A, B, P, or Y'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                lesson_calendar.lesson_type = new_type
            else:
                # 自動切り替え: A <-> B
                if old_type == 'A':
                    lesson_calendar.lesson_type = 'B'
                elif old_type == 'B':
                    lesson_calendar.lesson_type = 'A'
                else:
                    return Response(
                        {'error': f'Cannot auto-swap type {old_type}. Please specify new_type.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            lesson_calendar.save()

            # 操作ログを記録
            try:
                from .models import CalendarOperationLog
                CalendarOperationLog.log_ab_swap(
                    tenant_id=lesson_calendar.tenant_id,
                    school=lesson_calendar.school,
                    brand=lesson_calendar.brand,
                    lesson_calendar=lesson_calendar,
                    old_type=old_type,
                    new_type=lesson_calendar.lesson_type,
                    user=request.user if request.user.is_authenticated else None,
                )
            except Exception as log_error:
                # ログ記録に失敗してもスワップは成功とする
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to log AB swap: {log_error}")

            return Response({
                'success': True,
                'calendar_pattern': calendar_pattern,
                'date': date_str,
                'old_type': old_type,
                'new_type': lesson_calendar.lesson_type,
                'message': f'{old_type} → {lesson_calendar.lesson_type} に変更しました',
            })

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"AB swap error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleCalendarEventsView(APIView):
    """Google Calendar イベント取得API

    Google Calendarからイベントを取得して返す。
    月表示と週表示に対応。
    """
    permission_classes = [AllowAny]  # TODO: IsAuthenticated に変更

    def get(self, request):
        """
        Google Calendarのイベントを取得

        Query Parameters:
            calendar_id: GoogleカレンダーID（必須）
            view: 'month' or 'week' (デフォルト: 'month')
            year: 年 (view=monthの場合必須)
            month: 月 (view=monthの場合必須)
            week_start: 週の開始日 (view=weekの場合必須, YYYY-MM-DD形式)

        Returns:
            イベントリスト
        """
        from datetime import datetime
        from .services.google_calendar import GoogleCalendarService

        calendar_id = request.query_params.get('calendar_id')
        view = request.query_params.get('view', 'month')
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        week_start = request.query_params.get('week_start')

        if not calendar_id:
            return Response(
                {'error': 'calendar_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = GoogleCalendarService()

        if view == 'month':
            if not all([year, month]):
                return Response(
                    {'error': 'year and month are required for month view'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                events = service.get_events_for_month(
                    calendar_id,
                    int(year),
                    int(month)
                )
            except Exception as e:
                return Response(
                    {'error': f'Failed to fetch events: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        elif view == 'week':
            if not week_start:
                return Response(
                    {'error': 'week_start is required for week view'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                week_start_date = datetime.strptime(week_start, '%Y-%m-%d')
                events = service.get_events_for_week(calendar_id, week_start_date)
            except ValueError:
                return Response(
                    {'error': 'week_start must be in YYYY-MM-DD format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {'error': f'Failed to fetch events: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {'error': 'view must be "month" or "week"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'calendarId': calendar_id,
            'view': view,
            'events': events
        })


class GoogleCalendarListView(APIView):
    """Google Calendar 一覧取得API

    アクセス可能なカレンダー一覧を返す。
    """
    permission_classes = [AllowAny]  # TODO: IsAuthenticated に変更

    def get(self, request):
        """
        アクセス可能なカレンダー一覧を取得

        Returns:
            カレンダーリスト
        """
        from .services.google_calendar import GoogleCalendarService

        service = GoogleCalendarService()
        calendars = service.list_calendars()

        return Response({
            'calendars': calendars
        })

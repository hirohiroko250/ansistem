"""
Schedule Views - スケジュール関連
TimeSlot, SchoolSchedule, SchoolCourse, SchoolClosure
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from apps.core.exceptions import NotFoundError, SchoolNotFoundError
from apps.core.csv_utils import CSVMixin
from ..models import TimeSlot, SchoolSchedule, SchoolCourse, SchoolClosure, School, Brand
from ..serializers import (
    TimeSlotSerializer,
    SchoolScheduleListSerializer, SchoolScheduleDetailSerializer, SchoolScheduleCreateUpdateSerializer,
    SchoolCourseListSerializer, SchoolCourseDetailSerializer,
    SchoolClosureListSerializer, SchoolClosureDetailSerializer, SchoolClosureCreateUpdateSerializer,
)


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
            raise SchoolNotFoundError('校舎またはブランドが見つかりません')

        is_closed = SchoolClosure.is_closed(school, brand, check_date, time_slot)
        return Response({
            'is_closed': is_closed,
            'school': school.school_name,
            'brand': brand.brand_name,
            'date': date_str,
            'time_slot': time_slot.slot_name if time_slot else None
        })

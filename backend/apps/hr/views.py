"""
HR Views - 勤怠管理ビュー
"""
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Q
from datetime import datetime, timedelta

from apps.core.permissions import IsTenantUser
from apps.core.exceptions import OZAException, ErrorCode
from .models import (
    HRAttendance,
    StaffAvailability,
    StaffAvailabilityBooking,
    StaffWorkSchedule,
    StaffProfile,
    StaffSkill,
    StaffReview,
)
from .serializers import (
    HRAttendanceSerializer,
    StaffAvailabilitySerializer,
    StaffAvailabilityCreateSerializer,
    StaffAvailabilityBookingSerializer,
    StaffWorkScheduleSerializer,
    StaffProfileSerializer,
    StaffProfileUpdateSerializer,
    StaffSkillSerializer,
    StaffReviewSerializer,
)


class HRAttendanceViewSet(viewsets.ModelViewSet):
    """勤怠記録ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = HRAttendanceSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        queryset = HRAttendance.objects.filter(
            tenant_id=tenant_id,
            user=self.request.user
        )

        # 日付範囲フィルタ
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        # ステータスフィルタ
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-date')

    @action(detail=False, methods=['get'])
    def today(self, request):
        """今日の勤怠記録を取得"""
        today = timezone.localdate()
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)
        try:
            attendance = HRAttendance.objects.get(
                tenant_id=tenant_id,
                user=request.user,
                date=today
            )
            return Response(HRAttendanceSerializer(attendance).data)
        except HRAttendance.DoesNotExist:
            return Response(
                {'detail': '今日の勤怠記録がありません'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def clock_in(self, request):
        """出勤打刻"""
        today = timezone.localdate()
        now = timezone.now()
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        # 既存の記録をチェック
        existing = HRAttendance.objects.filter(
            tenant_id=tenant_id,
            user=request.user,
            date=today
        ).first()

        if existing and existing.clock_in:
            return Response(
                {'error': '既に出勤打刻済みです', 'message': '既に出勤打刻済みです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # QRコード打刻かどうか
        qr_code = request.data.get('qrCode')
        school_id = request.data.get('schoolId')

        if existing:
            existing.clock_in = now
            existing.status = HRAttendance.AttendanceStatus.WORKING
            existing.qr_code_used = bool(qr_code)
            if school_id:
                existing.school_id = school_id
            existing.save()
            attendance = existing
        else:
            attendance = HRAttendance.objects.create(
                tenant_id=tenant_id,
                user=request.user,
                date=today,
                clock_in=now,
                status=HRAttendance.AttendanceStatus.WORKING,
                qr_code_used=bool(qr_code),
                school_id=school_id if school_id else None
            )

        return Response({
            'id': str(attendance.id),
            'clockInTime': attendance.clock_in.isoformat() if attendance.clock_in else None,
            'status': attendance.status,
            'message': '出勤打刻が完了しました'
        })

    @action(detail=False, methods=['post'])
    def clock_out(self, request):
        """退勤打刻"""
        today = timezone.localdate()
        now = timezone.now()
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        try:
            attendance = HRAttendance.objects.get(
                tenant_id=tenant_id,
                user=request.user,
                date=today
            )
        except HRAttendance.DoesNotExist:
            return Response(
                {'error': '出勤打刻がありません', 'message': '先に出勤打刻をしてください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if attendance.clock_out:
            return Response(
                {'error': '既に退勤打刻済みです', 'message': '既に退勤打刻済みです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not attendance.clock_in:
            return Response(
                {'error': '出勤打刻がありません', 'message': '先に出勤打刻をしてください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 日報を更新
        daily_report = request.data.get('dailyReport')
        if daily_report:
            attendance.daily_report = daily_report

        attendance.clock_out = now
        attendance.status = HRAttendance.AttendanceStatus.COMPLETED
        attendance.save()

        return Response({
            'id': str(attendance.id),
            'clockInTime': attendance.clock_in.isoformat() if attendance.clock_in else None,
            'clockOutTime': attendance.clock_out.isoformat() if attendance.clock_out else None,
            'workMinutes': attendance.work_minutes,
            'status': attendance.status,
            'message': '退勤打刻が完了しました'
        })

    @action(detail=False, methods=['post'])
    def break_start(self, request):
        """休憩開始"""
        return Response({'message': '休憩開始しました'})

    @action(detail=False, methods=['post'])
    def break_end(self, request):
        """休憩終了"""
        return Response({'message': '休憩終了しました'})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """月別勤怠サマリー"""
        year = request.query_params.get('year', timezone.localdate().year)
        month = request.query_params.get('month', timezone.localdate().month)
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        queryset = HRAttendance.objects.filter(
            tenant_id=tenant_id,
            user=request.user,
            date__year=year,
            date__month=month
        )

        aggregates = queryset.aggregate(
            total_work_minutes=Sum('work_minutes'),
            total_overtime_minutes=Sum('overtime_minutes'),
            total_break_minutes=Sum('break_minutes')
        )

        work_days = queryset.filter(
            status=HRAttendance.AttendanceStatus.COMPLETED
        ).count()

        absent_days = queryset.filter(
            status=HRAttendance.AttendanceStatus.ABSENT
        ).count()

        leave_days = queryset.filter(
            status=HRAttendance.AttendanceStatus.LEAVE
        ).count()

        total_work_minutes = aggregates['total_work_minutes'] or 0

        return Response({
            'userId': str(request.user.id),
            'year': int(year),
            'month': int(month),
            'totalWorkDays': work_days,
            'totalWorkMinutes': total_work_minutes,
            'totalOvertimeMinutes': aggregates['total_overtime_minutes'] or 0,
            'totalBreakMinutes': aggregates['total_break_minutes'] or 0,
            'absentDays': absent_days,
            'leaveDays': leave_days,
            'averageWorkMinutes': total_work_minutes // work_days if work_days > 0 else 0
        })


class StaffAvailabilityViewSet(viewsets.ModelViewSet):
    """社員空き時間ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return StaffAvailabilityCreateSerializer
        return StaffAvailabilitySerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        queryset = StaffAvailability.objects.filter(tenant_id=tenant_id)

        # 社員IDでフィルタ
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)

        # 日付範囲でフィルタ
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        # ステータスでフィルタ
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 予約可能なもののみ
        bookable_only = self.request.query_params.get('bookable_only')
        if bookable_only == 'true':
            queryset = queryset.filter(
                status=StaffAvailability.SlotStatus.AVAILABLE
            ).extra(where=['current_bookings < capacity'])

        return queryset.select_related('employee', 'school').order_by('date', 'start_time')

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        employee_id = self.request.data.get('employee_id')

        # 自分のEmployeeレコードを取得
        if not employee_id:
            from apps.tenants.models import Employee
            try:
                employee = Employee.objects.get(
                    tenant_id=tenant_id,
                    email=self.request.user.email
                )
                employee_id = employee.id
            except Employee.DoesNotExist:
                raise OZAException(
                    error_code=ErrorCode.NOT_FOUND,
                    message='社員情報が見つかりません'
                )

        serializer.save(tenant_id=tenant_id, employee_id=employee_id)

    @action(detail=False, methods=['get'])
    def my_schedule(self, request):
        """自分の空き時間一覧を取得"""
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        from apps.tenants.models import Employee
        try:
            employee = Employee.objects.get(
                tenant_id=tenant_id,
                email=request.user.email
            )
        except Employee.DoesNotExist:
            return Response([])

        queryset = StaffAvailability.objects.filter(
            tenant_id=tenant_id,
            employee=employee
        )

        # 日付範囲
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        queryset = queryset.order_by('date', 'start_time')
        serializer = StaffAvailabilitySerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def book(self, request, pk=None):
        """空き時間を予約"""
        availability = self.get_object()

        if not availability.is_bookable:
            raise OZAException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message='この枠は予約できません'
            )

        student_id = request.data.get('student_id')
        student_item_id = request.data.get('student_item_id')
        request_message = request.data.get('request_message', '')

        booking = StaffAvailabilityBooking.objects.create(
            tenant_id=availability.tenant_id,
            availability=availability,
            student_id=student_id,
            student_item_id=student_item_id,
            request_message=request_message,
            status=StaffAvailabilityBooking.BookingStatus.PENDING
        )

        # 予約数を更新
        availability.current_bookings += 1
        if availability.current_bookings >= availability.capacity:
            availability.status = StaffAvailability.SlotStatus.BOOKED
        availability.save()

        return Response({
            'id': str(booking.id),
            'status': booking.status,
            'message': '予約が完了しました'
        })


class StaffAvailabilityBookingViewSet(viewsets.ModelViewSet):
    """空き時間予約ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = StaffAvailabilityBookingSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        queryset = StaffAvailabilityBooking.objects.filter(tenant_id=tenant_id)

        # 生徒でフィルタ
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        # ステータスでフィルタ
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related(
            'availability', 'availability__employee', 'student'
        ).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """予約を確定"""
        booking = self.get_object()
        booking.status = StaffAvailabilityBooking.BookingStatus.CONFIRMED
        booking.save()
        return Response({'message': '予約を確定しました'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """予約をキャンセル"""
        booking = self.get_object()

        if not booking.can_cancel():
            raise OZAException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message='この予約はキャンセルできません'
            )

        booking.status = StaffAvailabilityBooking.BookingStatus.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.cancelled_by = request.user
        booking.cancel_reason = request.data.get('cancel_reason', '')
        booking.save()

        # 空き時間の予約数を減らす
        availability = booking.availability
        availability.current_bookings = max(0, availability.current_bookings - 1)
        if availability.status == StaffAvailability.SlotStatus.BOOKED:
            availability.status = StaffAvailability.SlotStatus.AVAILABLE
        availability.save()

        return Response({'message': 'キャンセルしました'})


class StaffWorkScheduleViewSet(viewsets.ModelViewSet):
    """勤務スケジュールビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = StaffWorkScheduleSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        queryset = StaffWorkSchedule.objects.filter(tenant_id=tenant_id)

        # 社員でフィルタ
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)

        # 日付範囲
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        # 校舎でフィルタ
        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)

        return queryset.select_related('employee', 'school').order_by('date', 'planned_start')

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        employee_id = self.request.data.get('employee_id')

        if not employee_id:
            from apps.tenants.models import Employee
            try:
                employee = Employee.objects.get(
                    tenant_id=tenant_id,
                    email=self.request.user.email
                )
                employee_id = employee.id
            except Employee.DoesNotExist:
                raise OZAException(
                    error_code=ErrorCode.NOT_FOUND,
                    message='社員情報が見つかりません'
                )

        serializer.save(tenant_id=tenant_id, employee_id=employee_id)

    @action(detail=False, methods=['get'])
    def my_schedule(self, request):
        """自分の勤務スケジュールを取得"""
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        from apps.tenants.models import Employee
        try:
            employee = Employee.objects.get(
                tenant_id=tenant_id,
                email=request.user.email
            )
        except Employee.DoesNotExist:
            return Response([])

        queryset = StaffWorkSchedule.objects.filter(
            tenant_id=tenant_id,
            employee=employee
        )

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        queryset = queryset.order_by('date', 'planned_start')
        serializer = StaffWorkScheduleSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """カレンダー形式で勤務スケジュールを取得"""
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        year = int(request.query_params.get('year', timezone.localdate().year))
        month = int(request.query_params.get('month', timezone.localdate().month))

        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day}"

        queryset = StaffWorkSchedule.objects.filter(
            tenant_id=tenant_id,
            date__gte=start_date,
            date__lte=end_date
        ).select_related('employee', 'school')

        # 日付ごとにグループ化
        result = {}
        for schedule in queryset:
            date_str = schedule.date.strftime('%Y-%m-%d')
            if date_str not in result:
                result[date_str] = []
            result[date_str].append(StaffWorkScheduleSerializer(schedule).data)

        return Response(result)


class StaffProfileViewSet(viewsets.ModelViewSet):
    """講師プロフィールビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return StaffProfileUpdateSerializer
        return StaffProfileSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        queryset = StaffProfile.objects.filter(tenant_id=tenant_id)

        # 公開プロフィールのみ
        public_only = self.request.query_params.get('public_only')
        if public_only == 'true':
            queryset = queryset.filter(is_public=True)

        # 予約可能のみ
        bookable_only = self.request.query_params.get('bookable_only')
        if bookable_only == 'true':
            queryset = queryset.filter(is_bookable=True)

        # スキルでフィルタ
        skill = self.request.query_params.get('skill')
        if skill:
            queryset = queryset.filter(skills__name__icontains=skill)

        return queryset.select_related('employee', 'employee__position').prefetch_related(
            'skills', 'photos', 'employee__brands'
        )

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """自分のプロフィールを取得"""
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        from apps.tenants.models import Employee
        try:
            employee = Employee.objects.get(
                tenant_id=tenant_id,
                email=request.user.email
            )
        except Employee.DoesNotExist:
            raise OZAException(
                error_code=ErrorCode.NOT_FOUND,
                message='社員情報が見つかりません'
            )

        profile, created = StaffProfile.objects.get_or_create(
            tenant_id=tenant_id,
            employee=employee,
            defaults={'display_name': f"{employee.last_name}先生"}
        )

        serializer = StaffProfileSerializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_my_profile(self, request):
        """自分のプロフィールを更新"""
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        from apps.tenants.models import Employee
        try:
            employee = Employee.objects.get(
                tenant_id=tenant_id,
                email=request.user.email
            )
        except Employee.DoesNotExist:
            raise OZAException(
                error_code=ErrorCode.NOT_FOUND,
                message='社員情報が見つかりません'
            )

        profile, _ = StaffProfile.objects.get_or_create(
            tenant_id=tenant_id,
            employee=employee
        )

        serializer = StaffProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(StaffProfileSerializer(profile).data)

    @action(detail=True, methods=['post'])
    def add_skill(self, request, pk=None):
        """スキルを追加"""
        profile = self.get_object()

        skill = StaffSkill.objects.create(
            tenant_id=profile.tenant_id,
            profile=profile,
            category=request.data.get('category', 'specialty'),
            name=request.data.get('name'),
            level=request.data.get('level', 3),
            color=request.data.get('color', '')
        )

        return Response(StaffSkillSerializer(skill).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='remove_skill/(?P<skill_id>[^/.]+)')
    def remove_skill(self, request, pk=None, skill_id=None):
        """スキルを削除"""
        profile = self.get_object()
        StaffSkill.objects.filter(profile=profile, id=skill_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffReviewViewSet(viewsets.ModelViewSet):
    """講師レビュービューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = StaffReviewSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        queryset = StaffReview.objects.filter(tenant_id=tenant_id)

        # プロフィールでフィルタ
        profile_id = self.request.query_params.get('profile_id')
        if profile_id:
            queryset = queryset.filter(profile_id=profile_id)

        # 公開のみ
        public_only = self.request.query_params.get('public_only')
        if public_only == 'true':
            queryset = queryset.filter(is_public=True, is_approved=True)

        return queryset.select_related('profile', 'student').order_by('-created_at')

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        serializer.save(tenant_id=tenant_id)

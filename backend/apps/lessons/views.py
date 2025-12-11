"""
Lessons Views
授業スケジュール・出欠・振替のAPI
"""
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q
from django.utils import timezone

from .models import (
    TimeSlot, LessonSchedule, LessonRecord,
    Attendance, MakeupLesson, GroupLessonEnrollment
)
from .serializers import (
    TimeSlotSerializer,
    LessonScheduleListSerializer,
    LessonScheduleDetailSerializer,
    LessonScheduleCreateSerializer,
    LessonRecordSerializer,
    AttendanceSerializer,
    MakeupLessonListSerializer,
    MakeupLessonDetailSerializer,
    GroupLessonEnrollmentSerializer,
    CalendarEventSerializer,
)
from apps.schools.models import LessonCalendar


class TimeSlotViewSet(viewsets.ModelViewSet):
    """時間割 ViewSet"""
    queryset = TimeSlot.objects.all()
    serializer_class = TimeSlotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = TimeSlot.objects.filter(is_active=True)
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        school_id = self.request.query_params.get('school')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        return queryset


class LessonScheduleViewSet(viewsets.ModelViewSet):
    """授業スケジュール ViewSet"""
    queryset = LessonSchedule.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return LessonScheduleListSerializer
        elif self.action == 'create':
            return LessonScheduleCreateSerializer
        return LessonScheduleDetailSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = LessonSchedule.objects.all()
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        # フィルタリング
        student_id = self.request.query_params.get('student')
        school_id = self.request.query_params.get('school')
        teacher_id = self.request.query_params.get('teacher')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        lesson_status = self.request.query_params.get('status')
        lesson_type = self.request.query_params.get('lesson_type')

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if lesson_status:
            queryset = queryset.filter(status=lesson_status)
        if lesson_type:
            queryset = queryset.filter(lesson_type=lesson_type)

        # カレンダー形式の場合
        if self.request.query_params.get('format') == 'calendar':
            queryset = queryset.select_related('school', 'subject', 'teacher', 'student')

        return queryset.order_by('date', 'start_time')

    def list(self, request, *args, **kwargs):
        """一覧取得（カレンダー形式対応）"""
        if request.query_params.get('format') == 'calendar':
            queryset = self.filter_queryset(self.get_queryset())
            events = []
            for schedule in queryset:
                start_datetime = datetime.combine(schedule.date, schedule.start_time)
                end_datetime = datetime.combine(schedule.date, schedule.end_time)
                events.append({
                    'id': str(schedule.id),
                    'title': schedule.subject.subject_name if schedule.subject else schedule.class_name or '授業',
                    'start': start_datetime.isoformat(),
                    'end': end_datetime.isoformat(),
                    'type': schedule.lesson_type,
                    'status': schedule.status,
                    'resourceId': str(schedule.school_id) if schedule.school_id else None,
                })
            return Response(events)
        return super().list(request, *args, **kwargs)


class AttendanceViewSet(viewsets.ModelViewSet):
    """出席記録 ViewSet"""
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = Attendance.objects.all()
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        student_id = self.request.query_params.get('student')
        schedule_id = self.request.query_params.get('schedule')
        status_filter = self.request.query_params.get('status')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if date_from:
            queryset = queryset.filter(schedule__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(schedule__date__lte=date_to)

        return queryset.select_related('student', 'schedule')

    def partial_update(self, request, *args, **kwargs):
        """欠席登録など出欠更新"""
        instance = self.get_object()

        # ステータス更新
        new_status = request.data.get('status')
        if new_status:
            instance.status = new_status

        # 欠席理由
        absence_reason = request.data.get('absence_reason')
        if absence_reason:
            instance.absence_reason = absence_reason

        # 欠席連絡日時
        if new_status in ['absent', 'absent_notice']:
            instance.absence_notified_at = timezone.now()

        instance.save()

        # 振替申請も行う場合
        if request.data.get('request_makeup') and new_status in ['absent', 'absent_notice']:
            MakeupLesson.objects.create(
                tenant_id=instance.tenant_id,
                original_schedule=instance.schedule,
                student=instance.student,
                reason=absence_reason or '欠席による振替',
                requested_by=request.user,
                valid_until=instance.schedule.date + timedelta(days=90),
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class MakeupLessonViewSet(viewsets.ModelViewSet):
    """振替 ViewSet"""
    queryset = MakeupLesson.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return MakeupLessonListSerializer
        return MakeupLessonDetailSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = MakeupLesson.objects.all()
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        student_id = self.request.query_params.get('student')
        status_filter = self.request.query_params.get('status')

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related(
            'student', 'original_schedule', 'makeup_schedule'
        )

    def create(self, request, *args, **kwargs):
        """振替申請"""
        original_schedule_id = request.data.get('original_schedule')
        student_id = request.data.get('student')
        preferred_date = request.data.get('preferred_date')
        preferred_time_slot_id = request.data.get('preferred_time_slot')
        reason = request.data.get('reason', '')

        try:
            original_schedule = LessonSchedule.objects.get(id=original_schedule_id)
        except LessonSchedule.DoesNotExist:
            return Response(
                {'error': '元スケジュールが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 振替申請作成
        makeup = MakeupLesson.objects.create(
            tenant_id=request.tenant_id,
            original_schedule=original_schedule,
            student_id=student_id,
            preferred_date=preferred_date,
            preferred_time_slot_id=preferred_time_slot_id,
            reason=reason,
            requested_by=request.user,
            valid_until=original_schedule.date + timedelta(days=90),
        )

        serializer = MakeupLessonDetailSerializer(makeup)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='available-dates')
    def available_dates(self, request):
        """振替可能日を取得"""
        course_id = request.query_params.get('course')
        school_id = request.query_params.get('school')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if not date_from:
            date_from = datetime.now().date().isoformat()
        if not date_to:
            date_to = (datetime.now() + timedelta(days=60)).date().isoformat()

        # LessonCalendarから開講日を取得
        queryset = LessonCalendar.objects.filter(
            tenant_id=request.tenant_id,
            is_open=True,
            lesson_date__gte=date_from,
            lesson_date__lte=date_to,
        )

        if school_id:
            queryset = queryset.filter(school_id=school_id)

        available_dates = []
        for calendar in queryset:
            available_dates.append({
                'date': calendar.lesson_date.isoformat(),
                'dayOfWeek': calendar.day_of_week,
                'lessonType': calendar.lesson_type,
                'displayLabel': calendar.display_label,
            })

        return Response(available_dates)


class LessonRecordViewSet(viewsets.ModelViewSet):
    """授業実績 ViewSet"""
    queryset = LessonRecord.objects.all()
    serializer_class = LessonRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = LessonRecord.objects.all()
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        student_id = self.request.query_params.get('student')
        if student_id:
            queryset = queryset.filter(schedule__student_id=student_id)

        return queryset.select_related('schedule', 'schedule__student', 'schedule__teacher')


class GroupLessonEnrollmentViewSet(viewsets.ModelViewSet):
    """集団授業受講者 ViewSet"""
    queryset = GroupLessonEnrollment.objects.all()
    serializer_class = GroupLessonEnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = GroupLessonEnrollment.objects.all()
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        schedule_id = self.request.query_params.get('schedule')
        student_id = self.request.query_params.get('student')

        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        return queryset.select_related('student', 'schedule')


class StudentCalendarView(APIView):
    """生徒のカレンダー表示用API

    開講時間割（ClassSchedule）と年間カレンダー（LessonCalendar）を組み合わせて
    生徒のカレンダーイベントを生成する
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.schools.models import ClassSchedule, LessonCalendar
        from apps.contracts.models import StudentItem
        from apps.students.models import Student
        from datetime import datetime as dt
        import calendar as cal

        # tenant_idはrequest.tenant_idまたはrequest.user.tenant_idから取得
        tenant_id = getattr(request, 'tenant_id', None)
        if tenant_id is None and hasattr(request, 'user') and hasattr(request.user, 'tenant_id'):
            tenant_id = request.user.tenant_id
        student_id = request.query_params.get('student_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not student_id:
            return Response({'error': 'student_id is required'}, status=400)

        # 生徒取得
        try:
            student = Student.objects.get(id=student_id, tenant_id=tenant_id)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=404)

        # 日付範囲の設定
        if year and month:
            year = int(year)
            month = int(month)
            date_from = dt(year, month, 1).date()
            _, last_day = cal.monthrange(year, month)
            date_to = dt(year, month, last_day).date()
        elif date_from and date_to:
            date_from = dt.fromisoformat(date_from).date()
            date_to = dt.fromisoformat(date_to).date()
        else:
            # デフォルトは今月
            today = dt.now().date()
            date_from = today.replace(day=1)
            _, last_day = cal.monthrange(today.year, today.month)
            date_to = today.replace(day=last_day)

        # 生徒の受講クラス（ClassSchedule）を取得
        # StudentItemからブランド・校舎情報を取得
        student_items = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True
        ).select_related('brand', 'school')

        # 受講中のブランド・校舎を特定
        brand_ids = set()
        school_ids = set()
        for item in student_items:
            if item.brand_id:
                brand_ids.add(item.brand_id)
            if item.school_id:
                school_ids.add(item.school_id)

        # 生徒の主校舎・主ブランドも追加
        if student.primary_school_id:
            school_ids.add(student.primary_school_id)
        if student.primary_brand_id:
            brand_ids.add(student.primary_brand_id)

        # ClassScheduleを取得（曜日ベース）
        class_schedules = ClassSchedule.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            deleted_at__isnull=True
        )

        if school_ids:
            class_schedules = class_schedules.filter(school_id__in=school_ids)
        if brand_ids:
            class_schedules = class_schedules.filter(brand_id__in=brand_ids)

        class_schedules = class_schedules.select_related('school', 'brand', 'brand_category')

        # LessonCalendarを取得（日付ベースの開講情報）
        lesson_calendars = LessonCalendar.objects.filter(
            tenant_id=tenant_id,
            lesson_date__gte=date_from,
            lesson_date__lte=date_to,
        )
        if school_ids:
            lesson_calendars = lesson_calendars.filter(school_id__in=school_ids)
        if brand_ids:
            lesson_calendars = lesson_calendars.filter(brand_id__in=brand_ids)

        # カレンダーをdate+school+brandでインデックス化
        calendar_map = {}
        for lc in lesson_calendars:
            key = (lc.lesson_date, str(lc.school_id), str(lc.brand_id) if lc.brand_id else None)
            calendar_map[key] = lc

        # カレンダーイベントを生成
        events = []
        current_date = date_from
        day_of_week_map = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7}  # Python weekday -> DB day_of_week

        while current_date <= date_to:
            python_weekday = current_date.weekday()
            db_day_of_week = day_of_week_map[python_weekday]

            # この日の該当するClassScheduleを探す
            for cs in class_schedules:
                if cs.day_of_week != db_day_of_week:
                    continue

                # LessonCalendarから開講状況を確認
                cal_key = (current_date, str(cs.school_id), str(cs.brand_id) if cs.brand_id else None)
                lesson_cal = calendar_map.get(cal_key)

                # 休校日チェック
                is_closed = False
                is_native_day = False
                lesson_type = 'A'
                notice_message = ''
                holiday_name = ''

                if lesson_cal:
                    is_closed = not lesson_cal.is_open
                    is_native_day = lesson_cal.is_native_day
                    lesson_type = lesson_cal.lesson_type
                    notice_message = lesson_cal.notice_message or ''
                    holiday_name = lesson_cal.holiday_name or ''

                # イベントを追加
                start_datetime = dt.combine(current_date, cs.start_time)
                end_datetime = dt.combine(current_date, cs.end_time)

                event_type = 'lesson'
                if is_closed:
                    event_type = 'closed'
                elif is_native_day:
                    event_type = 'native'

                events.append({
                    'id': f'{cs.id}_{current_date.isoformat()}',
                    'classScheduleId': str(cs.id),
                    'title': cs.class_name or cs.display_course_name or 'レッスン',
                    'start': start_datetime.isoformat(),
                    'end': end_datetime.isoformat(),
                    'date': current_date.isoformat(),
                    'dayOfWeek': db_day_of_week,
                    'period': cs.period,
                    'type': event_type,
                    'lessonType': lesson_type,
                    'isClosed': is_closed,
                    'isNativeDay': is_native_day,
                    'holidayName': holiday_name,
                    'noticeMessage': notice_message,
                    'schoolId': str(cs.school_id),
                    'schoolName': cs.school.school_name if cs.school else '',
                    'brandId': str(cs.brand_id) if cs.brand_id else None,
                    'brandName': cs.brand.brand_name if cs.brand else '',
                    'brandCategoryName': cs.brand_category.category_name if cs.brand_category else '',
                    'roomName': cs.room_name or '',
                    'className': cs.class_name,
                    'displayCourseName': cs.display_course_name,
                    'displayPairName': cs.display_pair_name,
                    'transferGroup': cs.transfer_group,
                    'calendarPattern': cs.calendar_pattern,
                })

            current_date += timedelta(days=1)

        return Response({
            'studentId': str(student.id),
            'studentName': f'{student.last_name}{student.first_name}',
            'dateFrom': date_from.isoformat(),
            'dateTo': date_to.isoformat(),
            'events': events,
        })


class MarkAbsenceView(APIView):
    """カレンダーから欠席登録するAPI

    欠席登録と同時に振替チケットを自動追加する
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.students.models import Student
        from apps.schools.models import ClassSchedule
        from apps.contracts.models import StudentItem, Product
        from datetime import datetime as dt

        # tenant_idはrequest.tenant_idまたはrequest.user.tenant_idから取得
        tenant_id = getattr(request, 'tenant_id', None)
        if tenant_id is None and hasattr(request, 'user') and hasattr(request.user, 'tenant_id'):
            tenant_id = request.user.tenant_id

        student_id = request.data.get('student_id')
        lesson_date = request.data.get('lesson_date')  # YYYY-MM-DD
        class_schedule_id = request.data.get('class_schedule_id')
        reason = request.data.get('reason', '')

        if not student_id or not lesson_date or not class_schedule_id:
            return Response({'error': 'student_id, lesson_date, class_schedule_id are required'}, status=400)

        # 生徒取得
        try:
            student = Student.objects.get(id=student_id, tenant_id=tenant_id, deleted_at__isnull=True)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=404)

        # ClassSchedule取得
        try:
            class_schedule = ClassSchedule.objects.get(id=class_schedule_id, tenant_id=tenant_id)
        except ClassSchedule.DoesNotExist:
            return Response({'error': 'ClassSchedule not found'}, status=404)

        # 日付パース
        try:
            absence_date = dt.fromisoformat(lesson_date).date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)

        # 欠席レコードを作成（Attendanceモデルに記録）
        # AttendanceモデルがあればそれをAを使用、なければ新しい欠席記録モデルを検討
        from .models import Attendance, LessonSchedule

        # LessonScheduleを取得または作成して、Attendanceを記録
        # 現状の設計上、特定の日のレッスンスケジュールを取得
        lesson_schedule = LessonSchedule.objects.filter(
            tenant_id=tenant_id,
            scheduled_date=absence_date,
            course_id=class_schedule.course_id if hasattr(class_schedule, 'course_id') else None,
            deleted_at__isnull=True,
        ).first()

        # 出欠記録を作成
        attendance, created = Attendance.objects.update_or_create(
            tenant_id=tenant_id,
            student=student,
            schedule=lesson_schedule,
            defaults={
                'status': 'absent_notice',
                'absence_reason': reason or 'カレンダーからの欠席連絡',
            }
        )

        # 振替チケットを追加
        # 商品（振替チケット）を検索
        transfer_ticket_product = Product.objects.filter(
            tenant_id=tenant_id,
            item_type='ticket',
            deleted_at__isnull=True,
        ).filter(
            Q(product_name__icontains='振替') | Q(product_code__icontains='transfer')
        ).first()

        transfer_ticket_created = False
        if transfer_ticket_product:
            # 振替チケットをStudentItemとして追加
            from django.utils import timezone
            billing_month = absence_date.strftime('%Y-%m')

            StudentItem.objects.create(
                tenant_id=tenant_id,
                student=student,
                product=transfer_ticket_product,
                billing_month=billing_month,
                quantity=1,
                unit_price=0,
                discount_amount=0,
                final_price=0,
                notes=f'欠席による振替チケット発行（{absence_date.isoformat()}）',
                brand=class_schedule.brand if hasattr(class_schedule, 'brand') else None,
                school=class_schedule.school if hasattr(class_schedule, 'school') else None,
            )
            transfer_ticket_created = True

        return Response({
            'success': True,
            'message': '欠席登録が完了しました',
            'attendance_id': str(attendance.id) if attendance else None,
            'transfer_ticket_created': transfer_ticket_created,
            'absence_date': absence_date.isoformat(),
        })

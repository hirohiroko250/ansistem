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
        # student_id または student パラメータを受け付ける
        student_id = request.query_params.get('student_id') or request.query_params.get('student')
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
        # StudentItemから直接class_scheduleを参照する
        student_items = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True
        ).select_related('brand', 'school', 'course', 'class_schedule')

        # StudentItemから受講ClassScheduleのIDを収集
        # class_scheduleがあればそれを直接使用、なければ曜日+時間+ブランド+校舎でマッチング
        direct_schedule_ids = set()  # class_schedule FKで直接紐付けられたもの
        fallback_schedules = []  # class_scheduleがない場合のフォールバック用
        brand_ids = set()
        school_ids = set()

        for item in student_items:
            if item.brand_id:
                brand_ids.add(item.brand_id)
            if item.school_id:
                school_ids.add(item.school_id)

            # class_scheduleが設定されている場合は直接使用
            if item.class_schedule_id:
                direct_schedule_ids.add(item.class_schedule_id)
            # class_scheduleがない場合は曜日+時間でフォールバックマッチング
            elif item.day_of_week is not None and item.start_time:
                fallback_schedules.append({
                    'day_of_week': item.day_of_week,
                    'start_time': item.start_time,
                    'brand_id': str(item.brand_id) if item.brand_id else None,
                    'school_id': str(item.school_id) if item.school_id else None,
                })

        # 生徒の主校舎・主ブランドも追加
        if student.primary_school_id:
            school_ids.add(student.primary_school_id)
        if student.primary_brand_id:
            brand_ids.add(student.primary_brand_id)

        # 直接紐付けられたClassScheduleを取得
        class_schedules = list(ClassSchedule.objects.filter(
            id__in=direct_schedule_ids,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('school', 'brand', 'brand_category'))

        # フォールバック: class_scheduleがないStudentItemの場合は曜日+時間+ブランド+校舎でマッチング
        if fallback_schedules:
            all_class_schedules = ClassSchedule.objects.filter(
                is_active=True,
                deleted_at__isnull=True
            )
            if school_ids:
                all_class_schedules = all_class_schedules.filter(school_id__in=school_ids)
            if brand_ids:
                all_class_schedules = all_class_schedules.filter(brand_id__in=brand_ids)
            all_class_schedules = all_class_schedules.select_related('school', 'brand', 'brand_category')

            # フォールバックマッチング（既に直接紐付けされたものは除外）
            # 時間差を分単位で計算するヘルパー関数
            def time_diff_minutes(t1, t2):
                """2つの時間の差を分単位で返す"""
                if not t1 or not t2:
                    return float('inf')
                return abs((t1.hour * 60 + t1.minute) - (t2.hour * 60 + t2.minute))

            for cs in all_class_schedules:
                if cs.id in direct_schedule_ids:
                    continue  # 既に追加済み
                for enrolled in fallback_schedules:
                    # 曜日が一致
                    dow_match = (enrolled['day_of_week'] == cs.day_of_week)
                    # 開始時間が近い（±30分以内でマッチ）
                    si_start_time = enrolled['start_time']
                    time_match = time_diff_minutes(si_start_time, cs.start_time) <= 30
                    # ブランドと校舎が一致
                    brand_match = (enrolled['brand_id'] == str(cs.brand_id) if cs.brand_id else True)
                    school_match = (enrolled['school_id'] == str(cs.school_id) if cs.school_id else True)

                    if dow_match and time_match and brand_match and school_match:
                        class_schedules.append(cs)
                        break  # このスケジュールは追加済み

        # LessonCalendarを取得（日付ベースの開講情報）
        # school_idとbrand_idでフィルタ（tenant_idは使用しない）
        lesson_calendars = LessonCalendar.objects.filter(
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

        # 欠席チケット（AbsenceTicket）を取得して欠席日をマップ化
        from .models import AbsenceTicket
        absence_tickets = AbsenceTicket.objects.filter(
            student=student,
            absence_date__gte=date_from,
            absence_date__lte=date_to,
        ).select_related('class_schedule')

        # 欠席日とclass_schedule_idのマップを作成
        # キー: (absence_date, class_schedule_id)
        absence_map = {}
        for at in absence_tickets:
            key = (at.absence_date, str(at.class_schedule_id) if at.class_schedule_id else None)
            absence_map[key] = at

        # カレンダーイベントを生成
        events = []
        today = dt.now().date()
        current_date = date_from
        day_of_week_map = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7}  # Python weekday -> DB day_of_week

        while current_date <= date_to:
            # 今日より前の日付はスキップ
            if current_date < today:
                current_date += timedelta(days=1)
                continue

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

                # 欠席チェック
                absence_key = (current_date, str(cs.id))
                absence_ticket = absence_map.get(absence_key)
                is_absent = absence_ticket is not None

                # イベントを追加
                start_datetime = dt.combine(current_date, cs.start_time)
                end_datetime = dt.combine(current_date, cs.end_time)

                event_type = 'lesson'
                event_status = 'scheduled'  # デフォルトステータス
                if is_closed:
                    event_type = 'closed'
                elif is_absent:
                    event_type = 'absent'
                    event_status = 'absent'
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
                    'status': event_status,  # absent/scheduled/confirmed等
                    'lessonType': lesson_type,
                    'isClosed': is_closed,
                    'isAbsent': is_absent,
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
                    'absenceTicketId': str(absence_ticket.id) if absence_ticket else None,
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

    欠席登録と同時にAbsenceTicketを発行する。
    消化記号(consumption_symbol)を基準に振替可能なクラスを判定。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.students.models import Student
        from apps.schools.models import ClassSchedule
        from apps.contracts.models import Ticket
        from datetime import datetime as dt, timedelta
        from .models import AbsenceTicket

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

        # ClassSchedule取得（tenant_idはフィルタリングしない - 異なるテナントIDが設定されている場合があるため）
        try:
            class_schedule = ClassSchedule.objects.get(id=class_schedule_id)
        except ClassSchedule.DoesNotExist:
            return Response({'error': 'ClassSchedule not found'}, status=404)

        # 日付パース
        try:
            absence_date = dt.fromisoformat(lesson_date).date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)

        # ClassScheduleからticket_idで消化記号を取得
        consumption_symbol = ''
        original_ticket = None
        if class_schedule.ticket_id:
            try:
                original_ticket = Ticket.objects.get(
                    ticket_code=class_schedule.ticket_id,
                    deleted_at__isnull=True
                )
                consumption_symbol = original_ticket.consumption_symbol or ''
            except Ticket.DoesNotExist:
                pass

        # 有効期限: 欠席日から90日
        valid_until = absence_date + timedelta(days=90)

        # 生徒のtenant_idを使用（integer型）
        student_tenant_id = student.tenant_id

        # AbsenceTicketを作成
        absence_ticket = AbsenceTicket.objects.create(
            tenant_id=student_tenant_id,
            student=student,
            original_ticket=original_ticket,
            consumption_symbol=consumption_symbol,
            absence_date=absence_date,
            class_schedule=class_schedule,
            status='issued',
            valid_until=valid_until,
            notes=reason or 'カレンダーからの欠席連絡',
        )

        return Response({
            'success': True,
            'message': '欠席登録が完了しました。欠席チケットが発行されました。',
            'absence_ticket_id': str(absence_ticket.id),
            'consumption_symbol': consumption_symbol,
            'valid_until': valid_until.isoformat(),
            'absence_date': absence_date.isoformat(),
        })


class AbsenceTicketListView(APIView):
    """欠席チケット（振替チケット）一覧取得API

    保護者の子供に関連する欠席チケットを返す。
    ステータス（issued/used/expired）でフィルタ可能。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.students.models import Student, Guardian, StudentGuardian
        from .models import AbsenceTicket
        from datetime import date

        tenant_id = getattr(request, 'tenant_id', None)
        if tenant_id is None and hasattr(request, 'user') and hasattr(request.user, 'tenant_id'):
            tenant_id = request.user.tenant_id

        status_filter = request.query_params.get('status')  # issued, used, expired
        student_id = request.query_params.get('student_id')

        # 保護者の子供を取得（StudentGuardian中間テーブル経由）
        try:
            guardian = Guardian.objects.get(user=request.user)
            student_ids = list(StudentGuardian.objects.filter(
                guardian=guardian
            ).values_list('student_id', flat=True))
        except Guardian.DoesNotExist:
            student_ids = []

        # 特定の生徒のみ取得する場合
        if student_id:
            student_ids = [student_id] if student_id in [str(sid) for sid in student_ids] else []

        if not student_ids:
            return Response([])

        # AbsenceTicketを取得
        queryset = AbsenceTicket.objects.filter(
            student_id__in=student_ids
        ).select_related(
            'student', 'original_ticket', 'class_schedule',
            'class_schedule__school', 'class_schedule__brand'
        ).order_by('-absence_date')

        # ステータスフィルタ
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 期限切れチケットの自動更新
        today = date.today()
        for ticket in queryset.filter(status='issued'):
            if ticket.valid_until and ticket.valid_until < today:
                ticket.status = 'expired'
                ticket.save(update_fields=['status'])

        # レスポンス生成
        tickets = []
        for ticket in queryset:
            school_name = ''
            brand_name = ''
            if ticket.class_schedule:
                if ticket.class_schedule.school:
                    school_name = ticket.class_schedule.school.school_name
                if ticket.class_schedule.brand:
                    brand_name = ticket.class_schedule.brand.brand_name

            tickets.append({
                'id': str(ticket.id),
                'studentId': str(ticket.student_id),
                'studentName': ticket.student.full_name if ticket.student else '',
                'originalTicketId': str(ticket.original_ticket_id) if ticket.original_ticket_id else None,
                'originalTicketName': ticket.original_ticket.ticket_name if ticket.original_ticket else '',
                'consumptionSymbol': ticket.consumption_symbol or '',
                'absenceDate': ticket.absence_date.isoformat() if ticket.absence_date else None,
                'status': ticket.status,
                'validUntil': ticket.valid_until.isoformat() if ticket.valid_until else None,
                'usedDate': ticket.used_date.isoformat() if ticket.used_date else None,
                'schoolId': str(ticket.class_schedule.school_id) if ticket.class_schedule and ticket.class_schedule.school_id else None,
                'schoolName': school_name,
                'brandId': str(ticket.class_schedule.brand_id) if ticket.class_schedule and ticket.class_schedule.brand_id else None,
                'brandName': brand_name,
                'classScheduleId': str(ticket.class_schedule_id) if ticket.class_schedule_id else None,
                'notes': ticket.notes or '',
                'createdAt': ticket.created_at.isoformat() if ticket.created_at else None,
            })

        return Response(tickets)


class UseAbsenceTicketView(APIView):
    """振替予約API（欠席チケット使用）

    欠席チケット（AbsenceTicket）を使って振替予約を行う。
    同じconsumption_symbolを持つClassScheduleを選んで予約できる。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.students.models import Student, Guardian, StudentGuardian
        from .models import AbsenceTicket, Attendance
        from apps.schools.models import ClassSchedule
        from datetime import date, datetime

        absence_ticket_id = request.data.get('absence_ticket_id')
        target_date = request.data.get('target_date')  # 振替先の日付 (YYYY-MM-DD)
        target_class_schedule_id = request.data.get('target_class_schedule_id')  # 振替先のクラス

        if not absence_ticket_id:
            return Response({'error': '欠席チケットIDが必要です'}, status=400)
        if not target_date:
            return Response({'error': '振替先の日付が必要です'}, status=400)
        if not target_class_schedule_id:
            return Response({'error': '振替先のクラスが必要です'}, status=400)

        # 保護者の子供を取得
        try:
            guardian = Guardian.objects.get(user=request.user)
            student_ids = list(StudentGuardian.objects.filter(
                guardian=guardian
            ).values_list('student_id', flat=True))
        except Guardian.DoesNotExist:
            return Response({'error': '保護者情報が見つかりません'}, status=404)

        # 欠席チケットを取得
        try:
            absence_ticket = AbsenceTicket.objects.get(
                id=absence_ticket_id,
                student_id__in=student_ids,
                status=AbsenceTicket.Status.ISSUED
            )
        except AbsenceTicket.DoesNotExist:
            return Response({'error': '有効な欠席チケットが見つかりません'}, status=404)

        # 有効期限チェック
        if absence_ticket.valid_until and absence_ticket.valid_until < date.today():
            return Response({'error': 'このチケットは期限切れです'}, status=400)

        # 振替先のクラスを取得
        try:
            target_schedule = ClassSchedule.objects.get(
                id=target_class_schedule_id,
                is_active=True
            )
        except ClassSchedule.DoesNotExist:
            return Response({'error': '振替先のクラスが見つかりません'}, status=404)

        # 振替先日付をパース
        try:
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': '日付形式が不正です（YYYY-MM-DD）'}, status=400)

        # 過去の日付チェック
        if target_date_obj < date.today():
            return Response({'error': '過去の日付には振替できません'}, status=400)

        # 曜日チェック（振替先のクラスの曜日と一致するか）
        if target_schedule.day_of_week != target_date_obj.weekday():
            day_names = ['月', '火', '水', '木', '金', '土', '日']
            return Response({
                'error': f'このクラスは{day_names[target_schedule.day_of_week]}曜日のみ開講しています'
            }, status=400)

        # 欠席チケットを使用済みに更新
        absence_ticket.status = AbsenceTicket.Status.USED
        absence_ticket.used_date = target_date_obj
        absence_ticket.used_class_schedule = target_schedule
        absence_ticket.save()

        # 振替先の出席記録を作成（予約済みステータス）
        Attendance.objects.create(
            tenant_id=absence_ticket.tenant_id,
            student=absence_ticket.student,
            class_schedule=target_schedule,
            lesson_date=target_date_obj,
            status='reserved',  # 振替予約
            notes=f'振替予約（元: {absence_ticket.absence_date}）'
        )

        return Response({
            'success': True,
            'message': f'{target_date_obj.strftime("%m/%d")}に振替予約しました',
            'absenceTicketId': str(absence_ticket.id),
            'targetDate': target_date,
            'targetClassScheduleId': str(target_schedule.id),
        })


class TransferAvailableClassesView(APIView):
    """振替可能クラス取得API

    欠席チケットのconsumption_symbolを基に、振替可能なクラス一覧を返す。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.students.models import Guardian, StudentGuardian
        from .models import AbsenceTicket
        from apps.schools.models import ClassSchedule
        from datetime import date

        absence_ticket_id = request.query_params.get('absence_ticket_id')
        if not absence_ticket_id:
            return Response({'error': '欠席チケットIDが必要です'}, status=400)

        # 保護者の子供を取得
        try:
            guardian = Guardian.objects.get(user=request.user)
            student_ids = list(StudentGuardian.objects.filter(
                guardian=guardian
            ).values_list('student_id', flat=True))
        except Guardian.DoesNotExist:
            return Response({'error': '保護者情報が見つかりません'}, status=404)

        # 欠席チケットを取得
        try:
            absence_ticket = AbsenceTicket.objects.select_related(
                'class_schedule', 'class_schedule__school', 'class_schedule__brand'
            ).get(
                id=absence_ticket_id,
                student_id__in=student_ids,
                status=AbsenceTicket.Status.ISSUED
            )
        except AbsenceTicket.DoesNotExist:
            return Response({'error': '有効な欠席チケットが見つかりません'}, status=404)

        # 同じconsumption_symbolを持つClassScheduleを検索
        available_classes = ClassSchedule.objects.filter(
            is_active=True
        ).select_related('school', 'brand', 'ticket')

        # consumption_symbolでフィルタ（ticketを通じて）
        if absence_ticket.consumption_symbol:
            available_classes = available_classes.filter(
                ticket__consumption_symbol=absence_ticket.consumption_symbol
            )

        day_names = ['月', '火', '水', '木', '金', '土', '日']
        classes = []
        for cs in available_classes:
            classes.append({
                'id': str(cs.id),
                'schoolId': str(cs.school_id) if cs.school_id else None,
                'schoolName': cs.school.school_name if cs.school else '',
                'brandId': str(cs.brand_id) if cs.brand_id else None,
                'brandName': cs.brand.brand_name if cs.brand else '',
                'dayOfWeek': cs.day_of_week,
                'dayOfWeekLabel': day_names[cs.day_of_week] if cs.day_of_week is not None else '',
                'startTime': cs.start_time.strftime('%H:%M') if cs.start_time else '',
                'endTime': cs.end_time.strftime('%H:%M') if cs.end_time else '',
                'className': cs.class_name or '',
                'roomName': cs.room.room_name if cs.room else '',
                'maxStudents': cs.max_students,
                'currentStudents': cs.current_students,
            })

        return Response({
            'absenceTicket': {
                'id': str(absence_ticket.id),
                'consumptionSymbol': absence_ticket.consumption_symbol or '',
                'absenceDate': absence_ticket.absence_date.isoformat() if absence_ticket.absence_date else None,
                'validUntil': absence_ticket.valid_until.isoformat() if absence_ticket.valid_until else None,
            },
            'availableClasses': classes
        })

"""
Absence Views - 欠席・振替チケット関連Views
MarkAbsenceView, AbsenceTicketListView, UseAbsenceTicketView, TransferAvailableClassesView
"""
from datetime import date, datetime, timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


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
        from ..models import AbsenceTicket

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

        # 退会済み生徒で退会日を過ぎている場合はエラー
        if student.status == 'withdrawn' and student.withdrawal_date and date.today() > student.withdrawal_date:
            return Response({'error': '退会日を過ぎているため、欠席登録はできません'}, status=400)

        # ClassSchedule取得
        try:
            class_schedule = ClassSchedule.objects.get(id=class_schedule_id)
        except ClassSchedule.DoesNotExist:
            return Response({'error': 'ClassSchedule not found'}, status=404)

        # 日付パース
        try:
            absence_date = datetime.fromisoformat(lesson_date).date()
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
        from ..models import AbsenceTicket

        tenant_id = getattr(request, 'tenant_id', None)
        if tenant_id is None and hasattr(request, 'user') and hasattr(request.user, 'tenant_id'):
            tenant_id = request.user.tenant_id

        status_filter = request.query_params.get('status')
        student_id = request.query_params.get('student_id')

        # 保護者の子供を取得
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

            # 使用可能かどうか判定
            can_use = True
            unavailable_reason = None
            student = ticket.student
            if student and student.status == 'withdrawn' and student.withdrawal_date and today > student.withdrawal_date:
                can_use = False
                unavailable_reason = '退会日を過ぎているため使用できません'
            elif ticket.status != 'issued':
                can_use = False
            elif ticket.valid_until and ticket.valid_until < today:
                can_use = False
                unavailable_reason = '有効期限が切れています'

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
                'canUse': can_use,
                'unavailableReason': unavailable_reason,
            })

        return Response(tickets)


class UseAbsenceTicketView(APIView):
    """振替予約API（欠席チケット使用）

    欠席チケット（AbsenceTicket）を使って振替予約を行う。
    同じconsumption_symbolを持つClassScheduleを選んで予約できる。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.students.models import Guardian, StudentGuardian
        from ..models import AbsenceTicket, Attendance, LessonSchedule
        from apps.schools.models import ClassSchedule

        absence_ticket_id = request.data.get('absence_ticket_id')
        target_date = request.data.get('target_date')
        target_class_schedule_id = request.data.get('target_class_schedule_id')

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
            absence_ticket = AbsenceTicket.objects.select_related('student').get(
                id=absence_ticket_id,
                student_id__in=student_ids,
                status=AbsenceTicket.Status.ISSUED
            )
        except AbsenceTicket.DoesNotExist:
            return Response({'error': '有効な欠席チケットが見つかりません'}, status=404)

        # 退会済み生徒で退会日を過ぎている場合はエラー
        student = absence_ticket.student
        if student.status == 'withdrawn' and student.withdrawal_date and date.today() > student.withdrawal_date:
            return Response({'error': '退会日を過ぎているため、振替チケットは使用できません'}, status=400)

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

        # 当日振替の場合、授業開始30分前までかチェック
        if target_date_obj == date.today():
            now = datetime.now()
            class_start_datetime = datetime.combine(target_date_obj, target_schedule.start_time)
            minutes_until_class = (class_start_datetime - now).total_seconds() / 60

            if minutes_until_class < 30:
                return Response({
                    'error': '当日の振替予約は授業開始30分前までです'
                }, status=400)

        # 曜日チェック
        js_weekday = (target_date_obj.weekday() + 1) % 7
        if target_schedule.day_of_week != js_weekday:
            day_names = ['日', '月', '火', '水', '木', '金', '土']
            return Response({
                'error': f'このクラスは{day_names[target_schedule.day_of_week]}曜日のみ開講しています'
            }, status=400)

        # 欠席チケットを使用済みに更新
        absence_ticket.status = AbsenceTicket.Status.USED
        absence_ticket.used_date = target_date_obj
        absence_ticket.used_class_schedule = target_schedule
        absence_ticket.save()

        # 振替先のLessonScheduleを取得または作成
        lesson_schedule, created = LessonSchedule.objects.get_or_create(
            tenant_id=absence_ticket.tenant_id,
            school=target_schedule.school,
            date=target_date_obj,
            start_time=target_schedule.start_time,
            end_time=target_schedule.end_time,
            defaults={
                'lesson_type': LessonSchedule.LessonType.GROUP,
                'status': LessonSchedule.Status.SCHEDULED,
            }
        )

        # 振替先の出席記録を作成
        Attendance.objects.create(
            tenant_id=absence_ticket.tenant_id,
            schedule=lesson_schedule,
            student=absence_ticket.student,
            status=Attendance.Status.MAKEUP,
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
        from ..models import AbsenceTicket
        from apps.schools.models import ClassSchedule

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
                'student', 'class_schedule', 'class_schedule__school', 'class_schedule__brand'
            ).get(
                id=absence_ticket_id,
                student_id__in=student_ids,
                status=AbsenceTicket.Status.ISSUED
            )
        except AbsenceTicket.DoesNotExist:
            return Response({'error': '有効な欠席チケットが見つかりません'}, status=404)

        # 退会済み生徒で退会日を過ぎている場合はエラー
        student = absence_ticket.student
        if student and student.status == 'withdrawn' and student.withdrawal_date and date.today() > student.withdrawal_date:
            return Response({'error': '退会日を過ぎているため、振替チケットは使用できません'}, status=400)

        # 同じconsumption_symbolを持つClassScheduleを検索
        available_classes = ClassSchedule.objects.filter(
            is_active=True
        ).select_related('school', 'brand')

        import sys
        print(f"[TransferAvailableClasses] absence_ticket.consumption_symbol={absence_ticket.consumption_symbol}", file=sys.stderr, flush=True)
        print(f"[TransferAvailableClasses] Total active ClassSchedules: {available_classes.count()}", file=sys.stderr, flush=True)

        # consumption_symbolでフィルタ
        if absence_ticket.consumption_symbol:
            from apps.contracts.models import Ticket
            matching_ticket_codes = list(Ticket.objects.filter(
                consumption_symbol=absence_ticket.consumption_symbol
            ).values_list('ticket_code', flat=True))
            print(f"[TransferAvailableClasses] matching_ticket_codes={matching_ticket_codes}", file=sys.stderr, flush=True)

            if matching_ticket_codes:
                available_classes = available_classes.filter(
                    ticket_id__in=matching_ticket_codes
                )
            print(f"[TransferAvailableClasses] After filter: {available_classes.count()} classes", file=sys.stderr, flush=True)
        else:
            print(f"[TransferAvailableClasses] No consumption_symbol, returning all classes", file=sys.stderr, flush=True)

        day_names = ['日', '月', '火', '水', '木', '金', '土']
        classes = []
        for cs in available_classes:
            max_seat = cs.capacity or 10
            current_seat = cs.reserved_seats or 0
            available_seats = max(0, max_seat - current_seat)

            period_display = ''
            if cs.start_time and cs.end_time:
                period_display = f"{cs.start_time.strftime('%H:%M')}〜{cs.end_time.strftime('%H:%M')}"
            elif cs.start_time:
                period_display = cs.start_time.strftime('%H:%M')

            classes.append({
                'id': str(cs.id),
                'schoolId': str(cs.school_id) if cs.school_id else None,
                'schoolName': cs.school.school_name if cs.school else '',
                'brandId': str(cs.brand_id) if cs.brand_id else None,
                'brandName': cs.brand.brand_name if cs.brand else '',
                'dayOfWeek': cs.day_of_week,
                'dayOfWeekDisplay': day_names[cs.day_of_week] if cs.day_of_week is not None and 0 <= cs.day_of_week <= 6 else '',
                'period': cs.period or 1,
                'periodDisplay': period_display,
                'className': cs.class_name or '',
                'currentSeat': current_seat,
                'maxSeat': max_seat,
                'availableSeats': available_seats,
            })

        return Response(classes)

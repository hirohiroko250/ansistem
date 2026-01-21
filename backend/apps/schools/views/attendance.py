"""
Attendance Views - 出欠管理関連
AdminMarkAttendanceView, AdminAbsenceTicketListView
"""
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.permissions import IsTenantUser
from apps.core.exceptions import StudentNotFoundError, NotFoundError
from ..models import ClassSchedule


class AdminMarkAttendanceView(APIView):
    """管理者用出欠登録API

    出席/欠席を登録する。
    欠席の場合はAbsenceTicketを作成する。
    """
    permission_classes = [IsAuthenticated, IsTenantUser]

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
            raise StudentNotFoundError()

        # ClassSchedule取得
        try:
            schedule = ClassSchedule.objects.get(id=schedule_id)
        except ClassSchedule.DoesNotExist:
            raise NotFoundError('スケジュールが見つかりません')

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
            from apps.lessons.models import AbsenceTicket
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
    permission_classes = [IsAuthenticated, IsTenantUser]

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

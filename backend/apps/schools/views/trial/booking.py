"""
Trial Booking Views - 体験予約Views
PublicTrialBookingView
"""
import sys
from datetime import datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ...models import SchoolSchedule, LessonCalendar


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
        from apps.students.models import Student, TrialBooking
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

        # 生徒を取得
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

        # チャット通知を送信
        try:
            from apps.communications.models import Channel, Message

            channel = None
            if guardian:
                channel = Channel.objects.filter(
                    guardian=guardian,
                    channel_type=Channel.ChannelType.EXTERNAL
                ).first()

                if not channel:
                    channel = Channel.objects.create(
                        tenant_id=tenant_id,
                        channel_type=Channel.ChannelType.EXTERNAL,
                        name=f'{guardian.full_name}',
                        guardian=guardian,
                    )

            if channel:
                Message.objects.create(
                    tenant_id=tenant_id,
                    channel=channel,
                    message_type=Message.MessageType.SYSTEM,
                    content=f'体験授業のご予約ありがとうございます。\n\n'
                           f'【予約内容】\n'
                           f'お子様: {student.full_name}\n'
                           f'校舎: {schedule.school.school_name}\n'
                           f'ブランド: {schedule.brand.brand_name}\n'
                           f'日時: {trial_date.strftime("%Y年%m月%d日")} {time_str}\n\n'
                           f'当日お待ちしております。',
                    is_bot_message=True,
                )
        except Exception as e:
            print(f"[TrialBooking] Failed to send chat notification: {e}", file=sys.stderr)

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

"""
QR Attendance Views - QRコード出席打刻
"""
from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from apps.students.models import Student
from apps.core.permissions import IsTenantUser
from ..models import LessonSchedule, Attendance


class QRCheckInView(APIView):
    """QRコードで出席打刻（入室）"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def post(self, request):
        qr_code = request.data.get('qr_code')
        school_id = request.data.get('school_id')

        if not qr_code:
            return Response(
                {'error': 'QRコードが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not school_id:
            return Response(
                {'error': '校舎IDが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # QRコードから生徒を特定
        try:
            student = Student.objects.get(qr_code=qr_code, deleted_at__isnull=True)
        except Student.DoesNotExist:
            return Response(
                {'error': '無効なQRコードです'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 現在時刻を取得
        now = timezone.localtime(timezone.now())
        current_date = now.date()
        current_time = now.time()

        # 許容範囲（±15分）
        time_margin = timedelta(minutes=15)
        now_datetime = timezone.now()
        start_range = (now_datetime - time_margin).time()
        end_range = (now_datetime + time_margin).time()

        # 該当する授業スケジュールを検索
        # 条件：今日の日付、指定校舎、該当生徒、開始時刻が±15分以内
        schedules = LessonSchedule.objects.filter(
            school_id=school_id,
            date=current_date,
            status__in=['scheduled', 'confirmed', 'in_progress'],
            deleted_at__isnull=True
        ).filter(
            # 個別授業の場合：生徒が直接紐づいている
            Q(student=student) |
            # 集団授業の場合：enrollmentsで紐づいている
            Q(group_enrollments__student=student, group_enrollments__deleted_at__isnull=True)
        ).distinct()

        # 開始時刻でフィルタ（現在時刻の±15分以内、または既に開始して終了前）
        matching_schedule = None
        for schedule in schedules:
            # 授業開始時刻から15分前〜授業終了時刻までが打刻可能範囲
            schedule_start_datetime = timezone.make_aware(
                timezone.datetime.combine(schedule.date, schedule.start_time)
            )
            schedule_end_datetime = timezone.make_aware(
                timezone.datetime.combine(schedule.date, schedule.end_time)
            )
            earliest_checkin = schedule_start_datetime - time_margin

            if earliest_checkin <= now_datetime <= schedule_end_datetime:
                matching_schedule = schedule
                break

        if not matching_schedule:
            return Response(
                {
                    'error': '現在時刻に該当する授業が見つかりません',
                    'student_name': student.full_name,
                    'current_time': current_time.strftime('%H:%M'),
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # 出席レコードを作成または更新
        attendance, created = Attendance.objects.get_or_create(
            schedule=matching_schedule,
            student=student,
            defaults={
                'tenant_id': matching_schedule.tenant_id,
                'status': 'present',
                'check_in_time': current_time,
            }
        )

        if not created:
            # 既に出席レコードがある場合、check_in_timeを更新
            if not attendance.check_in_time:
                attendance.check_in_time = current_time
                attendance.status = 'present'
                attendance.save(update_fields=['check_in_time', 'status'])

        # 授業ステータスを「実施中」に更新
        if matching_schedule.status == 'scheduled':
            matching_schedule.status = 'confirmed'
            matching_schedule.save(update_fields=['status'])

        return Response({
            'success': True,
            'student_name': student.full_name,
            'student_no': student.student_no,
            'check_in_time': current_time.strftime('%H:%M'),
            'schedule_info': f"{matching_schedule.date} {matching_schedule.start_time.strftime('%H:%M')}-{matching_schedule.end_time.strftime('%H:%M')}",
            'class_name': matching_schedule.class_name or (matching_schedule.subject.subject_name if matching_schedule.subject else ''),
            'status': 'present',
            'message': '出席を記録しました',
        })


class QRCheckOutView(APIView):
    """QRコードで退出打刻"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def post(self, request):
        qr_code = request.data.get('qr_code')
        school_id = request.data.get('school_id')

        if not qr_code:
            return Response(
                {'error': 'QRコードが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not school_id:
            return Response(
                {'error': '校舎IDが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # QRコードから生徒を特定
        try:
            student = Student.objects.get(qr_code=qr_code, deleted_at__isnull=True)
        except Student.DoesNotExist:
            return Response(
                {'error': '無効なQRコードです'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 現在時刻を取得
        now = timezone.localtime(timezone.now())
        current_date = now.date()
        current_time = now.time()

        # 今日の出席レコードで、check_in_timeがあってcheck_out_timeがないものを検索
        attendance = Attendance.objects.filter(
            student=student,
            schedule__school_id=school_id,
            schedule__date=current_date,
            check_in_time__isnull=False,
            check_out_time__isnull=True,
            deleted_at__isnull=True
        ).select_related('schedule', 'schedule__subject').first()

        if not attendance:
            return Response(
                {
                    'error': '出席記録が見つかりません。先に入室打刻を行ってください。',
                    'student_name': student.full_name,
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # 退出時刻を記録
        attendance.check_out_time = current_time
        attendance.save(update_fields=['check_out_time'])

        schedule = attendance.schedule

        return Response({
            'success': True,
            'student_name': student.full_name,
            'student_no': student.student_no,
            'check_in_time': attendance.check_in_time.strftime('%H:%M'),
            'check_out_time': current_time.strftime('%H:%M'),
            'schedule_info': f"{schedule.date} {schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}",
            'class_name': schedule.class_name or (schedule.subject.subject_name if schedule.subject else ''),
            'message': '退出を記録しました',
        })

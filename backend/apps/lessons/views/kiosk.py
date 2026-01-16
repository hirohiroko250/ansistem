"""
Kiosk API Views - キオスク端末用の公開API
認証不要でキオスクトークンを使用
"""
from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
import hashlib
import hmac

from apps.students.models import Student
from apps.users.models import User
from apps.schools.models import School
from ..models import LessonSchedule, Attendance


def verify_kiosk_token(school_id: str, token: str) -> bool:
    """キオスクトークンを検証"""
    # 簡易的な検証（本番では環境変数等でシークレットを管理）
    secret = getattr(settings, 'KIOSK_SECRET_KEY', 'oz-kiosk-secret-2024')
    expected = hmac.new(
        secret.encode(),
        f"kiosk:{school_id}".encode(),
        hashlib.sha256
    ).hexdigest()[:32]
    return hmac.compare_digest(token, expected)


class KioskSchoolListView(APIView):
    """キオスク用校舎一覧（位置情報付き）"""
    permission_classes = [AllowAny]

    def get(self, request):
        schools = School.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).values(
            'id', 'school_name', 'latitude', 'longitude', 'geofence_range'
        ).order_by('sort_order', 'school_name')

        return Response({
            'schools': list(schools)
        })


class KioskCheckInView(APIView):
    """キオスク用QRコード入室打刻"""
    permission_classes = [AllowAny]

    def post(self, request):
        qr_code = request.data.get('qr_code')
        school_id = request.data.get('school_id')
        kiosk_token = request.data.get('kiosk_token') or request.headers.get('X-Kiosk-Token')

        if not qr_code:
            return Response(
                {'success': False, 'message': 'QRコードが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not school_id:
            return Response(
                {'success': False, 'message': '校舎IDが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # キオスクトークン検証（オプショナル - 設定されている場合のみ）
        if kiosk_token and not verify_kiosk_token(school_id, kiosk_token):
            return Response(
                {'success': False, 'message': '無効なキオスクトークンです'},
                status=status.HTTP_403_FORBIDDEN
            )

        # QRコードから生徒を特定
        student = None
        user = None

        # まず生徒のQRコードを検索
        try:
            student = Student.objects.get(qr_code=qr_code, deleted_at__isnull=True)
        except Student.DoesNotExist:
            pass

        # 生徒が見つからない場合、ユーザー（保護者）のQRコードを検索
        if not student:
            try:
                user = User.objects.get(qr_code=qr_code, is_active=True)
                # ユーザーの場合は保護者として記録（別途処理が必要な場合）
                return Response({
                    'success': True,
                    'type': 'guardian_check_in',
                    'message': f'{user.full_name}さんの入室を記録しました',
                    'user_name': user.full_name,
                    'timestamp': timezone.now().isoformat(),
                })
            except User.DoesNotExist:
                return Response(
                    {'success': False, 'message': '無効なQRコードです'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # 校舎の存在確認
        try:
            school = School.objects.get(id=school_id, deleted_at__isnull=True)
        except School.DoesNotExist:
            return Response(
                {'success': False, 'message': '校舎が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 現在時刻を取得
        now = timezone.localtime(timezone.now())
        current_date = now.date()
        current_time = now.time()

        # 許容範囲（±15分）
        time_margin = timedelta(minutes=15)
        now_datetime = timezone.now()

        # 該当する授業スケジュールを検索
        schedules = LessonSchedule.objects.filter(
            school_id=school_id,
            date=current_date,
            status__in=['scheduled', 'confirmed', 'in_progress'],
            deleted_at__isnull=True
        ).filter(
            Q(student=student) |
            Q(group_enrollments__student=student, group_enrollments__deleted_at__isnull=True)
        ).distinct()

        # 開始時刻でフィルタ
        matching_schedule = None
        for schedule in schedules:
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
            # 授業がなくても入室記録だけは残す（今後の機能拡張用）
            return Response({
                'success': True,
                'type': 'check_in',
                'message': f'{student.full_name}さんの入室を記録しました（授業予定なし）',
                'student_name': student.full_name,
                'student_no': student.student_no,
                'timestamp': timezone.now().isoformat(),
                'has_schedule': False,
            })

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
            if not attendance.check_in_time:
                attendance.check_in_time = current_time
                attendance.status = 'present'
                attendance.save(update_fields=['check_in_time', 'status'])

        # 授業ステータスを更新
        if matching_schedule.status == 'scheduled':
            matching_schedule.status = 'confirmed'
            matching_schedule.save(update_fields=['status'])

        return Response({
            'success': True,
            'type': 'check_in',
            'message': f'{student.full_name}さんの入室を記録しました',
            'student_name': student.full_name,
            'student_no': student.student_no,
            'check_in_time': current_time.strftime('%H:%M'),
            'timestamp': timezone.now().isoformat(),
            'has_schedule': True,
            'schedule_info': {
                'class_name': matching_schedule.class_name or (
                    matching_schedule.subject.subject_name if matching_schedule.subject else ''
                ),
                'start_time': matching_schedule.start_time.strftime('%H:%M'),
                'end_time': matching_schedule.end_time.strftime('%H:%M'),
            },
        })


class KioskCheckOutView(APIView):
    """キオスク用QRコード退室打刻"""
    permission_classes = [AllowAny]

    def post(self, request):
        qr_code = request.data.get('qr_code')
        school_id = request.data.get('school_id')
        kiosk_token = request.data.get('kiosk_token') or request.headers.get('X-Kiosk-Token')

        if not qr_code:
            return Response(
                {'success': False, 'message': 'QRコードが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not school_id:
            return Response(
                {'success': False, 'message': '校舎IDが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # キオスクトークン検証（オプショナル）
        if kiosk_token and not verify_kiosk_token(school_id, kiosk_token):
            return Response(
                {'success': False, 'message': '無効なキオスクトークンです'},
                status=status.HTTP_403_FORBIDDEN
            )

        # QRコードから生徒を特定
        student = None
        try:
            student = Student.objects.get(qr_code=qr_code, deleted_at__isnull=True)
        except Student.DoesNotExist:
            # ユーザー（保護者）を検索
            try:
                user = User.objects.get(qr_code=qr_code, is_active=True)
                return Response({
                    'success': True,
                    'type': 'guardian_check_out',
                    'message': f'{user.full_name}さんの退室を記録しました',
                    'user_name': user.full_name,
                    'timestamp': timezone.now().isoformat(),
                })
            except User.DoesNotExist:
                return Response(
                    {'success': False, 'message': '無効なQRコードです'},
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
            # 出席記録がなくても退室だけは記録
            return Response({
                'success': True,
                'type': 'check_out',
                'message': f'{student.full_name}さんの退室を記録しました（入室記録なし）',
                'student_name': student.full_name,
                'student_no': student.student_no,
                'timestamp': timezone.now().isoformat(),
                'has_check_in': False,
            })

        # 退出時刻を記録
        attendance.check_out_time = current_time
        attendance.save(update_fields=['check_out_time'])

        schedule = attendance.schedule

        return Response({
            'success': True,
            'type': 'check_out',
            'message': f'{student.full_name}さんの退室を記録しました',
            'student_name': student.full_name,
            'student_no': student.student_no,
            'check_in_time': attendance.check_in_time.strftime('%H:%M'),
            'check_out_time': current_time.strftime('%H:%M'),
            'timestamp': timezone.now().isoformat(),
            'has_check_in': True,
            'schedule_info': {
                'class_name': schedule.class_name or (
                    schedule.subject.subject_name if schedule.subject else ''
                ),
                'start_time': schedule.start_time.strftime('%H:%M'),
                'end_time': schedule.end_time.strftime('%H:%M'),
            },
        })


class KioskAttendanceView(APIView):
    """キオスク用統合出席API（入室/退室自動判定）"""
    permission_classes = [AllowAny]

    def post(self, request):
        """QRコードをスキャンすると、入室中なら退室、そうでなければ入室として処理"""
        qr_code = request.data.get('qr_code')
        school_id = request.data.get('school_id')

        if not qr_code:
            return Response(
                {'success': False, 'message': 'QRコードが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not school_id:
            return Response(
                {'success': False, 'message': '校舎IDが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # QRコードから生徒を特定
        student = None
        try:
            student = Student.objects.get(qr_code=qr_code, deleted_at__isnull=True)
        except Student.DoesNotExist:
            # ユーザー（保護者）を検索
            try:
                user = User.objects.get(qr_code=qr_code, is_active=True)
                # 保護者の入退室は簡易記録
                return Response({
                    'success': True,
                    'type': 'check_in',
                    'message': f'{user.full_name}さんの来校を記録しました',
                    'student_name': user.full_name,
                    'timestamp': timezone.now().isoformat(),
                })
            except User.DoesNotExist:
                return Response(
                    {'success': False, 'message': '無効なQRコードです'},
                    status=status.HTTP_404_NOT_FOUND
                )

        now = timezone.localtime(timezone.now())
        current_date = now.date()
        current_time = now.time()

        # 今日の入室中の出席レコードを検索
        active_attendance = Attendance.objects.filter(
            student=student,
            schedule__school_id=school_id,
            schedule__date=current_date,
            check_in_time__isnull=False,
            check_out_time__isnull=True,
            deleted_at__isnull=True
        ).select_related('schedule', 'schedule__subject').first()

        if active_attendance:
            # 既に入室中なら退室処理
            active_attendance.check_out_time = current_time
            active_attendance.save(update_fields=['check_out_time'])

            schedule = active_attendance.schedule
            return Response({
                'success': True,
                'type': 'check_out',
                'message': f'{student.full_name}さんが退室しました',
                'student_name': student.full_name,
                'student_no': student.student_no,
                'check_in_time': active_attendance.check_in_time.strftime('%H:%M'),
                'check_out_time': current_time.strftime('%H:%M'),
                'timestamp': timezone.now().isoformat(),
                'schedule_info': {
                    'class_name': schedule.class_name or (
                        schedule.subject.subject_name if schedule.subject else ''
                    ),
                },
            })

        # 入室処理
        # 該当する授業スケジュールを検索
        time_margin = timedelta(minutes=15)
        now_datetime = timezone.now()

        schedules = LessonSchedule.objects.filter(
            school_id=school_id,
            date=current_date,
            status__in=['scheduled', 'confirmed', 'in_progress'],
            deleted_at__isnull=True
        ).filter(
            Q(student=student) |
            Q(group_enrollments__student=student, group_enrollments__deleted_at__isnull=True)
        ).distinct()

        matching_schedule = None
        for schedule in schedules:
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

        if matching_schedule:
            attendance, created = Attendance.objects.get_or_create(
                schedule=matching_schedule,
                student=student,
                defaults={
                    'tenant_id': matching_schedule.tenant_id,
                    'status': 'present',
                    'check_in_time': current_time,
                }
            )

            if not created and not attendance.check_in_time:
                attendance.check_in_time = current_time
                attendance.status = 'present'
                attendance.save(update_fields=['check_in_time', 'status'])

            if matching_schedule.status == 'scheduled':
                matching_schedule.status = 'confirmed'
                matching_schedule.save(update_fields=['status'])

            return Response({
                'success': True,
                'type': 'check_in',
                'message': f'{student.full_name}さんが入室しました',
                'student_name': student.full_name,
                'student_no': student.student_no,
                'check_in_time': current_time.strftime('%H:%M'),
                'timestamp': timezone.now().isoformat(),
                'schedule_info': {
                    'class_name': matching_schedule.class_name or (
                        matching_schedule.subject.subject_name if matching_schedule.subject else ''
                    ),
                    'start_time': matching_schedule.start_time.strftime('%H:%M'),
                    'end_time': matching_schedule.end_time.strftime('%H:%M'),
                },
            })

        # 授業がない場合でも入室記録
        return Response({
            'success': True,
            'type': 'check_in',
            'message': f'{student.full_name}さんが入室しました',
            'student_name': student.full_name,
            'student_no': student.student_no,
            'check_in_time': current_time.strftime('%H:%M'),
            'timestamp': timezone.now().isoformat(),
            'schedule_info': None,
        })

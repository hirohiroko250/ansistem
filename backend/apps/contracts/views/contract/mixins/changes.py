"""
Change Actions Mixin - 変更申請アクション
ChangeActionsMixin
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.contracts.models import StudentItem, ContractChangeRequest
from apps.contracts.serializers import MyStudentItemSerializer


class ChangeActionsMixin:
    """変更申請アクションMixin"""

    @action(detail=True, methods=['post'], url_path='change-class', permission_classes=[IsAuthenticated])
    def change_class(self, request, pk=None):
        """クラス変更（曜日・時間変更）"""
        from apps.schools.models import ClassSchedule
        from apps.students.models import Guardian, StudentGuardian, StudentEnrollment

        user = request.user
        request_tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得
        try:
            if request_tenant_id:
                guardian = Guardian.objects.get(user=user, tenant_id=request_tenant_id, deleted_at__isnull=True)
            else:
                guardian = Guardian.objects.filter(user=user, deleted_at__isnull=True).first()
                if not guardian:
                    raise Guardian.DoesNotExist()
        except Guardian.DoesNotExist:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = guardian.tenant_id

        # 保護者に紐づく生徒を取得
        student_ids = StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id
        ).values_list('student_id', flat=True)

        # StudentItemを取得（自分の子供のものか確認）
        try:
            student_item = StudentItem.objects.get(
                id=pk,
                student_id__in=student_ids,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except StudentItem.DoesNotExist:
            return Response(
                {'error': '指定された受講情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # リクエストデータ
        new_day_of_week = request.data.get('new_day_of_week')
        new_start_time = request.data.get('new_start_time')
        new_class_schedule_id = request.data.get('new_class_schedule_id')

        if not all([new_day_of_week is not None, new_start_time, new_class_schedule_id]):
            return Response(
                {'error': '曜日、開始時間、クラススケジュールIDは必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # クラススケジュールを取得して検証
        try:
            class_schedule = ClassSchedule.objects.get(
                id=new_class_schedule_id,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except ClassSchedule.DoesNotExist:
            return Response(
                {'error': '指定されたクラススケジュールが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 同じ校舎かチェック
        if class_schedule.school_id != student_item.school_id:
            return Response(
                {'error': '校舎が異なります。校舎変更は別のAPIをご利用ください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 翌週の開始日を計算
        today = timezone.now().date()
        days_until_next_week = 7 - today.weekday()
        next_monday = today + timedelta(days=days_until_next_week)
        effective_date = request.data.get('effective_date', next_monday.isoformat())

        # StudentItemを更新
        student_item.day_of_week = int(new_day_of_week)
        student_item.start_time = new_start_time
        if hasattr(class_schedule, 'end_time'):
            student_item.end_time = class_schedule.end_time
        student_item.save()

        # effective_dateをdate型に変換
        if isinstance(effective_date, str):
            effective_date_obj = datetime.strptime(effective_date, '%Y-%m-%d').date()
        else:
            effective_date_obj = effective_date

        if student_item.school and student_item.brand:
            StudentEnrollment.create_enrollment(
                student=student_item.student,
                school=student_item.school,
                brand=student_item.brand,
                class_schedule=class_schedule,
                change_type=StudentEnrollment.ChangeType.CLASS_CHANGE,
                effective_date=effective_date_obj,
                student_item=student_item,
                notes=f'クラス変更: {class_schedule}',
            )

        return Response({
            'success': True,
            'message': f'{effective_date}からクラスが変更されます',
            'contract': MyStudentItemSerializer(student_item).data,
            'effective_date': effective_date
        })

    @action(detail=True, methods=['post'], url_path='change-school', permission_classes=[IsAuthenticated])
    def change_school(self, request, pk=None):
        """校舎変更"""
        from apps.schools.models import School
        from apps.students.models import Guardian, StudentGuardian

        user = request.user
        request_tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得
        try:
            if request_tenant_id:
                guardian = Guardian.objects.get(user=user, tenant_id=request_tenant_id, deleted_at__isnull=True)
            else:
                guardian = Guardian.objects.filter(user=user, deleted_at__isnull=True).first()
                if not guardian:
                    raise Guardian.DoesNotExist()
        except Guardian.DoesNotExist:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = guardian.tenant_id

        # 保護者に紐づく生徒を取得
        student_ids = StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id
        ).values_list('student_id', flat=True)

        # StudentItemを取得（自分の子供のものか確認）
        try:
            student_item = StudentItem.objects.get(
                id=pk,
                student_id__in=student_ids,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except StudentItem.DoesNotExist:
            return Response(
                {'error': '指定された受講情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # リクエストデータ
        new_school_id = request.data.get('new_school_id')
        new_day_of_week = request.data.get('new_day_of_week')
        new_start_time = request.data.get('new_start_time')

        if not all([new_school_id, new_day_of_week is not None, new_start_time]):
            return Response(
                {'error': '校舎ID、曜日、開始時間は必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 校舎を取得して検証
        try:
            new_school = School.objects.get(
                id=new_school_id,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except School.DoesNotExist:
            return Response(
                {'error': '指定された校舎が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 翌週の開始日を計算
        today = timezone.now().date()
        days_until_next_week = 7 - today.weekday()
        next_monday = today + timedelta(days=days_until_next_week)
        effective_date = request.data.get('effective_date', next_monday.isoformat())

        # StudentItemを更新
        student_item.school = new_school
        student_item.day_of_week = int(new_day_of_week)
        student_item.start_time = new_start_time
        student_item.save()

        return Response({
            'success': True,
            'message': f'{effective_date}から校舎が{new_school.school_name}に変更されます',
            'contract': MyStudentItemSerializer(student_item).data,
            'effective_date': effective_date
        })

    @action(detail=True, methods=['post'], url_path='request-suspension', permission_classes=[IsAuthenticated])
    def request_suspension(self, request, pk=None):
        """休会申請"""
        from apps.students.models import Guardian, StudentGuardian

        user = request.user
        request_tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得
        try:
            if request_tenant_id:
                guardian = Guardian.objects.get(user=user, tenant_id=request_tenant_id, deleted_at__isnull=True)
            else:
                guardian = Guardian.objects.filter(user=user, deleted_at__isnull=True).first()
                if not guardian:
                    raise Guardian.DoesNotExist()
        except Guardian.DoesNotExist:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = guardian.tenant_id

        # 保護者に紐づく生徒を取得
        student_ids = StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id
        ).values_list('student_id', flat=True)

        # StudentItemを取得（自分の子供のものか確認）
        try:
            student_item = StudentItem.objects.get(
                id=pk,
                student_id__in=student_ids,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except StudentItem.DoesNotExist:
            return Response(
                {'error': '指定された受講情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # StudentItemに関連するContractを取得
        contract = student_item.contract
        if not contract:
            return Response(
                {'error': 'この受講情報には契約が紐づいていないため、休会申請できません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # リクエストデータ
        suspend_from = request.data.get('suspend_from')
        suspend_until = request.data.get('suspend_until')
        keep_seat = request.data.get('keep_seat', False)
        reason = request.data.get('reason', '')

        if not suspend_from:
            return Response(
                {'error': '休会開始日は必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 既存の申請中をチェック
        existing = ContractChangeRequest.objects.filter(
            tenant_id=tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.SUSPENSION,
            status=ContractChangeRequest.Status.PENDING
        ).exists()

        if existing:
            return Response(
                {'error': 'すでに申請中の休会申請があります'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 申請を作成
        change_request = ContractChangeRequest.objects.create(
            tenant_id=tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.SUSPENSION,
            status=ContractChangeRequest.Status.PENDING,
            suspend_from=suspend_from,
            suspend_until=suspend_until if suspend_until else None,
            keep_seat=keep_seat,
            reason=reason,
            requested_by=request.user
        )

        seat_fee_message = ''
        if keep_seat:
            seat_fee_message = '座席保持料（月額800円）が発生します。'

        return Response({
            'success': True,
            'message': f'休会申請を受け付けました。{seat_fee_message}スタッフの承認後に確定します。',
            'request_id': str(change_request.id),
            'suspend_from': suspend_from,
            'suspend_until': suspend_until,
            'keep_seat': keep_seat
        })

    @action(detail=True, methods=['post'], url_path='request-cancellation', permission_classes=[IsAuthenticated])
    def request_cancellation(self, request, pk=None):
        """退会申請"""
        from apps.students.models import Guardian, StudentGuardian

        user = request.user
        request_tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得
        try:
            if request_tenant_id:
                guardian = Guardian.objects.get(user=user, tenant_id=request_tenant_id, deleted_at__isnull=True)
            else:
                guardian = Guardian.objects.filter(user=user, deleted_at__isnull=True).first()
                if not guardian:
                    raise Guardian.DoesNotExist()
        except Guardian.DoesNotExist:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        tenant_id = guardian.tenant_id

        # 保護者に紐づく生徒を取得
        student_ids = StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id
        ).values_list('student_id', flat=True)

        # StudentItemを取得（自分の子供のものか確認）
        try:
            student_item = StudentItem.objects.get(
                id=pk,
                student_id__in=student_ids,
                tenant_id=tenant_id,
                deleted_at__isnull=True
            )
        except StudentItem.DoesNotExist:
            return Response(
                {'error': '指定された受講情報が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # StudentItemに関連するContractを取得
        contract = student_item.contract
        if not contract:
            return Response(
                {'error': 'この受講情報には契約が紐づいていないため、退会申請できません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # リクエストデータ
        cancel_date = request.data.get('cancel_date')
        reason = request.data.get('reason', '').strip()

        if not cancel_date:
            return Response(
                {'error': '退会日は必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not reason:
            return Response(
                {'error': '退会理由は必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 既存の申請中をチェック
        existing = ContractChangeRequest.objects.filter(
            tenant_id=tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.CANCELLATION,
            status=ContractChangeRequest.Status.PENDING
        ).exists()

        if existing:
            return Response(
                {'error': 'すでに申請中の退会申請があります'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 相殺金額を計算（当月退会の場合）
        cancel_date_obj = datetime.strptime(cancel_date, '%Y-%m-%d').date()
        today = date.today()
        refund_amount = None

        if cancel_date_obj.year == today.year and cancel_date_obj.month == today.month:
            # 当月退会の場合、日割り計算の目安を表示
            days_in_month = 30
            remaining_days = days_in_month - cancel_date_obj.day
            monthly_fee = getattr(contract, 'monthly_fee', None) or Decimal('0')
            refund_amount = (monthly_fee / days_in_month * remaining_days).quantize(Decimal('1'))

        # 申請を作成
        change_request = ContractChangeRequest.objects.create(
            tenant_id=tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.CANCELLATION,
            status=ContractChangeRequest.Status.PENDING,
            cancel_date=cancel_date,
            refund_amount=refund_amount,
            reason=reason,
            requested_by=request.user
        )

        refund_message = ''
        if refund_amount:
            refund_message = f'相殺金額（目安）: {refund_amount:,}円'

        return Response({
            'success': True,
            'message': f'退会申請を受け付けました。{refund_message}スタッフの承認後に確定します。',
            'request_id': str(change_request.id),
            'cancel_date': cancel_date,
            'refund_amount': str(refund_amount) if refund_amount else None
        })

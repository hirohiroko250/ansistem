"""
Change Request Service - 契約変更申請サービス
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class ChangeRequestService:
    """契約変更申請サービス

    クラス変更、校舎変更、休会申請、退会申請を処理
    """

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def get_guardian_from_user(self, user, request_tenant_id=None):
        """ユーザーから保護者を取得"""
        from apps.students.models import Guardian

        if request_tenant_id:
            return Guardian.objects.get(
                user=user,
                tenant_id=request_tenant_id,
                deleted_at__isnull=True
            )
        else:
            guardian = Guardian.objects.filter(
                user=user,
                deleted_at__isnull=True
            ).first()
            if not guardian:
                raise Guardian.DoesNotExist()
            return guardian

    def get_student_item(self, item_id, guardian):
        """保護者に紐づく生徒のStudentItemを取得"""
        from apps.students.models import StudentGuardian
        from ..models import StudentItem

        student_ids = StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=guardian.tenant_id
        ).values_list('student_id', flat=True)

        return StudentItem.objects.get(
            id=item_id,
            student_id__in=student_ids,
            tenant_id=guardian.tenant_id,
            deleted_at__isnull=True
        )

    @transaction.atomic
    def change_class(
        self,
        student_item,
        new_day_of_week: int,
        new_start_time: str,
        class_schedule,
        effective_date=None
    ):
        """クラス変更を実行

        Args:
            student_item: 変更対象のStudentItem
            new_day_of_week: 新しい曜日
            new_start_time: 新しい開始時間
            class_schedule: 新しいクラススケジュール
            effective_date: 適用開始日

        Returns:
            更新されたStudentItem

        Raises:
            ValueError: 校舎が異なる場合
        """
        from apps.students.models import StudentEnrollment

        # 同じ校舎かチェック
        if class_schedule.school_id != student_item.school_id:
            raise ValueError('校舎が異なります。校舎変更は別のAPIをご利用ください')

        # 翌週の開始日を計算
        if not effective_date:
            today = timezone.now().date()
            days_until_next_week = 7 - today.weekday()
            effective_date = today + timedelta(days=days_until_next_week)
        elif isinstance(effective_date, str):
            effective_date = datetime.strptime(effective_date, '%Y-%m-%d').date()

        # StudentItemを更新
        student_item.day_of_week = new_day_of_week
        student_item.start_time = new_start_time
        if hasattr(class_schedule, 'end_time'):
            student_item.end_time = class_schedule.end_time
        student_item.save()

        # 履歴を記録
        if student_item.school and student_item.brand:
            StudentEnrollment.create_enrollment(
                student=student_item.student,
                school=student_item.school,
                brand=student_item.brand,
                class_schedule=class_schedule,
                change_type=StudentEnrollment.ChangeType.CLASS_CHANGE,
                effective_date=effective_date,
                student_item=student_item,
                notes=f'クラス変更: {class_schedule}',
            )

        logger.info(
            f"Class changed for StudentItem {student_item.id}: "
            f"day={new_day_of_week}, time={new_start_time}"
        )

        return student_item

    @transaction.atomic
    def change_school(
        self,
        student_item,
        new_school,
        new_day_of_week: int,
        new_start_time: str,
        effective_date=None
    ):
        """校舎変更を実行

        Args:
            student_item: 変更対象のStudentItem
            new_school: 新しい校舎
            new_day_of_week: 新しい曜日
            new_start_time: 新しい開始時間
            effective_date: 適用開始日

        Returns:
            更新されたStudentItem
        """
        # 翌週の開始日を計算
        if not effective_date:
            today = timezone.now().date()
            days_until_next_week = 7 - today.weekday()
            effective_date = today + timedelta(days=days_until_next_week)
        elif isinstance(effective_date, str):
            effective_date = datetime.strptime(effective_date, '%Y-%m-%d').date()

        # StudentItemを更新
        student_item.school = new_school
        student_item.day_of_week = new_day_of_week
        student_item.start_time = new_start_time
        student_item.save()

        logger.info(
            f"School changed for StudentItem {student_item.id}: "
            f"school={new_school.school_name}"
        )

        return student_item

    def create_suspension_request(
        self,
        contract,
        suspend_from: str,
        suspend_until: str = None,
        keep_seat: bool = False,
        reason: str = '',
        requested_by=None
    ):
        """休会申請を作成

        Args:
            contract: 対象契約
            suspend_from: 休会開始日
            suspend_until: 休会終了日（任意）
            keep_seat: 座席保持するか
            reason: 理由
            requested_by: 申請者

        Returns:
            作成された変更申請

        Raises:
            ValueError: 既に申請中の場合
        """
        from ..models import ContractChangeRequest

        # 既存の申請中をチェック
        existing = ContractChangeRequest.objects.filter(
            tenant_id=self.tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.SUSPENSION,
            status=ContractChangeRequest.Status.PENDING
        ).exists()

        if existing:
            raise ValueError('すでに申請中の休会申請があります')

        change_request = ContractChangeRequest.objects.create(
            tenant_id=self.tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.SUSPENSION,
            status=ContractChangeRequest.Status.PENDING,
            suspend_from=suspend_from,
            suspend_until=suspend_until if suspend_until else None,
            keep_seat=keep_seat,
            reason=reason,
            requested_by=requested_by
        )

        logger.info(f"Suspension request created: {change_request.id}")

        return change_request

    def create_cancellation_request(
        self,
        contract,
        cancel_date: str,
        reason: str = '',
        requested_by=None
    ):
        """退会申請を作成

        Args:
            contract: 対象契約
            cancel_date: 退会日
            reason: 理由
            requested_by: 申請者

        Returns:
            作成された変更申請

        Raises:
            ValueError: 既に申請中の場合
        """
        from ..models import ContractChangeRequest

        # 既存の申請中をチェック
        existing = ContractChangeRequest.objects.filter(
            tenant_id=self.tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.CANCELLATION,
            status=ContractChangeRequest.Status.PENDING
        ).exists()

        if existing:
            raise ValueError('すでに申請中の退会申請があります')

        # 相殺金額を計算（当月退会の場合）
        cancel_date_obj = datetime.strptime(cancel_date, '%Y-%m-%d').date()
        today = date.today()
        refund_amount = None

        if cancel_date_obj.year == today.year and cancel_date_obj.month == today.month:
            # 当月退会の場合、日割り計算の目安
            days_in_month = 30
            remaining_days = days_in_month - cancel_date_obj.day
            monthly_fee = getattr(contract, 'monthly_fee', None) or Decimal('0')
            refund_amount = (monthly_fee / days_in_month * remaining_days).quantize(Decimal('1'))

        change_request = ContractChangeRequest.objects.create(
            tenant_id=self.tenant_id,
            contract=contract,
            request_type=ContractChangeRequest.RequestType.CANCELLATION,
            status=ContractChangeRequest.Status.PENDING,
            cancel_date=cancel_date,
            refund_amount=refund_amount,
            reason=reason,
            requested_by=requested_by
        )

        logger.info(f"Cancellation request created: {change_request.id}")

        return change_request

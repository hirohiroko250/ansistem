"""
Request Service - 休会・退会申請処理サービス
"""
from decimal import Decimal
from calendar import monthrange
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class SuspensionService:
    """休会申請処理サービス"""

    SUSPENSION_FEE = Decimal('800')  # 座席保持の休会費

    def __init__(self, suspension_request):
        self.request = suspension_request
        self.tenant_id = suspension_request.tenant_id

    @transaction.atomic
    def approve(self, processed_by) -> bool:
        """休会申請を承認

        Args:
            processed_by: 承認者（User）

        Returns:
            成功した場合 True

        Raises:
            ValueError: 申請が承認可能な状態でない場合
        """
        if self.request.status != 'pending':
            raise ValueError('申請中のもののみ承認できます')

        # 休会日を月末に設定
        suspend_date = self._get_month_end(self.request.suspend_from)
        self.request.suspend_from = suspend_date

        # 生徒のステータスを休会中に変更
        student = self.request.student
        student.status = 'suspended'
        student.suspended_date = suspend_date
        student.save()

        # 座席保持の場合は休会費を追加
        if self.request.keep_seat:
            self._create_suspension_fee(student, suspend_date)
            self.request.monthly_fee_during_suspension = self.SUSPENSION_FEE

        # 申請ステータス更新
        self.request.status = 'approved'
        self.request.processed_by = processed_by
        self.request.processed_at = timezone.now()
        self.request.save()

        logger.info(
            f"Suspension approved: student={student.id}, "
            f"from={suspend_date}"
        )

        return True

    def reject(self, processed_by, reason: str = '') -> bool:
        """休会申請を却下"""
        if self.request.status != 'pending':
            raise ValueError('申請中のもののみ却下できます')

        self.request.status = 'rejected'
        self.request.processed_by = processed_by
        self.request.processed_at = timezone.now()
        self.request.rejection_reason = reason
        self.request.save()

        logger.info(f"Suspension rejected: request={self.request.id}")

        return True

    def cancel(self) -> bool:
        """休会申請をキャンセル"""
        if self.request.status != 'pending':
            raise ValueError('申請中のもののみキャンセルできます')

        self.request.status = 'cancelled'
        self.request.save()

        logger.info(f"Suspension cancelled: request={self.request.id}")

        return True

    @transaction.atomic
    def resume(self) -> bool:
        """休会から復会

        Returns:
            成功した場合 True

        Raises:
            ValueError: 承認済みの休会でない場合
        """
        if self.request.status != 'approved':
            raise ValueError('承認済みの休会のみ復会できます')

        # 生徒のステータスを在籍中に戻す
        student = self.request.student
        student.status = 'enrolled'
        student.save()

        # 申請ステータス更新
        self.request.status = 'resumed'
        self.request.suspend_until = timezone.now().date()
        self.request.save()

        logger.info(f"Suspension resumed: student={student.id}")

        return True

    def _get_month_end(self, date):
        """月末日を取得"""
        last_day = monthrange(date.year, date.month)[1]
        return date.replace(day=last_day)

    def _create_suspension_fee(self, student, suspend_date):
        """休会費のStudentItemを作成"""
        from apps.contracts.models import StudentItem, Product

        # 休会費用の商品を取得または作成
        suspension_product, _ = Product.objects.get_or_create(
            product_code='SUSPENSION_FEE',
            defaults={
                'tenant_id': self.tenant_id,
                'product_name': '休会費',
                'item_type': 'other',
                'base_price': self.SUSPENSION_FEE,
                'is_recurring': True,
            }
        )

        # 休会費のStudentItemを作成
        StudentItem.objects.create(
            tenant_id=self.tenant_id,
            student=student,
            product=suspension_product,
            brand=self.request.brand,
            school=self.request.school,
            billing_month=suspend_date.strftime('%Y-%m'),
            quantity=1,
            unit_price=self.SUSPENSION_FEE,
            discount_amount=Decimal('0'),
            final_price=self.SUSPENSION_FEE,
            notes=f'休会費（{suspend_date}〜）',
        )


class WithdrawalService:
    """退会申請処理サービス"""

    def __init__(self, withdrawal_request):
        self.request = withdrawal_request
        self.tenant_id = withdrawal_request.tenant_id

    @transaction.atomic
    def approve(self, processed_by) -> bool:
        """退会申請を承認

        Args:
            processed_by: 承認者（User）

        Returns:
            成功した場合 True

        Raises:
            ValueError: 申請が承認可能な状態でない場合
        """
        from ..models import StudentSchool, StudentEnrollment

        if self.request.status != 'pending':
            raise ValueError('申請中のもののみ承認できます')

        # 退会日を月末に設定
        withdrawal_date = self._get_month_end(self.request.withdrawal_date)
        self.request.withdrawal_date = withdrawal_date

        student = self.request.student

        # 生徒のステータスを退会に変更
        student.status = 'withdrawn'
        student.withdrawal_date = withdrawal_date
        student.withdrawal_reason = (
            self.request.reason_detail or
            self.request.get_reason_display()
        )
        student.save()

        # StudentSchoolの終了日を設定
        StudentSchool.objects.filter(
            student=student,
            brand=self.request.brand,
            school=self.request.school,
            deleted_at__isnull=True,
            end_date__isnull=True
        ).update(end_date=withdrawal_date)

        # StudentEnrollmentも終了
        StudentEnrollment.objects.filter(
            student=student,
            brand=self.request.brand,
            school=self.request.school,
            deleted_at__isnull=True,
            end_date__isnull=True
        ).update(
            end_date=withdrawal_date,
            status='withdrawn',
            change_type='withdraw'
        )

        # 申請ステータス更新
        self.request.status = 'approved'
        self.request.processed_by = processed_by
        self.request.processed_at = timezone.now()
        self.request.save()

        logger.info(
            f"Withdrawal approved: student={student.id}, "
            f"date={withdrawal_date}"
        )

        return True

    def reject(self, processed_by, reason: str = '') -> bool:
        """退会申請を却下"""
        if self.request.status != 'pending':
            raise ValueError('申請中のもののみ却下できます')

        self.request.status = 'rejected'
        self.request.processed_by = processed_by
        self.request.processed_at = timezone.now()
        self.request.rejection_reason = reason
        self.request.save()

        logger.info(f"Withdrawal rejected: request={self.request.id}")

        return True

    def cancel(self) -> bool:
        """退会申請をキャンセル"""
        if self.request.status != 'pending':
            raise ValueError('申請中のもののみキャンセルできます')

        self.request.status = 'cancelled'
        self.request.save()

        logger.info(f"Withdrawal cancelled: request={self.request.id}")

        return True

    def _get_month_end(self, date):
        """月末日を取得"""
        last_day = monthrange(date.year, date.month)[1]
        return date.replace(day=last_day)

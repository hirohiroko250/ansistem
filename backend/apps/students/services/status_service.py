"""
Student Status Service - 生徒ステータス遷移サービス
"""
from django.utils import timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class StudentStatusService:
    """生徒ステータス遷移サービス

    生徒のステータス遷移ロジックを一元管理:
    - 登録 → 体験 → 入会 → 休会 → 退会
    """

    # ステータス定義
    STATUS_LEAD = 'lead'           # リード（問い合わせ）
    STATUS_TRIAL = 'trial'         # 体験中
    STATUS_ENROLLED = 'enrolled'   # 在籍中
    STATUS_SUSPENDED = 'suspended' # 休会中
    STATUS_WITHDRAWN = 'withdrawn' # 退会済み

    # 許可される遷移
    ALLOWED_TRANSITIONS = {
        STATUS_LEAD: [STATUS_TRIAL, STATUS_ENROLLED, STATUS_WITHDRAWN],
        STATUS_TRIAL: [STATUS_ENROLLED, STATUS_WITHDRAWN],
        STATUS_ENROLLED: [STATUS_SUSPENDED, STATUS_WITHDRAWN],
        STATUS_SUSPENDED: [STATUS_ENROLLED, STATUS_WITHDRAWN],
        STATUS_WITHDRAWN: [],  # 退会後は遷移不可
    }

    def __init__(self, student):
        self.student = student

    def can_transition_to(self, new_status: str) -> bool:
        """指定ステータスへの遷移が可能かチェック"""
        current = self.student.status
        allowed = self.ALLOWED_TRANSITIONS.get(current, [])
        return new_status in allowed

    def transition_to(self, new_status: str, **kwargs) -> bool:
        """ステータスを遷移させる

        Args:
            new_status: 新しいステータス
            **kwargs: 遷移に必要な追加データ
                - suspended_date: 休会開始日
                - withdrawal_date: 退会日
                - withdrawal_reason: 退会理由

        Returns:
            成功した場合 True

        Raises:
            ValueError: 許可されていない遷移の場合
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"ステータス遷移が許可されていません: "
                f"{self.student.status} → {new_status}"
            )

        old_status = self.student.status
        self.student.status = new_status

        # ステータス固有の処理
        if new_status == self.STATUS_SUSPENDED:
            self._handle_suspension(**kwargs)
        elif new_status == self.STATUS_ENROLLED and old_status == self.STATUS_SUSPENDED:
            self._handle_resume(**kwargs)
        elif new_status == self.STATUS_WITHDRAWN:
            self._handle_withdrawal(**kwargs)

        self.student.save()

        logger.info(
            f"Student {self.student.id} status changed: "
            f"{old_status} → {new_status}"
        )

        return True

    def _handle_suspension(self, **kwargs):
        """休会処理"""
        suspended_date = kwargs.get('suspended_date', timezone.now().date())
        self.student.suspended_date = suspended_date

    def _handle_resume(self, **kwargs):
        """復会処理"""
        self.student.suspended_date = None

    def _handle_withdrawal(self, **kwargs):
        """退会処理"""
        withdrawal_date = kwargs.get('withdrawal_date', timezone.now().date())
        withdrawal_reason = kwargs.get('withdrawal_reason', '')

        self.student.withdrawal_date = withdrawal_date
        self.student.withdrawal_reason = withdrawal_reason

    def enroll(self) -> bool:
        """入会処理"""
        return self.transition_to(self.STATUS_ENROLLED)

    def suspend(self, suspended_date=None) -> bool:
        """休会処理"""
        return self.transition_to(
            self.STATUS_SUSPENDED,
            suspended_date=suspended_date or timezone.now().date()
        )

    def resume(self) -> bool:
        """復会処理"""
        return self.transition_to(self.STATUS_ENROLLED)

    def withdraw(self, withdrawal_date=None, withdrawal_reason='') -> bool:
        """退会処理"""
        return self.transition_to(
            self.STATUS_WITHDRAWN,
            withdrawal_date=withdrawal_date or timezone.now().date(),
            withdrawal_reason=withdrawal_reason
        )

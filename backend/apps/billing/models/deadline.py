"""
Deadline Models - 月次請求締切管理
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class MonthlyBillingDeadline(TenantModel):
    """月次請求締切管理

    内部的な締日管理。決済代行会社とは別に、各月の請求データを締める。
    締日を過ぎると、その月の請求データは編集・削除・割引追加が不可になる。

    例:
    - 12月分請求の締日が25日の場合、12/26以降は12月分の請求データは編集不可
    - 編集不可になる項目: 料金変更、削除、割引追加、コース変更など
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 対象期間
    year = models.IntegerField('対象年')
    month = models.IntegerField('対象月')

    # 締日設定
    closing_day = models.IntegerField(
        '締日',
        default=25,
        help_text='毎月この日を過ぎると、当月分の請求は編集不可になる'
    )

    # 自動締め（締日を過ぎたら自動的にロック）
    auto_close = models.BooleanField(
        '自動締め',
        default=True,
        help_text='締日を過ぎたら自動的にロック状態にする'
    )

    # 手動締め状態
    is_manually_closed = models.BooleanField(
        '手動締め済み',
        default=False,
        help_text='締日前でも手動で締めることが可能'
    )
    manually_closed_at = models.DateTimeField('手動締め日時', null=True, blank=True)
    manually_closed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='manually_closed_deadlines',
        verbose_name='手動締め実行者'
    )

    # 締め解除（特別な場合のみ）
    is_reopened = models.BooleanField('締め解除済み', default=False)
    reopened_at = models.DateTimeField('締め解除日時', null=True, blank=True)
    reopened_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reopened_deadlines',
        verbose_name='締め解除実行者'
    )
    reopen_reason = models.TextField('締め解除理由', blank=True)

    # 確認中状態（経理確認中）
    is_under_review = models.BooleanField(
        '確認中',
        default=False,
        help_text='経理が確認中。経理以外は編集不可'
    )
    under_review_at = models.DateTimeField('確認開始日時', null=True, blank=True)
    under_review_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='review_started_deadlines',
        verbose_name='確認開始者'
    )

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'billing_monthly_deadlines'
        verbose_name = '月次請求締切'
        verbose_name_plural = '月次請求締切'
        ordering = ['-year', '-month']
        unique_together = ['tenant_id', 'year', 'month']

    def __str__(self):
        return f"{self.year}年{self.month:02d}月分請求 ({self.status_display})"

    @property
    def status(self) -> str:
        """ステータスを取得: open, under_review, closed"""
        if self.is_closed:
            return 'closed'
        if self.is_under_review:
            return 'under_review'
        return 'open'

    @property
    def status_display(self) -> str:
        """ステータス表示名"""
        status_map = {
            'open': '未締',
            'under_review': '確認中',
            'closed': '締済',
        }
        return status_map.get(self.status, '未締')

    @property
    def is_closed(self) -> bool:
        """締め状態を判定

        以下のいずれかの場合に締め済みとなる:
        1. 手動で締められた（is_manually_closed=True）
        2. 自動締めが有効で、締日を過ぎている
        3. ただし、締め解除されている場合は未締め扱い
        """
        if self.is_reopened:
            return False

        if self.is_manually_closed:
            return True

        if self.auto_close:
            from datetime import date
            today = date.today()
            try:
                closing_date = date(self.year, self.month, self.closing_day)
            except ValueError:
                # 締日が月末を超える場合は月末日
                import calendar
                last_day = calendar.monthrange(self.year, self.month)[1]
                closing_date = date(self.year, self.month, last_day)

            return today > closing_date

        return False

    @property
    def closing_date(self):
        """実際の締日を取得"""
        from datetime import date
        import calendar
        try:
            return date(self.year, self.month, self.closing_day)
        except ValueError:
            last_day = calendar.monthrange(self.year, self.month)[1]
            return date(self.year, self.month, last_day)

    @property
    def can_edit(self) -> bool:
        """編集可能かどうか（確定済みは編集不可）"""
        return not self.is_closed

    def can_edit_by_user(self, user) -> bool:
        """ユーザーが編集可能かどうか

        - 確定済み: 誰も編集不可
        - 確認中: 経理・管理者のみ編集可
        - 未締め: 誰でも編集可
        """
        if self.is_closed:
            return False
        if self.is_under_review:
            # 経理・管理者権限チェック
            from apps.users.models import User
            allowed_roles = [
                User.Role.ACCOUNTING,
                User.Role.ADMIN,
                User.Role.SUPER_ADMIN,
            ]
            return hasattr(user, 'role') and user.role in allowed_roles
        return True

    def start_review(self, user):
        """確認中にする"""
        self.is_under_review = True
        self.under_review_at = timezone.now()
        self.under_review_by = user
        # 締め解除状態をクリア
        self.is_reopened = False
        self.reopened_at = None
        self.reopened_by = None
        self.reopen_reason = ''
        self.save()

    def cancel_review(self, user):
        """確認中を解除して通常状態に戻す"""
        self.is_under_review = False
        self.under_review_at = None
        self.under_review_by = None
        self.save()

    def close_manually(self, user, notes: str = ''):
        """手動で締める（確定）"""
        self.is_manually_closed = True
        self.manually_closed_at = timezone.now()
        self.manually_closed_by = user
        # 確認中状態をクリア
        self.is_under_review = False
        self.under_review_at = None
        self.under_review_by = None
        # 締め解除状態をクリア
        self.is_reopened = False
        self.reopened_at = None
        self.reopened_by = None
        if notes:
            self.notes = notes
        self.save()

    def reopen(self, user, reason: str):
        """締め解除（要理由）"""
        self.is_reopened = True
        self.reopened_at = timezone.now()
        self.reopened_by = user
        self.reopen_reason = reason
        self.save()

    @classmethod
    def get_or_create_for_month(cls, tenant_id: int, year: int, month: int, closing_day: int = 25):
        """指定月の締切レコードを取得または作成"""
        deadline, created = cls.objects.get_or_create(
            tenant_id=tenant_id,
            year=year,
            month=month,
            defaults={
                'closing_day': closing_day,
                'auto_close': True,
            }
        )
        return deadline, created

    @classmethod
    def is_month_editable(cls, tenant_id: int, year: int, month: int) -> bool:
        """指定月が編集可能かどうかをチェック"""
        try:
            deadline = cls.objects.get(
                tenant_id=tenant_id,
                year=year,
                month=month
            )
            return deadline.can_edit
        except cls.DoesNotExist:
            # レコードがない場合は編集可能（まだ締切管理されていない）
            return True

    @classmethod
    def get_billing_month_for_date(cls, target_date, closing_day: int = 10) -> tuple:
        """日付から請求月を計算

        締め日ロジック:
        - 締め日を過ぎた日付は翌月請求
        - 例: 締め日=10の場合、12/11〜1/10 → 1月請求、1/11〜2/10 → 2月請求

        Args:
            target_date: 対象日付
            closing_day: 締め日（デフォルト10日）

        Returns:
            tuple: (year, month) 請求月
        """
        from dateutil.relativedelta import relativedelta

        if isinstance(target_date, str):
            from datetime import datetime
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

        if target_date.day > closing_day:
            # 締め日を過ぎている場合は翌月請求
            next_month = target_date.replace(day=1) + relativedelta(months=1)
            return (next_month.year, next_month.month)
        else:
            # 締め日以内の場合は当月請求
            return (target_date.year, target_date.month)

    @classmethod
    def get_current_billing_period(cls, tenant_id: int, closing_day: int = 10) -> tuple:
        """現在の編集可能な請求期間を取得

        Returns:
            tuple: (year, month) 現在の請求期間
        """
        from datetime import date
        today = date.today()
        return cls.get_billing_month_for_date(today, closing_day)

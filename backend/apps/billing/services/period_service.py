"""
Billing Period Service
請求期間/締日管理サービス

締日管理、締め処理、請求書の編集可否チェックなどを行う。
"""
from datetime import date, timedelta
from typing import Optional, Tuple

from django.db import transaction
from django.utils import timezone

from apps.billing.models import (
    Invoice, PaymentProvider, BillingPeriod
)


class BillingPeriodService:
    """請求期間/締日管理サービス"""

    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id

    def get_or_create_period(
        self,
        provider: PaymentProvider,
        year: int,
        month: int
    ) -> Tuple[BillingPeriod, bool]:
        """請求期間を取得または作成

        Args:
            provider: 決済代行会社
            year: 対象年
            month: 対象月

        Returns:
            (BillingPeriod, created) のタプル
        """
        # 締日を計算
        closing_date = self._calculate_closing_date(provider, year, month)

        return BillingPeriod.objects.get_or_create(
            tenant_id=self.tenant_id,
            provider=provider,
            year=year,
            month=month,
            defaults={
                'closing_date': closing_date,
            }
        )

    def _calculate_closing_date(
        self,
        provider: PaymentProvider,
        year: int,
        month: int
    ) -> date:
        """締日を計算

        月末の場合や日付が存在しない場合（2月30日など）は
        その月の最終日に調整する。
        """
        closing_day = provider.closing_day

        # 翌月の1日から1日戻すと前月の末日が取れる
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)

        last_day_of_month = (next_month - timedelta(days=1)).day

        # 締日が月末を超える場合は月末に調整
        actual_day = min(closing_day, last_day_of_month)

        return date(year, month, actual_day)

    def close_period(self, period: BillingPeriod, user) -> bool:
        """締め処理を実行

        Args:
            period: 請求期間
            user: 実行ユーザー

        Returns:
            成功したかどうか
        """
        if period.is_closed:
            return False

        period.close(user)
        return True

    def reopen_period(self, period: BillingPeriod) -> bool:
        """締め解除

        Args:
            period: 請求期間

        Returns:
            成功したかどうか
        """
        if not period.is_closed:
            return False

        period.reopen()
        return True

    def is_period_closed(
        self,
        provider: PaymentProvider,
        year: int,
        month: int
    ) -> bool:
        """期間が締められているか確認

        Args:
            provider: 決済代行会社
            year: 対象年
            month: 対象月

        Returns:
            締められていればTrue
        """
        try:
            period = BillingPeriod.objects.get(
                tenant_id=self.tenant_id,
                provider=provider,
                year=year,
                month=month,
            )
            return period.is_closed
        except BillingPeriod.DoesNotExist:
            return False

    def can_edit_invoice(self, invoice: Invoice) -> bool:
        """請求書が編集可能か確認

        関連する全ての決済代行会社の請求期間が締められていないか確認する。

        Args:
            invoice: 請求書

        Returns:
            編集可能ならTrue
        """
        # アクティブな決済代行会社の請求期間をチェック
        providers = PaymentProvider.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True,
        )

        for provider in providers:
            if self.is_period_closed(
                provider,
                invoice.billing_year,
                invoice.billing_month
            ):
                return False

        return True

    def get_editable_status(self, invoice: Invoice) -> dict:
        """請求書の編集可否ステータスを取得

        Args:
            invoice: 請求書

        Returns:
            ステータス情報の辞書
        """
        providers = PaymentProvider.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True,
        )

        closed_providers = []
        for provider in providers:
            if self.is_period_closed(
                provider,
                invoice.billing_year,
                invoice.billing_month
            ):
                closed_providers.append(provider.name)

        return {
            'can_edit': len(closed_providers) == 0,
            'closed_providers': closed_providers,
            'message': (
                f'{", ".join(closed_providers)} で締められています'
                if closed_providers
                else '編集可能です'
            ),
        }

    def get_next_closing_date(self, provider: PaymentProvider) -> date:
        """次の締日を取得

        Args:
            provider: 決済代行会社

        Returns:
            次の締日
        """
        today = timezone.now().date()
        year = today.year
        month = today.month

        closing_date = self._calculate_closing_date(provider, year, month)

        # 今月の締日が過ぎていれば翌月
        if today > closing_date:
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
            closing_date = self._calculate_closing_date(provider, year, month)

        return closing_date

    def get_current_period(
        self,
        provider: PaymentProvider
    ) -> Optional[BillingPeriod]:
        """現在の請求期間を取得

        Args:
            provider: 決済代行会社

        Returns:
            現在の請求期間（存在しない場合はNone）
        """
        today = timezone.now().date()

        return BillingPeriod.objects.filter(
            tenant_id=self.tenant_id,
            provider=provider,
            year=today.year,
            month=today.month,
        ).first()

    def create_periods_for_month(self, year: int, month: int) -> int:
        """指定月の全決済代行会社の請求期間を作成

        Args:
            year: 対象年
            month: 対象月

        Returns:
            作成された期間の数
        """
        providers = PaymentProvider.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True,
        )

        created_count = 0
        for provider in providers:
            _, created = self.get_or_create_period(provider, year, month)
            if created:
                created_count += 1

        return created_count

    def get_billing_month_for_new_charge(
        self,
        charge_date: Optional[date] = None,
        provider: Optional[PaymentProvider] = None
    ) -> Tuple[int, int]:
        """新規料金の請求月を判定

        締日以前なら当月、締日以降なら翌月の請求になる。

        Args:
            charge_date: 料金発生日（デフォルト: 今日）
            provider: 決済代行会社（デフォルト: アクティブな最初のプロバイダー）

        Returns:
            (year, month) のタプル - 請求対象の年月

        Example:
            締日が15日の場合:
            - 12/10に入会 → 12月分から請求
            - 12/16に入会 → 1月分から請求（12月分は確定済み）
        """
        if charge_date is None:
            charge_date = timezone.now().date()

        if provider is None:
            provider = PaymentProvider.objects.filter(
                tenant_id=self.tenant_id,
                is_active=True,
            ).first()

        if provider is None:
            # プロバイダーがない場合はデフォルトで当月
            return charge_date.year, charge_date.month

        closing_day = provider.closing_day
        year = charge_date.year
        month = charge_date.month

        # 今月の締日を計算
        closing_date = self._calculate_closing_date(provider, year, month)

        # 締日を過ぎていたら翌月から請求
        if charge_date > closing_date:
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1

        return year, month

    def get_billing_info_for_new_enrollment(
        self,
        enrollment_date: Optional[date] = None,
        provider: Optional[PaymentProvider] = None
    ) -> dict:
        """新規入会時の請求情報を取得

        入会時に「今月分」「翌月分」「翌々月分」がどうなるかを返す。

        Args:
            enrollment_date: 入会日（デフォルト: 今日）
            provider: 決済代行会社

        Returns:
            請求情報の辞書

        Example:
            締日が15日で12/16に入会した場合:
            {
                'enrollment_date': '2024-12-16',
                'closing_day': 15,
                'is_after_closing': True,
                'current_month': {'year': 2024, 'month': 12, 'editable': False, 'note': '締日超過のため確定済み'},
                'next_month': {'year': 2025, 'month': 1, 'editable': False, 'note': '確定済み'},
                'following_month': {'year': 2025, 'month': 2, 'editable': True, 'note': '編集可能'},
                'first_billable_month': {'year': 2025, 'month': 2},
                'message': '12月分・1月分は確定済みです。2月分から料金を調整できます。'
            }
        """
        if enrollment_date is None:
            enrollment_date = timezone.now().date()

        if provider is None:
            provider = PaymentProvider.objects.filter(
                tenant_id=self.tenant_id,
                is_active=True,
            ).first()

        current_year = enrollment_date.year
        current_month = enrollment_date.month

        result = {
            'enrollment_date': enrollment_date.isoformat(),
            'closing_day': provider.closing_day if provider else 25,
            'is_after_closing': False,
            'current_month': None,
            'next_month': None,
            'following_month': None,
            'first_billable_month': None,
            'message': '',
        }

        if provider is None:
            result['message'] = '決済代行会社が設定されていません'
            result['first_billable_month'] = {'year': current_year, 'month': current_month}
            return result

        # 今月の締日
        closing_date = self._calculate_closing_date(provider, current_year, current_month)
        is_after_closing = enrollment_date > closing_date
        result['is_after_closing'] = is_after_closing

        # 各月の情報を設定
        def get_next_month(y, m):
            if m == 12:
                return y + 1, 1
            return y, m + 1

        # 当月
        result['current_month'] = {
            'year': current_year,
            'month': current_month,
            'editable': not is_after_closing and not self.is_period_closed(provider, current_year, current_month),
            'note': '締日超過のため確定済み' if is_after_closing else ('確定済み' if self.is_period_closed(provider, current_year, current_month) else '編集可能'),
        }

        # 翌月
        next_year, next_month = get_next_month(current_year, current_month)
        # 締日超過の場合、翌月も確定済みとみなす（引落日までの準備期間）
        next_editable = not is_after_closing and not self.is_period_closed(provider, next_year, next_month)
        result['next_month'] = {
            'year': next_year,
            'month': next_month,
            'editable': next_editable,
            'note': '確定済み' if not next_editable else '編集可能',
        }

        # 翌々月
        following_year, following_month = get_next_month(next_year, next_month)
        following_editable = not self.is_period_closed(provider, following_year, following_month)
        result['following_month'] = {
            'year': following_year,
            'month': following_month,
            'editable': following_editable,
            'note': '確定済み' if not following_editable else '編集可能',
        }

        # 最初に編集可能な月
        if result['current_month']['editable']:
            result['first_billable_month'] = {'year': current_year, 'month': current_month}
        elif result['next_month']['editable']:
            result['first_billable_month'] = {'year': next_year, 'month': next_month}
        else:
            result['first_billable_month'] = {'year': following_year, 'month': following_month}

        # メッセージ生成
        if is_after_closing:
            result['message'] = f'{current_month}月分・{next_month}月分は確定済みです。{following_month}月分から料金を調整できます。'
        elif not result['current_month']['editable']:
            result['message'] = f'{current_month}月分は確定済みです。{next_month}月分から料金を調整できます。'
        else:
            result['message'] = f'{current_month}月分から料金を調整できます。'

        return result

    def get_ticket_billing_month(
        self,
        purchase_date: Optional[date] = None,
        provider: Optional[PaymentProvider] = None
    ) -> dict:
        """チケット購入時の請求月を判定

        Args:
            purchase_date: 購入日（デフォルト: 今日）
            provider: 決済代行会社

        Returns:
            請求情報の辞書
        """
        if purchase_date is None:
            purchase_date = timezone.now().date()

        billing_year, billing_month = self.get_billing_month_for_new_charge(
            charge_date=purchase_date,
            provider=provider
        )

        if provider is None:
            provider = PaymentProvider.objects.filter(
                tenant_id=self.tenant_id,
                is_active=True,
            ).first()

        current_month = purchase_date.month
        closing_date = None
        is_after_closing = False

        if provider:
            closing_date = self._calculate_closing_date(provider, purchase_date.year, purchase_date.month)
            is_after_closing = purchase_date > closing_date

        return {
            'purchase_date': purchase_date.isoformat(),
            'billing_year': billing_year,
            'billing_month': billing_month,
            'closing_day': provider.closing_day if provider else None,
            'closing_date': closing_date.isoformat() if closing_date else None,
            'is_after_closing': is_after_closing,
            'message': (
                f'締日（{closing_date.day}日）を過ぎているため、{billing_month}月分として請求されます。'
                if is_after_closing
                else f'{billing_month}月分として請求されます。'
            ),
        }

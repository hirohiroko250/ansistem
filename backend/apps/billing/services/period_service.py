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

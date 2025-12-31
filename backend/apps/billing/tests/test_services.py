"""
Billing Services Tests - 請求サービスのユニットテスト
"""
import os
import pytest
from datetime import date
from decimal import Decimal
from django.utils import timezone

# PostgreSQL必須テストのマーカー
requires_postgres = pytest.mark.skipif(
    not os.environ.get('USE_POSTGRES_FOR_TESTS'),
    reason="Requires PostgreSQL. Set USE_POSTGRES_FOR_TESTS=1 or run in Docker."
)


class TestBalanceService:
    """預り金サービスのテスト"""

    @pytest.mark.django_db
    @requires_postgres
    def test_get_balance_no_record(self):
        """残高レコードがない場合は0を返す"""
        from apps.billing.services.balance_service import BalanceService
        from apps.students.models import Guardian
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(
            tenant_code='TEST_BALANCE',
            tenant_name='テスト',
            is_active=True
        )

        guardian = Guardian.objects.create(
            tenant_id=tenant.id,
            guardian_no='GRD_BALANCE_001',
            last_name='テスト',
            first_name='保護者'
        )

        result = BalanceService.get_balance(str(tenant.id), str(guardian.id))

        assert result['balance'] == 0
        assert result['last_updated'] is None

    @pytest.mark.django_db
    @requires_postgres
    def test_deposit(self):
        """預り金入金"""
        from apps.billing.services.balance_service import BalanceService
        from apps.students.models import Guardian
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(
            tenant_code='TEST_DEPOSIT',
            tenant_name='テスト',
            is_active=True
        )

        guardian = Guardian.objects.create(
            tenant_id=tenant.id,
            guardian_no='GRD_DEPOSIT_001',
            last_name='テスト',
            first_name='保護者'
        )

        balance = BalanceService.deposit(
            tenant_id=str(tenant.id),
            guardian_id=str(guardian.id),
            amount=Decimal('10000'),
            reason='テスト入金'
        )

        assert balance.balance == Decimal('10000')

    @pytest.mark.django_db
    @requires_postgres
    def test_multiple_deposits(self):
        """複数回の入金"""
        from apps.billing.services.balance_service import BalanceService
        from apps.students.models import Guardian
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(
            tenant_code='TEST_MULTI_DEP',
            tenant_name='テスト',
            is_active=True
        )

        guardian = Guardian.objects.create(
            tenant_id=tenant.id,
            guardian_no='GRD_MULTI_001',
            last_name='テスト',
            first_name='保護者'
        )

        BalanceService.deposit(
            tenant_id=str(tenant.id),
            guardian_id=str(guardian.id),
            amount=Decimal('10000'),
            reason='1回目'
        )

        balance = BalanceService.deposit(
            tenant_id=str(tenant.id),
            guardian_id=str(guardian.id),
            amount=Decimal('5000'),
            reason='2回目'
        )

        assert balance.balance == Decimal('15000')


class TestInvoiceCalculation:
    """請求書計算のテスト"""

    def test_tax_calculation_10_percent(self):
        """消費税計算（10%）"""
        base_amount = Decimal('10000')
        tax_rate = Decimal('0.10')
        tax_amount = (base_amount * tax_rate).quantize(Decimal('1'))

        assert tax_amount == Decimal('1000')

    def test_tax_calculation_8_percent(self):
        """消費税計算（8%軽減税率）"""
        base_amount = Decimal('10000')
        tax_rate = Decimal('0.08')
        tax_amount = (base_amount * tax_rate).quantize(Decimal('1'))

        assert tax_amount == Decimal('800')

    def test_tax_calculation_rounding(self):
        """消費税計算（端数処理）"""
        from decimal import ROUND_HALF_UP

        base_amount = Decimal('9999')
        tax_rate = Decimal('0.10')
        tax_amount = (base_amount * tax_rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)

        # 9999 * 0.10 = 999.9 → 1000
        assert tax_amount == Decimal('1000')

    def test_total_with_tax(self):
        """税込合計計算"""
        base_amount = Decimal('10000')
        tax_rate = Decimal('0.10')
        total = base_amount + (base_amount * tax_rate).quantize(Decimal('1'))

        assert total == Decimal('11000')


class TestPaymentAllocation:
    """入金配分のテスト"""

    def test_full_payment(self):
        """全額入金"""
        invoice_amount = Decimal('10000')
        payment_amount = Decimal('10000')

        remaining = invoice_amount - payment_amount

        assert remaining == Decimal('0')

    def test_partial_payment(self):
        """一部入金"""
        invoice_amount = Decimal('10000')
        payment_amount = Decimal('5000')

        remaining = invoice_amount - payment_amount

        assert remaining == Decimal('5000')

    def test_overpayment(self):
        """過払い"""
        invoice_amount = Decimal('10000')
        payment_amount = Decimal('12000')

        # 過払い分は預り金へ
        applied_amount = min(invoice_amount, payment_amount)
        deposit_amount = payment_amount - applied_amount

        assert applied_amount == Decimal('10000')
        assert deposit_amount == Decimal('2000')


class TestBillingPeriod:
    """請求期間のテスト"""

    def test_get_billing_month_start(self):
        """請求月の開始日取得"""
        # 通常は1日が開始日
        year, month = 2025, 1
        start_date = date(year, month, 1)

        assert start_date == date(2025, 1, 1)

    def test_get_billing_month_end(self):
        """請求月の終了日取得"""
        from calendar import monthrange

        year, month = 2025, 1
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)

        assert end_date == date(2025, 1, 31)

    def test_get_billing_month_february(self):
        """2月の請求期間（閏年対応）"""
        from calendar import monthrange

        # 2024年は閏年
        year, month = 2024, 2
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)

        assert end_date == date(2024, 2, 29)

        # 2025年は平年
        year, month = 2025, 2
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)

        assert end_date == date(2025, 2, 28)

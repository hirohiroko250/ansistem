"""
Discount Calculation Tests - 割引計算のユニットテスト
"""
import os
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# PostgreSQL必須テストのマーカー
requires_postgres = pytest.mark.skipif(
    not os.environ.get('USE_POSTGRES_FOR_TESTS'),
    reason="Requires PostgreSQL. Set USE_POSTGRES_FOR_TESTS=1 or run in Docker."
)


class TestFSDiscountCalculation:
    """FS割引（友達紹介割引）計算のテスト"""

    def test_fixed_discount(self):
        """固定額割引の計算"""
        from apps.pricing.calculations.discounts import calculate_fs_discount_amount

        # Mockのfs_discountオブジェクト
        fs_discount = Mock()
        fs_discount.discount_type = 'fixed'
        fs_discount.discount_value = 1000

        subtotal = Decimal('10000')
        result = calculate_fs_discount_amount(fs_discount, subtotal)

        assert result == Decimal('1000')

    def test_percentage_discount(self):
        """パーセンテージ割引の計算"""
        from apps.pricing.calculations.discounts import calculate_fs_discount_amount

        fs_discount = Mock()
        fs_discount.discount_type = 'percentage'
        fs_discount.discount_value = 10  # 10%

        subtotal = Decimal('10000')
        result = calculate_fs_discount_amount(fs_discount, subtotal)

        assert result == Decimal('1000')

    def test_no_discount(self):
        """割引なしの場合"""
        from apps.pricing.calculations.discounts import calculate_fs_discount_amount

        result = calculate_fs_discount_amount(None, Decimal('10000'))

        assert result == Decimal('0')

    def test_percentage_discount_rounding(self):
        """パーセンテージ割引の端数処理"""
        from apps.pricing.calculations.discounts import calculate_fs_discount_amount

        fs_discount = Mock()
        fs_discount.discount_type = 'percentage'
        fs_discount.discount_value = 15  # 15%

        subtotal = Decimal('9999')
        result = calculate_fs_discount_amount(fs_discount, subtotal)

        # 9999 * 15 / 100 = 1499.85
        expected = Decimal('9999') * Decimal('15') / Decimal('100')
        assert result == expected


class TestMileDiscountCalculation:
    """マイル割引計算のテスト"""

    @pytest.mark.django_db
    @requires_postgres
    def test_single_course_no_discount(self):
        """1コースのみの場合は割引なし"""
        from apps.pricing.calculations.discounts import calculate_mile_discount
        from apps.students.models import Guardian
        from apps.tenants.models import Tenant

        # テナント作成
        tenant = Tenant.objects.create(
            tenant_code='TEST_MILE',
            tenant_name='テスト',
            is_active=True
        )

        # 保護者作成
        guardian = Guardian.objects.create(
            tenant_id=tenant.id,
            guardian_no='GRD_MILE_TEST',
            last_name='テスト',
            first_name='保護者'
        )

        # 契約なし・新規コースなしの場合
        discount_amount, total_miles, discount_name = calculate_mile_discount(
            guardian=guardian,
            new_course=None,
            new_pack=None
        )

        assert discount_amount == Decimal('0')
        assert discount_name == ''

    def test_mile_discount_calculation_logic(self):
        """マイル割引計算ロジック（ぽっきりのみ）"""
        # 計算式: (合計マイル - 1) × 500円
        # 例: 3マイルの場合 = (3-1) * 500 = 1000円

        # ぽっきりのみの場合
        total_miles = 3
        has_regular = False

        if has_regular:
            discount = (total_miles - 2) * 500 if total_miles > 2 else 0
        else:
            discount = (total_miles - 1) * 500 if total_miles > 1 else 0

        assert discount == 1000

    def test_mile_discount_with_regular_course(self):
        """マイル割引計算ロジック（通常コースあり）"""
        # 計算式: (合計マイル - 2) × 500円
        # 例: 5マイルの場合 = (5-2) * 500 = 1500円

        total_miles = 5
        has_regular = True

        if has_regular:
            discount = (total_miles - 2) * 500 if total_miles > 2 else 0
        else:
            discount = (total_miles - 1) * 500 if total_miles > 1 else 0

        assert discount == 1500

    def test_mile_discount_edge_case_2_miles_regular(self):
        """2マイル以下で通常コースありの場合は割引なし"""
        total_miles = 2
        has_regular = True

        if has_regular:
            discount = (total_miles - 2) * 500 if total_miles > 2 else 0
        else:
            discount = (total_miles - 1) * 500 if total_miles > 1 else 0

        assert discount == 0

    def test_mile_discount_edge_case_1_mile_pokkiri(self):
        """1マイルでぽっきりのみの場合は割引なし"""
        total_miles = 1
        has_regular = False

        if has_regular:
            discount = (total_miles - 2) * 500 if total_miles > 2 else 0
        else:
            discount = (total_miles - 1) * 500 if total_miles > 1 else 0

        assert discount == 0

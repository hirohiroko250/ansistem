"""
料金計算ゴールデンテスト

JSONベースのテストケースで料金計算の正確性を検証する。
"""
import json
import pytest
from pathlib import Path
from decimal import Decimal
from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.pricing.views.utils import (
    calculate_prorated_by_day_of_week,
    calculate_prorated_by_multiple_days,
    calculate_prorated_current_month_fees,
    calculate_prorated_current_month_fees_multiple,
)


class TestProratedCalculation(TestCase):
    """回数割計算のテスト"""

    def test_prorated_month_start(self):
        """月初は回数割なし（ratio = 1.0）"""
        result = calculate_prorated_by_day_of_week(date(2026, 1, 1), 3)  # 水曜
        self.assertEqual(result['ratio'], Decimal('1'))
        self.assertEqual(result['remaining_count'], result['total_count'])

    def test_prorated_month_middle(self):
        """月中は回数割あり（ratio < 1.0）"""
        result = calculate_prorated_by_day_of_week(date(2026, 1, 15), 3)  # 水曜
        self.assertLess(result['ratio'], Decimal('1'))
        self.assertLess(result['remaining_count'], result['total_count'])

    def test_prorated_month_end(self):
        """月末は回数割が最小"""
        result = calculate_prorated_by_day_of_week(date(2026, 1, 28), 3)  # 水曜
        self.assertLess(result['ratio'], Decimal('0.5'))

    def test_prorated_multiple_days(self):
        """複数曜日の回数割計算"""
        # 水曜と金曜
        result = calculate_prorated_by_multiple_days(date(2026, 1, 7), [3, 5])

        # 個別計算
        wed = calculate_prorated_by_day_of_week(date(2026, 1, 7), 3)
        fri = calculate_prorated_by_day_of_week(date(2026, 1, 7), 5)

        # 合計が一致
        self.assertEqual(
            result['remaining_count'],
            wed['remaining_count'] + fri['remaining_count']
        )
        self.assertEqual(
            result['total_count'],
            wed['total_count'] + fri['total_count']
        )


class TestPricingInvariants(TestCase):
    """料金計算の不変条件テスト（Property-based testing的アプローチ）"""

    def test_prorated_ratio_bounds(self):
        """回数割比率は0〜1の範囲"""
        for day in range(1, 32):
            try:
                test_date = date(2026, 1, day)
            except ValueError:
                continue

            for dow in range(1, 8):
                result = calculate_prorated_by_day_of_week(test_date, dow)
                self.assertGreaterEqual(result['ratio'], Decimal('0'))
                self.assertLessEqual(result['ratio'], Decimal('1'))

    def test_remaining_not_exceed_total(self):
        """残回数は合計回数を超えない"""
        for day in range(1, 32):
            try:
                test_date = date(2026, 1, day)
            except ValueError:
                continue

            for dow in range(1, 8):
                result = calculate_prorated_by_day_of_week(test_date, dow)
                self.assertLessEqual(
                    result['remaining_count'],
                    result['total_count']
                )

    def test_later_date_less_remaining(self):
        """開始日が遅いほど残回数は少ない（同じ曜日）"""
        dow = 3  # 水曜
        prev_remaining = None

        for day in range(1, 29):
            test_date = date(2026, 1, day)
            result = calculate_prorated_by_day_of_week(test_date, dow)

            if prev_remaining is not None:
                self.assertLessEqual(
                    result['remaining_count'],
                    prev_remaining,
                    f"Day {day} should have <= remaining than day {day-1}"
                )
            prev_remaining = result['remaining_count']

    def test_multiple_days_sum_correct(self):
        """複数曜日の合計は個別計算の合計と一致"""
        test_date = date(2026, 1, 10)
        days = [1, 3, 5]  # 月水金

        multi_result = calculate_prorated_by_multiple_days(test_date, days)

        individual_sum_remaining = 0
        individual_sum_total = 0
        for dow in days:
            single = calculate_prorated_by_day_of_week(test_date, dow)
            individual_sum_remaining += single['remaining_count']
            individual_sum_total += single['total_count']

        self.assertEqual(multi_result['remaining_count'], individual_sum_remaining)
        self.assertEqual(multi_result['total_count'], individual_sum_total)


class TestPricingAPI(TestCase):
    """料金プレビューAPIのテスト"""

    def setUp(self):
        self.client = APIClient()
        # テストユーザーのセットアップが必要

    @pytest.mark.skip(reason="テストデータのセットアップが必要")
    def test_preview_returns_required_fields(self):
        """プレビューAPIが必要なフィールドを返す"""
        response = self.client.post('/api/v1/pricing/preview/', {
            'student_id': 'test-student',
            'course_id': 'test-course',
            'product_ids': [],
            'start_date': '2026-01-07',
            'day_of_week': 3,
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # 必須フィールドの存在確認
        required_fields = [
            'items', 'subtotal', 'grandTotal',
            'billingByMonth', 'currentMonthProrated'
        ]
        for field in required_fields:
            self.assertIn(field, data, f"Missing field: {field}")


def load_golden_test_cases():
    """JSONからテストケースを読み込む"""
    test_dir = Path(__file__).parent / 'test_cases'
    cases = []

    for json_file in test_dir.glob('*.json'):
        with open(json_file) as f:
            file_cases = json.load(f)
            for case in file_cases:
                case['_file'] = json_file.name
                cases.append(case)

    return cases


# ゴールデンテストのパラメータ化
@pytest.mark.parametrize(
    "test_case",
    load_golden_test_cases(),
    ids=lambda tc: tc.get('name', 'unnamed')
)
def test_golden_case(test_case):
    """ゴールデンテストケースの実行"""
    input_data = test_case['input']
    expected = test_case['expected']

    # 開始日をパース
    start_date = date.fromisoformat(input_data['start_date'])

    # 複数曜日 or 単一曜日
    if 'days_of_week' in input_data:
        result = calculate_prorated_by_multiple_days(
            start_date,
            input_data['days_of_week']
        )
    elif 'day_of_week' in input_data:
        result = calculate_prorated_by_day_of_week(
            start_date,
            input_data['day_of_week']
        )
    else:
        pytest.skip("No day_of_week specified")
        return

    # 期待値の検証
    if 'current_month_prorated' in expected:
        cmp = expected['current_month_prorated']
        if cmp is None:
            # 回数割なし = ratio == 1
            assert result['ratio'] == Decimal('1'), \
                f"Expected no proration, but got ratio={result['ratio']}"
        else:
            if 'remaining_count_gte' in cmp:
                assert result['remaining_count'] >= cmp['remaining_count_gte']
            if 'total_count' in cmp:
                assert result['total_count'] == cmp['total_count']
            if 'ratio_lt' in cmp:
                assert float(result['ratio']) < cmp['ratio_lt']

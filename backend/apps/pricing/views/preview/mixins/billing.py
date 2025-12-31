"""
Billing Calculation Mixin - 請求計算
"""
import sys
from datetime import date as date_type
from decimal import Decimal

from apps.pricing.views.utils import (
    calculate_prorated_current_month_fees,
    get_monthly_tuition_prices,
)


class BillingCalculationMixin:
    """請求計算のMixin"""

    def _calculate_discounts(self, guardian, course, pack):
        """マイル割引を計算"""
        discounts = []
        discount_total = Decimal('0')

        if guardian and course:
            from apps.pricing.calculations import calculate_mile_discount
            try:
                mile_discount_amount, total_miles, mile_discount_name = calculate_mile_discount(
                    guardian=guardian,
                    new_course=course,
                    new_pack=pack
                )
                if mile_discount_amount > 0:
                    discounts.append({
                        'discountName': mile_discount_name,
                        'discountType': 'fixed',
                        'discountAmount': int(mile_discount_amount),
                    })
                    discount_total += mile_discount_amount
            except Exception as e:
                print(f"[PricingPreview] Error in calculate_mile_discount: {e}", file=sys.stderr)

        return discounts, discount_total

    def _get_monthly_tuition(self, course, start_date):
        """月別授業料を取得"""
        if not course or not start_date:
            return None

        monthly_tuition_data = get_monthly_tuition_prices(course, start_date)
        monthly_tuition = {
            'month1': monthly_tuition_data['month1'],
            'month2': monthly_tuition_data['month2'],
            'month1Price': monthly_tuition_data['month1Price'],
            'month2Price': monthly_tuition_data['month2Price'],
            'facilityFee': monthly_tuition_data['facilityFee'],
            'monthlyFee': monthly_tuition_data['monthlyFee'],
        }
        print(f"[PricingPreview] Monthly tuition: {monthly_tuition}", file=sys.stderr)
        return monthly_tuition

    def _setup_billing_labels(self, billing_by_month, start_date, monthly_tuition):
        """月別ラベルを設定"""
        if start_date and monthly_tuition:
            current_month = start_date.month
            billing_by_month['currentMonth']['label'] = f'{current_month}月分（当月）'
            billing_by_month['currentMonth']['month'] = current_month
            billing_by_month['month1']['label'] = f'{monthly_tuition["month1"]}月分'
            billing_by_month['month1']['month'] = monthly_tuition['month1']
            billing_by_month['month2']['label'] = f'{monthly_tuition["month2"]}月分〜'
            billing_by_month['month2']['month'] = monthly_tuition['month2']
        else:
            today = date_type.today()
            current_month = today.month
            next_month = (current_month % 12) + 1
            following_month = ((current_month + 1) % 12) + 1
            billing_by_month['currentMonth']['label'] = f'{current_month}月分（当月）'
            billing_by_month['currentMonth']['month'] = current_month
            billing_by_month['month1']['label'] = f'{next_month}月分'
            billing_by_month['month1']['month'] = next_month
            billing_by_month['month2']['label'] = f'{following_month}月分〜'
            billing_by_month['month2']['month'] = following_month

        return billing_by_month

    def _calculate_current_month_prorated(self, course, start_date, day_of_week):
        """当月分回数割料金を計算"""
        if not course or not start_date or not day_of_week:
            return None

        try:
            dow_int = int(day_of_week)
            if not (1 <= dow_int <= 7):
                return None

            prorated_data = calculate_prorated_current_month_fees(course, start_date, dow_int)
            if prorated_data['total_prorated'] <= 0:
                return None

            current_month_prorated = {
                'tuition': None,
                'facilityFee': None,
                'monthlyFee': None,
                'totalProrated': prorated_data['total_prorated'],
                'remainingCount': 0,
                'totalCount': 0,
                'ratio': 0,
                'dates': [],
            }

            if prorated_data['tuition']:
                current_month_prorated['tuition'] = {
                    'productId': prorated_data['tuition']['product_id'],
                    'productName': prorated_data['tuition']['product_name'],
                    'fullPrice': prorated_data['tuition']['full_price'],
                    'proratedPrice': prorated_data['tuition']['prorated_price'],
                }
                current_month_prorated['remainingCount'] = prorated_data['tuition']['remaining_count']
                current_month_prorated['totalCount'] = prorated_data['tuition']['total_count']
                current_month_prorated['ratio'] = prorated_data['tuition']['ratio']
                current_month_prorated['dates'] = prorated_data['tuition']['dates']

            if prorated_data['facility_fee']:
                current_month_prorated['facilityFee'] = {
                    'productId': prorated_data['facility_fee']['product_id'],
                    'productName': prorated_data['facility_fee']['product_name'],
                    'fullPrice': prorated_data['facility_fee']['full_price'],
                    'proratedPrice': prorated_data['facility_fee']['prorated_price'],
                }

            if prorated_data['monthly_fee']:
                current_month_prorated['monthlyFee'] = {
                    'productId': prorated_data['monthly_fee']['product_id'],
                    'productName': prorated_data['monthly_fee']['product_name'],
                    'fullPrice': prorated_data['monthly_fee']['full_price'],
                    'proratedPrice': prorated_data['monthly_fee']['prorated_price'],
                }

            print(f"[PricingPreview] Current month prorated: {current_month_prorated}", file=sys.stderr)
            return current_month_prorated

        except (ValueError, TypeError) as e:
            print(f"[PricingPreview] Error calculating prorated fees: {e}", file=sys.stderr)
            return None

    def _calculate_grand_total(self, enrollment_tuition_item, additional_fees, monthly_tuition, discount_total):
        """合計金額を計算"""
        enrollment_tuition_total = enrollment_tuition_item['total'] if enrollment_tuition_item else 0
        enrollment_fee = additional_fees.get('enrollmentFee', {}).get('price', 0)
        materials_fee = additional_fees.get('materialsFee', {}).get('price', 0)

        if monthly_tuition:
            month1_total = monthly_tuition['month1Price'] + monthly_tuition['facilityFee'] + monthly_tuition['monthlyFee']
            month2_total = monthly_tuition['month2Price'] + monthly_tuition['facilityFee'] + monthly_tuition['monthlyFee']
        else:
            month1_total = additional_fees.get('facilityFee', {}).get('price', 0) + additional_fees.get('monthlyFee', {}).get('price', 0)
            month2_total = month1_total

        return (
            enrollment_tuition_total +
            enrollment_fee +
            materials_fee +
            month1_total +
            month2_total -
            int(discount_total)
        )

    def _apply_prorated_fees(self, billing_by_month, current_month_prorated, enrollment_tuition_item):
        """回数割料金をbilling_by_monthに反映"""
        if current_month_prorated:
            # 設備費の回数割を反映
            if current_month_prorated.get('facilityFee'):
                for item in billing_by_month['currentMonth']['items']:
                    if item.get('itemType') == 'enrollment_facility':
                        old_price = item['priceWithTax']
                        new_price = current_month_prorated['facilityFee']['proratedPrice']
                        item['priceWithTax'] = new_price
                        item['unitPrice'] = int(new_price / 1.1)
                        item['billingCategoryName'] = "設備費（回数割）"
                        billing_by_month['currentMonth']['total'] -= old_price
                        billing_by_month['currentMonth']['total'] += new_price
                        print(f"[PricingPreview] Updated facility fee to prorated: ¥{old_price} -> ¥{new_price}", file=sys.stderr)

            # 月会費の回数割を反映
            if current_month_prorated.get('monthlyFee'):
                for item in billing_by_month['currentMonth']['items']:
                    if item.get('itemType') == 'enrollment_monthly_fee':
                        old_price = item['priceWithTax']
                        new_price = current_month_prorated['monthlyFee']['proratedPrice']
                        item['priceWithTax'] = new_price
                        item['unitPrice'] = int(new_price / 1.1)
                        item['billingCategoryName'] = "月会費（回数割）"
                        billing_by_month['currentMonth']['total'] -= old_price
                        billing_by_month['currentMonth']['total'] += new_price
                        print(f"[PricingPreview] Updated monthly fee to prorated: ¥{old_price} -> ¥{new_price}", file=sys.stderr)

        # 入会時授業料をcurrentMonthに追加
        if enrollment_tuition_item:
            billing_by_month['currentMonth']['items'].insert(0, {
                'productId': enrollment_tuition_item['productId'],
                'productName': enrollment_tuition_item['productName'],
                'billingCategoryName': '入会時授業料',
                'itemType': 'enrollment_tuition',
                'quantity': 1,
                'unitPrice': enrollment_tuition_item['unitPrice'],
                'priceWithTax': enrollment_tuition_item['total'],
                'taxRate': enrollment_tuition_item['taxRate'],
            })
            billing_by_month['currentMonth']['total'] += enrollment_tuition_item['total']

        return billing_by_month

    def _log_results(self, enrollment_tuition_item, additional_fees, monthly_tuition, discount_total, grand_total, billing_by_month, textbook_options):
        """結果をログ出力"""
        enrollment_tuition_total = enrollment_tuition_item['total'] if enrollment_tuition_item else 0
        enrollment_fee = additional_fees.get('enrollmentFee', {}).get('price', 0)
        materials_fee = additional_fees.get('materialsFee', {}).get('price', 0)

        if monthly_tuition:
            month1_total = monthly_tuition['month1Price'] + monthly_tuition['facilityFee'] + monthly_tuition['monthlyFee']
            month2_total = monthly_tuition['month2Price'] + monthly_tuition['facilityFee'] + monthly_tuition['monthlyFee']
        else:
            month1_total = 0
            month2_total = 0

        print(f"[PricingPreview] grandTotal calculation: enrollment_tuition={enrollment_tuition_total}, enrollment_fee={enrollment_fee}, materials_fee={materials_fee}, month1={month1_total}, month2={month2_total}, discount={discount_total}, total={grand_total}", file=sys.stderr)
        print(f"[PricingPreview] billingByMonth: enrollment={len(billing_by_month['enrollment']['items'])} items, currentMonth={len(billing_by_month['currentMonth']['items'])} items, month1={len(billing_by_month['month1']['items'])} items, month2={len(billing_by_month['month2']['items'])} items", file=sys.stderr)
        print(f"[PricingPreview] textbookOptions: {len(textbook_options)} items", file=sys.stderr)
        for opt in textbook_options:
            print(f"[PricingPreview]   - {opt['productName']}: {opt['paymentType']}, ¥{opt['unitPrice']}, billing={opt['billingMonths']}", file=sys.stderr)

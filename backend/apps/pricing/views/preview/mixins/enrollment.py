"""
Enrollment Fees Mixin - 入会時費用計算
"""
import sys
from decimal import Decimal

from apps.contracts.models import Course, Pack
from apps.pricing.calculations import calculate_enrollment_fees
from apps.pricing.views.utils import calculate_prorated_by_day_of_week

from ..helpers import process_course_pricing, process_pack_pricing


class EnrollmentFeesMixin:
    """入会時費用計算のMixin"""

    def _process_course_or_pack(self, course_id, start_date, items, subtotal):
        """コースまたはパックを処理"""
        course = None
        pack = None
        enrollment_tuition_item = None

        if not course_id:
            return course, pack, items, subtotal, enrollment_tuition_item

        # まずCourseを検索
        try:
            course = Course.objects.get(id=course_id)
            items, subtotal, enrollment_tuition_item = process_course_pricing(course, start_date, items, subtotal)
        except Course.DoesNotExist:
            # Courseが見つからない場合はPackを検索
            try:
                pack = Pack.objects.get(id=course_id)
                items, subtotal = process_pack_pricing(pack, start_date, items, subtotal)
            except Pack.DoesNotExist:
                print(f"[PricingPreview] Neither Course nor Pack found for id={course_id}", file=sys.stderr)

        return course, pack, items, subtotal, enrollment_tuition_item

    def _init_billing_by_month(self, include_month3=False):
        """月別料金グループを初期化

        Args:
            include_month3: 3ヶ月目を含めるかどうか（締日後の場合True）
        """
        billing = {
            'enrollment': {'label': '入会時費用', 'items': [], 'total': 0},
            'currentMonth': {'label': '', 'month': 0, 'items': [], 'total': 0},
            'month1': {'label': '', 'month': 0, 'items': [], 'total': 0},
            'month2': {'label': '', 'month': 0, 'items': [], 'total': 0},
        }
        if include_month3:
            billing['month3'] = {'label': '', 'month': 0, 'items': [], 'total': 0}
        return billing

    def _is_after_cutoff(self, cutoff_day=15):
        """今日が締日を過ぎているかどうかを判定（非推奨：_is_billing_confirmed を使用）

        Args:
            cutoff_day: 締日（デフォルト15日）
        Returns:
            bool: 締日を過ぎている場合True
        """
        from datetime import date as date_module
        today = date_module.today()
        return today.day > cutoff_day

    def _is_billing_confirmed(self, tenant_id=None):
        """当月の請求が確定済みかどうかを判定

        確定済みの場合、翌月分も請求に含める必要がある

        Returns:
            bool: 確定済みの場合True
        """
        from datetime import date as date_module
        from apps.billing.models import MonthlyBillingDeadline

        today = date_module.today()
        current_year = today.year
        current_month = today.month

        try:
            # テナントIDが指定されていない場合はデフォルトの1を使用
            tid = tenant_id or 1
            deadline = MonthlyBillingDeadline.objects.get(
                tenant_id=tid,
                year=current_year,
                month=current_month
            )
            # is_closed プロパティで確定状態を判定
            is_confirmed = deadline.is_closed
            print(f"[PricingPreview] Billing deadline check: {current_year}/{current_month} is_closed={is_confirmed}", file=sys.stderr)
            return is_confirmed
        except MonthlyBillingDeadline.DoesNotExist:
            # レコードがない場合は未確定とみなす
            print(f"[PricingPreview] No deadline record for {current_year}/{current_month}, treating as not confirmed", file=sys.stderr)
            return False

    def _calculate_enrollment_fees(self, course, start_date, day_of_week, student, guardian, billing_by_month, additional_fees):
        """入会時費用を計算"""
        enrollment_fees_calculated = []

        try:
            dow_int = int(day_of_week) if day_of_week else None
            if not dow_int or not (1 <= dow_int <= 7):
                return enrollment_fees_calculated, billing_by_month, additional_fees

            prorated_info = calculate_prorated_by_day_of_week(start_date, dow_int)
            additional_tickets = prorated_info['remaining_count']
            total_classes_in_month = prorated_info['total_count']

            print(f"[PricingPreview] Enrollment fees calculation: additional_tickets={additional_tickets}, total_classes={total_classes_in_month}", file=sys.stderr)

            enrollment_fees_calculated = calculate_enrollment_fees(
                course=course,
                tenant_id=str(course.tenant_id),
                enrollment_date=start_date,
                additional_tickets=additional_tickets,
                total_classes_in_month=total_classes_in_month,
                student=student,
                guardian=guardian,
            )

            # billing_by_month['enrollment']をクリアして新しい計算結果で上書き
            billing_by_month['enrollment']['items'] = []
            billing_by_month['enrollment']['total'] = 0

            for fee in enrollment_fees_calculated:
                if fee['calculated_price'] >= 0:
                    tax_rate = Decimal('0.1')
                    tax_amount = int(Decimal(str(fee['calculated_price'])) * tax_rate)
                    price_with_tax = fee['calculated_price'] + tax_amount

                    billing_category = fee['product_name'].split('【')[1].split('】')[0] if '【' in fee['product_name'] else fee['item_type']
                    item_data = {
                        'productId': fee['product_id'],
                        'productCode': fee['product_code'],
                        'productName': fee['product_name'],
                        'billingCategoryName': billing_category,
                        'itemType': fee['item_type'],
                        'quantity': 1,
                        'unitPrice': fee['calculated_price'],
                        'priceWithTax': price_with_tax,
                        'taxRate': float(tax_rate),
                        'calculationDetail': fee['calculation_detail'],
                    }
                    billing_by_month['enrollment']['items'].append(item_data)
                    billing_by_month['enrollment']['total'] += price_with_tax

                    # additional_feesにも追加
                    if fee['item_type'] == 'enrollment':
                        additional_fees['enrollmentFee'] = {
                            'productId': fee['product_id'],
                            'productName': fee['product_name'],
                            'price': price_with_tax,
                            'priceExcludingTax': fee['calculated_price'],
                            'taxRate': float(tax_rate),
                            'taxAmount': tax_amount,
                        }
                    elif fee['item_type'] == 'enrollment_textbook':
                        additional_fees['materialsFee'] = {
                            'productId': fee['product_id'],
                            'productName': fee['product_name'],
                            'price': price_with_tax,
                            'priceExcludingTax': fee['calculated_price'],
                            'taxRate': float(tax_rate),
                            'taxAmount': tax_amount,
                        }

            print(f"[PricingPreview] Enrollment fees: {len(enrollment_fees_calculated)} items, total={billing_by_month['enrollment']['total']}", file=sys.stderr)

        except Exception as e:
            print(f"[PricingPreview] Error calculating enrollment fees: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

        return enrollment_fees_calculated, billing_by_month, additional_fees

    def _ensure_enrollment_items(self, billing_by_month):
        """入会時費用の項目を0円で追加（項目がない場合）"""
        enrollment_item_types = [item.get('itemType') for item in billing_by_month['enrollment']['items']]

        if 'enrollment' not in enrollment_item_types:
            billing_by_month['enrollment']['items'].insert(0, {
                'productId': None,
                'productName': '入会金',
                'billingCategoryName': '入会金',
                'itemType': 'enrollment',
                'quantity': 1,
                'unitPrice': 0,
                'priceWithTax': 0,
                'taxRate': 0.1,
            })

        if 'enrollment_textbook' not in enrollment_item_types and 'textbook' not in enrollment_item_types:
            billing_by_month['enrollment']['items'].append({
                'productId': None,
                'productName': '教材費',
                'billingCategoryName': '入会時教材費',
                'itemType': 'enrollment_textbook',
                'quantity': 1,
                'unitPrice': 0,
                'priceWithTax': 0,
                'taxRate': 0.1,
            })

        return billing_by_month

"""
PricingPreviewService - 料金プレビューサービス

コース/パックの料金プレビュー計算のビジネスロジック
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from calendar import monthrange
from typing import Optional, Dict, List, Any

from apps.contracts.models import Course, Pack, Product, CourseItem, ProductPrice
from apps.students.models import Student, Guardian
from apps.billing.models import MileTransaction
from apps.pricing.calculations import (
    calculate_enrollment_fees,
    calculate_mile_discount,
    has_guardian_paid_enrollment_fee,
    has_student_received_bag,
)

logger = logging.getLogger(__name__)


class PricingPreviewService:
    """料金プレビューサービス"""

    @classmethod
    def calculate_prorated_by_day_of_week(
        cls,
        start_date: date,
        day_of_week: int
    ) -> Dict[str, Any]:
        """曜日ベースの回数割計算

        Args:
            start_date: 開始日
            day_of_week: 曜日（1=月, 2=火, 3=水, 4=木, 5=金, 6=土, 7=日）

        Returns:
            {'remaining_count': int, 'total_count': int, 'ratio': Decimal, 'dates': list}
        """
        if not start_date or day_of_week is None:
            return {
                'remaining_count': 0,
                'total_count': 0,
                'ratio': Decimal('0'),
                'dates': [],
            }

        python_weekday = day_of_week - 1 if day_of_week >= 1 else 6

        first_day = start_date.replace(day=1)
        last_day = start_date.replace(day=monthrange(start_date.year, start_date.month)[1])

        total_dates = []
        current = first_day
        while current <= last_day:
            if current.weekday() == python_weekday:
                total_dates.append(current)
            current += timedelta(days=1)

        remaining_dates = [d for d in total_dates if d >= start_date]

        total_count = len(total_dates)
        remaining_count = len(remaining_dates)

        ratio = Decimal(str(remaining_count)) / Decimal(str(total_count)) if total_count > 0 else Decimal('0')

        return {
            'remaining_count': remaining_count,
            'total_count': total_count,
            'ratio': ratio,
            'dates': remaining_dates,
        }

    @classmethod
    def calculate_enrollment_tickets(cls, start_date: date) -> int:
        """入会日から当月の追加チケット枚数を計算"""
        day = start_date.day

        if day <= 10:
            return 3
        elif day <= 20:
            return 2
        else:
            return 1

    @classmethod
    def get_monthly_tuition_prices(
        cls,
        course: Course,
        start_date: date,
        closing_day: int = 20
    ) -> Dict[str, Any]:
        """コースの月別授業料を取得

        Args:
            course: コース
            start_date: 開始日
            closing_day: 締日

        Returns:
            月別料金情報
        """
        if not course or not start_date:
            return {}

        enrollment_month = start_date.month
        enrollment_day = start_date.day

        if enrollment_day <= closing_day:
            month1 = enrollment_month + 1
            month2 = enrollment_month + 2
        else:
            month1 = enrollment_month + 2
            month2 = enrollment_month + 3

        if month1 > 12:
            month1 -= 12
        if month2 > 12:
            month2 -= 12

        # コース構成商品から授業料を取得
        tuition_product = None
        facility_product = None
        monthly_fee_product = None

        course_items = CourseItem.objects.filter(
            course=course,
            is_active=True
        ).select_related('product')

        for ci in course_items:
            product = ci.product
            if not product or not product.is_active:
                continue

            if product.item_type == Product.ItemType.TUITION:
                tuition_product = product
            elif product.item_type == Product.ItemType.FACILITY:
                facility_product = product
            elif product.item_type == Product.ItemType.MONTHLY_FEE:
                monthly_fee_product = product

        # 月別料金を取得
        month1_price = 0
        month2_price = 0

        if tuition_product:
            product_price = ProductPrice.objects.filter(
                product=tuition_product,
                is_active=True
            ).first()

            if product_price:
                month1_price = product_price.get_billing_price(month1) or 0
                month2_price = product_price.get_billing_price(month2) or 0
            else:
                month1_price = tuition_product.base_price or 0
                month2_price = tuition_product.base_price or 0

        return {
            'month1': month1,
            'month2': month2,
            'month1Price': int(month1_price),
            'month2Price': int(month2_price),
            'facilityFee': int(facility_product.base_price) if facility_product else 0,
            'monthlyFee': int(monthly_fee_product.base_price) if monthly_fee_product else 0,
        }

    @classmethod
    def calculate_current_month_prorated(
        cls,
        course: Course,
        start_date: date,
        day_of_week: int
    ) -> Dict[str, Any]:
        """当月分の回数割料金を計算

        Args:
            course: コース
            start_date: 開始日
            day_of_week: 曜日

        Returns:
            回数割料金情報
        """
        result = {
            'tuition': None,
            'facility_fee': None,
            'monthly_fee': None,
            'total_prorated': 0,
        }

        if not course or not start_date or day_of_week is None:
            return result

        proration = cls.calculate_prorated_by_day_of_week(start_date, day_of_week)

        if proration['ratio'] >= Decimal('1'):
            return result

        course_items = CourseItem.objects.filter(
            course=course,
            is_active=True
        ).select_related('product').prefetch_related('product__prices')

        for ci in course_items:
            product = ci.product
            if not product or not product.is_active:
                continue

            tax_rate = product.tax_rate or Decimal('0.1')
            base_price = product.base_price or Decimal('0')

            try:
                product_price = product.prices.filter(is_active=True).first()
                if product_price:
                    price = product_price.get_enrollment_price(start_date.month)
                    if price is not None:
                        base_price = Decimal(str(price))
            except Exception:
                pass

            full_price_with_tax = int(base_price * (1 + tax_rate))
            prorated_price = int(Decimal(str(full_price_with_tax)) * proration['ratio'])

            fee_info = {
                'product_id': str(product.id),
                'product_name': product.product_name,
                'full_price': full_price_with_tax,
                'prorated_price': prorated_price,
                'remaining_count': proration['remaining_count'],
                'total_count': proration['total_count'],
                'ratio': float(proration['ratio']),
                'dates': [d.isoformat() for d in proration['dates']],
            }

            if product.item_type == Product.ItemType.TUITION:
                result['tuition'] = fee_info
                result['total_prorated'] += prorated_price
            elif product.item_type == Product.ItemType.FACILITY:
                result['facility_fee'] = fee_info
                result['total_prorated'] += prorated_price
            elif product.item_type == Product.ItemType.MONTHLY_FEE:
                result['monthly_fee'] = fee_info
                result['total_prorated'] += prorated_price

        return result

    @classmethod
    def build_billing_by_month(
        cls,
        course: Course,
        start_date: date,
        day_of_week: Optional[int],
        student: Optional[Student],
        guardian: Optional[Guardian]
    ) -> Dict[str, Any]:
        """月別請求グループを構築

        Args:
            course: コース
            start_date: 開始日
            day_of_week: 曜日
            student: 生徒
            guardian: 保護者

        Returns:
            月別請求データ
        """
        billing_by_month = {
            'enrollment': {'label': '入会時', 'items': [], 'total': 0},
            'currentMonth': {'label': '当月分', 'items': [], 'total': 0, 'month': None},
            'month1': {'label': '翌月分', 'items': [], 'total': 0, 'month': None},
            'month2': {'label': '翌々月分〜', 'items': [], 'total': 0, 'month': None},
        }

        if not course:
            return billing_by_month

        course_items = CourseItem.objects.filter(
            course=course,
            is_active=True
        ).select_related('product')

        for ci in course_items:
            product = ci.product
            if not product or not product.is_active:
                continue

            base_price = product.base_price or Decimal('0')
            tax_rate = product.tax_rate or Decimal('0.1')
            tax_amount = int(base_price * tax_rate)
            price_with_tax = int(base_price) + tax_amount

            item_data = {
                'productId': str(product.id),
                'productName': product.product_name,
                'billingCategoryName': product.get_item_type_display(),
                'itemType': product.item_type,
                'quantity': ci.quantity,
                'unitPrice': int(base_price),
                'priceWithTax': price_with_tax,
                'taxRate': float(tax_rate),
            }

            item_type = product.item_type

            if item_type in ['enrollment', 'enrollment_textbook', 'bag']:
                billing_by_month['enrollment']['items'].append(item_data)
                billing_by_month['enrollment']['total'] += price_with_tax
            elif item_type in ['enrollment_monthly_fee', 'enrollment_facility']:
                billing_by_month['currentMonth']['items'].append(item_data)
                billing_by_month['currentMonth']['total'] += price_with_tax
            elif item_type in ['tuition', 'monthly_fee', 'facility']:
                billing_by_month['month1']['items'].append(item_data.copy())
                billing_by_month['month1']['total'] += price_with_tax
                billing_by_month['month2']['items'].append(item_data.copy())
                billing_by_month['month2']['total'] += price_with_tax

        # 入会時費用の自動計算
        if course and start_date and day_of_week:
            try:
                dow_int = int(day_of_week)
                if 1 <= dow_int <= 7:
                    prorated_info = cls.calculate_prorated_by_day_of_week(start_date, dow_int)
                    additional_tickets = prorated_info['remaining_count']
                    total_classes_in_month = prorated_info['total_count']

                    enrollment_fees = calculate_enrollment_fees(
                        course=course,
                        tenant_id=str(course.tenant_id),
                        enrollment_date=start_date,
                        additional_tickets=additional_tickets,
                        total_classes_in_month=total_classes_in_month,
                        student=student,
                        guardian=guardian,
                    )

                    billing_by_month['enrollment']['items'] = []
                    billing_by_month['enrollment']['total'] = 0

                    for fee in enrollment_fees:
                        if fee['calculated_price'] >= 0:
                            tax_rate = Decimal('0.1')
                            tax_amount = int(Decimal(str(fee['calculated_price'])) * tax_rate)
                            price_with_tax = fee['calculated_price'] + tax_amount

                            item_data = {
                                'productId': fee['product_id'],
                                'productCode': fee['product_code'],
                                'productName': fee['product_name'],
                                'itemType': fee['item_type'],
                                'quantity': 1,
                                'unitPrice': fee['calculated_price'],
                                'priceWithTax': price_with_tax,
                                'taxRate': float(tax_rate),
                                'calculationDetail': fee['calculation_detail'],
                            }
                            billing_by_month['enrollment']['items'].append(item_data)
                            billing_by_month['enrollment']['total'] += price_with_tax

            except Exception as e:
                logger.error(f"Error calculating enrollment fees: {e}")

        # 月別ラベルを設定
        if start_date:
            monthly_tuition = cls.get_monthly_tuition_prices(course, start_date)
            current_month = start_date.month
            billing_by_month['currentMonth']['label'] = f'{current_month}月分（当月）'
            billing_by_month['currentMonth']['month'] = current_month
            billing_by_month['month1']['label'] = f'{monthly_tuition["month1"]}月分'
            billing_by_month['month1']['month'] = monthly_tuition['month1']
            billing_by_month['month2']['label'] = f'{monthly_tuition["month2"]}月分〜'
            billing_by_month['month2']['month'] = monthly_tuition['month2']

        return billing_by_month

    @classmethod
    def calculate_discounts(
        cls,
        guardian: Optional[Guardian],
        course: Optional[Course] = None,
        pack: Optional[Pack] = None
    ) -> List[Dict[str, Any]]:
        """割引を計算

        Args:
            guardian: 保護者
            course: コース
            pack: パック

        Returns:
            割引リスト
        """
        discounts = []

        if not guardian:
            return discounts

        # マイル割引
        if course or pack:
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
                        'totalMiles': total_miles,
                    })
            except Exception as e:
                logger.error(f"Error calculating mile discount: {e}")

        return discounts

    @classmethod
    def get_mile_info(cls, guardian: Optional[Guardian]) -> Dict[str, Any]:
        """マイル情報を取得

        Args:
            guardian: 保護者

        Returns:
            マイル情報
        """
        if not guardian:
            return {
                'currentBalance': 0,
                'canUseMiles': False,
            }

        balance = MileTransaction.get_balance(guardian)
        can_use = MileTransaction.can_use_miles(guardian)

        return {
            'currentBalance': balance,
            'canUseMiles': can_use,
        }

"""
料金計算エンジン

T3契約の料金計算ロジック:
- 初月: 「X月入会者」列の金額を使用
- 2ヶ月目以降: 「X月」列の月額料金を使用
- 月途中入会の追加チケット: 月額 ÷ 3.3 × 追加チケット枚数（四捨五入）
- 税区分: 1,2=課税（10%加算）, 3=非課税
- 3.3計算なし: 入会金、教材費、入会時教材費
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.contracts.models import Product, ProductPrice


class PricingEngine:
    """料金計算エンジン"""

    TICKET_DIVISOR = Decimal('3.3')
    TAX_RATE = Decimal('1.10')  # 消費税10%

    # 3.3計算を適用しないカテゴリ
    NO_TICKET_CALC_TYPES = [
        'enrollment',   # 入会金
        'textbook',     # 教材費
    ]

    # 3.3計算を適用しない商品名パターン
    NO_TICKET_CALC_NAMES = [
        '入会金',
        '教材費',
        '入会時教材費',
    ]

    def calculate_product_price(
        self,
        product: 'Product',
        enrollment_date: date,
        target_month: int,
        target_year: int,
        additional_tickets: int = 0,
        tax_category: int = 1,
    ) -> dict:
        """
        商品の料金を計算

        Args:
            product: 商品マスタ
            enrollment_date: 入会日
            target_month: 計算対象月（1〜12）
            target_year: 計算対象年
            additional_tickets: 追加チケット枚数
            tax_category: 税区分（1=課税, 2=課税, 3=非課税）

        Returns:
            {
                'product_id': 商品ID,
                'product_name': 商品名,
                'base_price': 基本料金（税抜）,
                'additional_ticket_price': 追加チケット料金（税抜）,
                'subtotal': 小計（税抜）,
                'tax_amount': 消費税額,
                'total_price': 合計金額（税込）,
                'is_first_month': 初月かどうか,
                'tax_category': 税区分,
                'applies_ticket_calc': 3.3計算適用するか
            }
        """
        enrollment_month = enrollment_date.month
        enrollment_year = enrollment_date.year

        # 初月判定
        is_first_month = (
            target_month == enrollment_month and
            target_year == enrollment_year
        )

        # 基本料金取得
        if is_first_month:
            base_price = self._get_first_month_price(product, enrollment_month)
        else:
            base_price = self._get_billing_month_price(product, target_month)

        # 3.3計算を適用するかどうか
        applies_ticket_calc = self._should_apply_ticket_calc(product)

        # 追加チケット料金計算（対象カテゴリのみ）
        additional_ticket_price = Decimal(0)
        if additional_tickets > 0 and applies_ticket_calc:
            monthly_price = self._get_billing_month_price(product, target_month)
            per_ticket = monthly_price / self.TICKET_DIVISOR
            additional_ticket_price = (per_ticket * additional_tickets).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )

        # 小計（税抜）
        subtotal = base_price + additional_ticket_price

        # 税計算（金額は税抜で登録されている）
        if tax_category in [1, 2]:  # 課税 → 10%加算
            tax_amount = (subtotal * (self.TAX_RATE - 1)).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
            total_price = subtotal + tax_amount
        else:  # 非課税（税区分=3）
            tax_amount = Decimal(0)
            total_price = subtotal

        return {
            'product_id': str(product.id),
            'product_name': product.product_name,
            'item_type': product.item_type,
            'base_price': int(base_price),
            'additional_ticket_price': int(additional_ticket_price),
            'subtotal': int(subtotal),
            'tax_amount': int(tax_amount),
            'total_price': int(total_price),
            'is_first_month': is_first_month,
            'tax_category': tax_category,
            'applies_ticket_calc': applies_ticket_calc,
            'additional_tickets': additional_tickets,
        }

    def _get_first_month_price(self, product: 'Product', enrollment_month: int) -> Decimal:
        """入会月に応じた初月料金を取得"""
        # ProductPriceから取得を試みる
        price_record = product.prices.filter(is_active=True).first()
        if price_record:
            price = price_record.get_enrollment_price(enrollment_month)
            if price is not None:
                return Decimal(price)
        return Decimal(product.base_price)

    def _get_billing_month_price(self, product: 'Product', billing_month: int) -> Decimal:
        """請求月に応じた月額料金を取得"""
        # ProductPriceから取得を試みる
        price_record = product.prices.filter(is_active=True).first()
        if price_record:
            price = price_record.get_billing_price(billing_month)
            if price is not None:
                return Decimal(price)
        return Decimal(product.base_price)

    def _should_apply_ticket_calc(self, product: 'Product') -> bool:
        """3.3計算を適用するかどうか判定"""
        # 商品種別でチェック
        if product.item_type in self.NO_TICKET_CALC_TYPES:
            return False

        # 商品名でチェック
        for name_pattern in self.NO_TICKET_CALC_NAMES:
            if name_pattern in product.product_name:
                return False

        return True

    def calculate_course_price(
        self,
        course,
        enrollment_date: date,
        target_month: int,
        target_year: int,
        additional_tickets: int = 0,
        tax_category: int = 1,
    ) -> dict:
        """
        コースの料金を計算（コース構成商品の合計）

        Args:
            course: コースマスタ
            enrollment_date: 入会日
            target_month: 計算対象月
            target_year: 計算対象年
            additional_tickets: 追加チケット枚数
            tax_category: 税区分

        Returns:
            {
                'course_id': コースID,
                'course_name': コース名,
                'items': [商品ごとの計算結果...],
                'subtotal': 小計（税抜）,
                'tax_amount': 消費税合計,
                'total_price': 合計金額（税込）,
                'is_first_month': 初月かどうか
            }
        """
        items = []
        subtotal = Decimal(0)
        tax_total = Decimal(0)

        # コース構成商品を取得
        for course_item in course.course_items.filter(is_active=True):
            product = course_item.product
            quantity = course_item.quantity

            # 商品料金を計算
            item_result = self.calculate_product_price(
                product=product,
                enrollment_date=enrollment_date,
                target_month=target_month,
                target_year=target_year,
                additional_tickets=additional_tickets,
                tax_category=tax_category,
            )

            # 数量を乗算
            for key in ['base_price', 'additional_ticket_price', 'subtotal', 'tax_amount', 'total_price']:
                item_result[key] = item_result[key] * quantity

            item_result['quantity'] = quantity
            items.append(item_result)

            subtotal += Decimal(item_result['subtotal'])
            tax_total += Decimal(item_result['tax_amount'])

        enrollment_month = enrollment_date.month
        enrollment_year = enrollment_date.year
        is_first_month = (
            target_month == enrollment_month and
            target_year == enrollment_year
        )

        return {
            'course_id': str(course.id),
            'course_name': course.course_name,
            'items': items,
            'subtotal': int(subtotal),
            'tax_amount': int(tax_total),
            'total_price': int(subtotal + tax_total),
            'is_first_month': is_first_month,
            'enrollment_month': enrollment_month,
            'target_month': target_month,
            'additional_tickets': additional_tickets,
        }

    def calculate_pack_price(
        self,
        pack,
        enrollment_date: date,
        target_month: int,
        target_year: int,
        additional_tickets: int = 0,
        tax_category: int = 1,
    ) -> dict:
        """
        パックの料金を計算

        Args:
            pack: パックマスタ
            enrollment_date: 入会日
            target_month: 計算対象月
            target_year: 計算対象年
            additional_tickets: 追加チケット枚数
            tax_category: 税区分

        Returns:
            {
                'pack_id': パックID,
                'pack_name': パック名,
                'courses': [コースごとの計算結果...],
                'pack_items': [パック直属商品の計算結果...],
                'subtotal': 小計（税抜）,
                'discount_amount': 割引額,
                'tax_amount': 消費税合計,
                'total_price': 合計金額（税込）
            }
        """
        courses = []
        pack_items = []
        subtotal = Decimal(0)
        tax_total = Decimal(0)

        # パック構成コースを取得
        for pack_course in pack.pack_courses.filter(is_active=True):
            course_result = self.calculate_course_price(
                course=pack_course.course,
                enrollment_date=enrollment_date,
                target_month=target_month,
                target_year=target_year,
                additional_tickets=additional_tickets,
                tax_category=tax_category,
            )
            courses.append(course_result)
            subtotal += Decimal(course_result['subtotal'])
            tax_total += Decimal(course_result['tax_amount'])

        # パック直属商品を取得
        for pack_item in pack.pack_items.filter(is_active=True):
            product = pack_item.product
            quantity = pack_item.quantity

            item_result = self.calculate_product_price(
                product=product,
                enrollment_date=enrollment_date,
                target_month=target_month,
                target_year=target_year,
                additional_tickets=additional_tickets,
                tax_category=tax_category,
            )

            for key in ['base_price', 'additional_ticket_price', 'subtotal', 'tax_amount', 'total_price']:
                item_result[key] = item_result[key] * quantity

            item_result['quantity'] = quantity
            pack_items.append(item_result)

            subtotal += Decimal(item_result['subtotal'])
            tax_total += Decimal(item_result['tax_amount'])

        # 割引適用
        discount_amount = Decimal(0)
        if pack.discount_type == 'percentage':
            discount_amount = (subtotal * pack.discount_value / 100).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
        elif pack.discount_type == 'fixed':
            discount_amount = Decimal(pack.discount_value)

        subtotal_after_discount = max(subtotal - discount_amount, Decimal(0))

        # 割引後の税額再計算
        if tax_category in [1, 2]:
            tax_after_discount = (subtotal_after_discount * (self.TAX_RATE - 1)).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
        else:
            tax_after_discount = Decimal(0)

        enrollment_month = enrollment_date.month
        enrollment_year = enrollment_date.year
        is_first_month = (
            target_month == enrollment_month and
            target_year == enrollment_year
        )

        return {
            'pack_id': str(pack.id),
            'pack_name': pack.pack_name,
            'courses': courses,
            'pack_items': pack_items,
            'subtotal_before_discount': int(subtotal),
            'discount_amount': int(discount_amount),
            'discount_type': pack.discount_type,
            'subtotal': int(subtotal_after_discount),
            'tax_amount': int(tax_after_discount),
            'total_price': int(subtotal_after_discount + tax_after_discount),
            'is_first_month': is_first_month,
            'enrollment_month': enrollment_month,
            'target_month': target_month,
            'additional_tickets': additional_tickets,
        }

    def preview_monthly_billing(
        self,
        contract,
        target_month: int,
        target_year: int,
        additional_tickets: int = 0,
    ) -> dict:
        """
        契約の月次請求プレビュー

        Args:
            contract: 契約
            target_month: 計算対象月
            target_year: 計算対象年
            additional_tickets: 追加チケット枚数

        Returns:
            月次請求のプレビュー
        """
        enrollment_date = contract.start_date

        if contract.course:
            result = self.calculate_course_price(
                course=contract.course,
                enrollment_date=enrollment_date,
                target_month=target_month,
                target_year=target_year,
                additional_tickets=additional_tickets,
                tax_category=1,  # デフォルト課税
            )
            result['contract_id'] = str(contract.id)
            result['contract_no'] = contract.contract_no
            return result

        return {
            'contract_id': str(contract.id),
            'contract_no': contract.contract_no,
            'error': 'コースが設定されていません',
        }

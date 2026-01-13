"""
Preview Helpers - 料金プレビュー計算ヘルパー
"""
import re
import sys
from decimal import Decimal

from apps.contracts.models import Course, Pack, Product, CourseItem, ProductSetItem
from apps.pricing.views.utils import (
    get_product_price_for_enrollment,
    calculate_enrollment_tuition_tickets,
    get_enrollment_tuition_product,
)


def extract_billing_months(product_name: str) -> list:
    """商品名から請求月を抽出

    例:
    - 「半年払い（4月・10月）」→ [4, 10]
    - 「月払い」→ [] (毎月)
    - 「（4月・8月・12月）」→ [4, 8, 12]
    """
    months = []
    pattern = r'(\d+)月'
    matches = re.findall(pattern, product_name)
    if matches:
        months = [int(m) for m in matches]
    return months


def process_course_pricing(course, start_date, items, subtotal):
    """コースの料金処理"""
    price = course.get_price()
    print(f"[PricingPreview] Found course: {course.course_name}, price={price}", file=sys.stderr)

    item = {
        'productId': str(course.id),
        'productName': course.course_name,
        'productType': 'tuition',
        'unitPrice': int(price),
        'quantity': 1,
        'subtotal': int(price),
        'taxRate': 0.1,
        'taxAmount': int(price * Decimal('0.1')),
        'discountAmount': 0,
        'total': int(price * Decimal('1.1')),
    }
    items.append(item)
    subtotal += price

    # 入会時授業料（追加チケット）を計算
    enrollment_tuition_item = None
    if start_date and start_date.day > 1:
        enrollment_tuition_item = calculate_course_enrollment_tuition(course, start_date)
        if enrollment_tuition_item:
            items.append(enrollment_tuition_item)
            subtotal += Decimal(str(enrollment_tuition_item['unitPrice']))

    return items, subtotal, enrollment_tuition_item


def calculate_course_enrollment_tuition(course, start_date):
    """コースの入会時授業料を計算"""
    tickets = calculate_enrollment_tuition_tickets(start_date)
    enrollment_product = get_enrollment_tuition_product(course, tickets)

    if not enrollment_product:
        print(f"[PricingPreview] No enrollment tuition product found for {tickets} tickets", file=sys.stderr)
        return None

    enrollment_price = get_product_price_for_enrollment(enrollment_product, start_date)
    enrollment_tuition_item = {
        'productId': str(enrollment_product.id),
        'productName': enrollment_product.product_name,
        'productType': 'enrollment_tuition',
        'unitPrice': int(enrollment_price),
        'quantity': 1,
        'subtotal': int(enrollment_price),
        'taxRate': 0.1,
        'taxAmount': int(enrollment_price * Decimal('0.1')),
        'discountAmount': 0,
        'total': int(enrollment_price * Decimal('1.1')),
        'tickets': tickets,
        'isEnrollmentTuition': True,
    }
    print(f"[PricingPreview] Added enrollment tuition: {enrollment_product.product_name}, tickets={tickets}, price={enrollment_price}", file=sys.stderr)
    return enrollment_tuition_item


def process_pack_pricing(pack, start_date, items, subtotal):
    """パックの料金処理"""
    price = pack.pack_price or Decimal('0')
    print(f"[PricingPreview] Found pack: {pack.pack_name}, price={price}", file=sys.stderr)

    item = {
        'productId': str(pack.id),
        'productName': pack.pack_name,
        'productType': 'pack',
        'unitPrice': int(price),
        'quantity': 1,
        'subtotal': int(price),
        'taxRate': 0.1,
        'taxAmount': int(price * Decimal('0.1')),
        'discountAmount': 0,
        'total': int(price * Decimal('1.1')),
    }
    items.append(item)
    subtotal += price

    # パック内のコースごとの入会時授業料を計算
    if start_date and start_date.day > 1:
        pack_courses = pack.pack_courses.filter(is_active=True).select_related('course')
        for pack_course in pack_courses:
            pc_course = pack_course.course
            if pc_course:
                enrollment_item = calculate_course_enrollment_tuition(pc_course, start_date)
                if enrollment_item:
                    # パックのコース名を付加
                    enrollment_item['productName'] = f'{pc_course.course_name} - {enrollment_item["productName"]}'
                    items.append(enrollment_item)
                    subtotal += Decimal(str(enrollment_item['unitPrice']))

    return items, subtotal


def process_product_ids(product_ids, course_id, items, subtotal):
    """商品IDリストから料金を取得"""
    for product_id in product_ids:
        if product_id == course_id:
            continue  # コースと重複する場合はスキップ
        try:
            product = Product.objects.get(id=product_id)
            price = product.base_price
            item = {
                'productId': str(product.id),
                'productName': product.product_name,
                'productType': product.item_type,
                'unitPrice': int(price),
                'quantity': 1,
                'subtotal': int(price),
                'taxRate': float(product.tax_rate),
                'taxAmount': int(price * product.tax_rate),
                'discountAmount': 0,
                'total': int(price * (1 + product.tax_rate)),
            }
            items.append(item)
            subtotal += price
        except Product.DoesNotExist:
            pass
    return items, subtotal


def build_product_item_data(product, quantity, source):
    """商品データを構築"""
    base_price = product.base_price or Decimal('0')
    tax_rate = product.tax_rate or Decimal('0.1')
    tax_amount = int(base_price * tax_rate)
    price_with_tax = int(base_price) + tax_amount

    return {
        'productId': str(product.id),
        'productName': product.product_name,
        'billingCategoryName': product.get_item_type_display(),
        'itemType': product.item_type,
        'quantity': quantity,
        'unitPrice': int(base_price),
        'priceWithTax': price_with_tax,
        'taxRate': float(tax_rate),
        'source': source,
    }


def build_textbook_option(product, start_date, source):
    """教材費オプションを構築"""
    base_price = product.base_price or Decimal('0')
    tax_rate = product.tax_rate or Decimal('0.1')
    textbook_price = base_price
    textbook_tax_amount = int(textbook_price * tax_rate)
    textbook_price_with_tax = int(textbook_price) + textbook_tax_amount

    # 入会時教材費（傾斜料金）を計算
    enrollment_month = start_date.month if start_date else None
    enrollment_textbook_price = int(product.get_price_for_enrollment_month(enrollment_month)) if enrollment_month else int(base_price)
    enrollment_textbook_tax = int(enrollment_textbook_price * tax_rate)
    enrollment_textbook_price_with_tax = enrollment_textbook_price + enrollment_textbook_tax

    # 支払いタイプを判定
    product_name = product.product_name
    if '月払い' in product_name:
        payment_type = 'monthly'
    elif '半年払い' in product_name or '半期' in product_name:
        payment_type = 'semi_annual'
    else:
        payment_type = 'annual'

    return {
        'productId': str(product.id),
        'productCode': product.product_code,
        'productName': product.product_name,
        'itemType': product.item_type,
        'unitPrice': int(textbook_price),
        'priceWithTax': textbook_price_with_tax,
        'basePrice': int(base_price),
        'enrollmentMonth': enrollment_month,
        'enrollmentPrice': enrollment_textbook_price,
        'enrollmentPriceWithTax': enrollment_textbook_price_with_tax,
        'taxRate': float(tax_rate),
        'paymentType': payment_type,
        'billingMonths': extract_billing_months(product.product_name),
        'source': source,
    }


def categorize_item_to_billing_month(item_data, item_type, billing_by_month):
    """商品を月別グループに振り分け"""
    price_with_tax = item_data['priceWithTax']

    print(f"[PricingPreview] Product: {item_data['productName']}, item_type: '{item_type}'", file=sys.stderr, flush=True)

    if item_type in ['enrollment', 'enrollment_textbook', 'bag']:
        billing_by_month['enrollment']['items'].append(item_data)
        billing_by_month['enrollment']['total'] += price_with_tax
        print(f"[PricingPreview]   -> Added to enrollment", file=sys.stderr)
    elif item_type in ['enrollment_monthly_fee', 'enrollment_facility']:
        billing_by_month['currentMonth']['items'].append(item_data)
        billing_by_month['currentMonth']['total'] += price_with_tax
        print(f"[PricingPreview]   -> Added to currentMonth", file=sys.stderr)
    elif item_type == 'enrollment_tuition':
        print(f"[PricingPreview]   -> Skipped (enrollment_tuition variant)", file=sys.stderr)
    elif item_type in ['tuition', 'monthly_fee', 'facility']:
        billing_by_month['month1']['items'].append(item_data.copy())
        billing_by_month['month1']['total'] += price_with_tax
        billing_by_month['month2']['items'].append(item_data.copy())
        billing_by_month['month2']['total'] += price_with_tax
        # month3がある場合（締日後）は3ヶ月目も追加
        if 'month3' in billing_by_month:
            billing_by_month['month3']['items'].append(item_data.copy())
            billing_by_month['month3']['total'] += price_with_tax
            print(f"[PricingPreview]   -> Added to month1, month2, and month3", file=sys.stderr)
        else:
            print(f"[PricingPreview]   -> Added to month1 and month2", file=sys.stderr)
    else:
        print(f"[PricingPreview]   -> NOT MATCHED (item_type not in any group)", file=sys.stderr)


def add_fee_to_additional_fees(product, price_with_tax, base_price, tax_rate, tax_amount, additional_fees, subtotal):
    """追加料金（入会金、設備費など）を追加"""
    fee_key = None
    if product.item_type == Product.ItemType.ENROLLMENT:
        fee_key = 'enrollmentFee'
    elif product.item_type == Product.ItemType.FACILITY:
        fee_key = 'facilityFee'
    elif product.item_type == Product.ItemType.ENROLLMENT_TEXTBOOK:
        fee_key = 'materialsFee'
    elif product.item_type == Product.ItemType.MONTHLY_FEE:
        fee_key = 'monthlyFee'

    if fee_key:
        additional_fees[fee_key] = {
            'productId': str(product.id),
            'productName': product.product_name,
            'price': price_with_tax,
            'priceExcludingTax': int(base_price),
            'taxRate': float(tax_rate),
            'taxAmount': tax_amount,
        }
        subtotal += Decimal(str(price_with_tax))

    return additional_fees, subtotal


def process_course_items(course, start_date, billing_by_month, textbook_options, additional_fees, subtotal, course_items_list):
    """コースアイテムを処理"""
    # 商品セット（ProductSet）の商品を追加
    if course.product_set:
        set_items = ProductSetItem.objects.filter(
            product_set=course.product_set,
            is_active=True
        ).select_related('product')

        for si in set_items:
            product = si.product
            if not product or not product.is_active:
                continue

            item_data = build_product_item_data(product, si.quantity, 'product_set')
            course_items_list.append(item_data)
            subtotal += Decimal(str(item_data['priceWithTax']))

            item_type = product.item_type
            if item_type == 'textbook':
                textbook_option = build_textbook_option(product, start_date, 'product_set')
                textbook_options.append(textbook_option)
                print(f"[PricingPreview]   -> Added to textbook_options (base_price={textbook_option['unitPrice']}, enrollment_price={textbook_option['enrollmentPrice']})", file=sys.stderr)
            else:
                categorize_item_to_billing_month(item_data, item_type, billing_by_month)

    # CourseItemを処理
    course_items = CourseItem.objects.filter(
        course=course,
        is_active=True
    ).select_related('product')

    print(f"[PricingPreview] CourseItems count: {course_items.count()}, ProductSet: {course.product_set}", file=sys.stderr, flush=True)

    for ci in course_items:
        product = ci.product
        if not product or not product.is_active:
            continue

        item_data = build_product_item_data(product, ci.quantity, 'course_item')
        course_items_list.append(item_data)

        base_price = product.base_price or Decimal('0')
        tax_rate = product.tax_rate or Decimal('0.1')
        tax_amount = int(base_price * tax_rate)
        price_with_tax = item_data['priceWithTax']

        item_type = product.item_type
        if item_type == 'textbook':
            textbook_option = build_textbook_option(product, start_date, 'course_item')
            textbook_options.append(textbook_option)
            print(f"[PricingPreview]   -> Added to textbook_options (base_price={textbook_option['unitPrice']}, enrollment_price={textbook_option['enrollmentPrice']})", file=sys.stderr)
        else:
            categorize_item_to_billing_month(item_data, item_type, billing_by_month)

        # 追加料金に登録
        additional_fees, subtotal = add_fee_to_additional_fees(
            product, price_with_tax, base_price, tax_rate, tax_amount,
            additional_fees, subtotal
        )

    return billing_by_month, textbook_options, additional_fees, subtotal, course_items_list

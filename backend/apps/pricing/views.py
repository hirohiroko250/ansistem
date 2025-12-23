"""
Pricing views - 料金計算・購入確認API
"""
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from calendar import monthrange
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.contracts.models import Course, Pack, StudentItem, Product, ProductPrice, Contract
from apps.students.models import Student, StudentSchool, StudentEnrollment
from apps.tasks.models import Task
from apps.schools.models import Brand, School, ClassSchedule
from apps.billing.models import MileTransaction
from apps.pricing.calculations import (
    calculate_all_fees_and_discounts,
    calculate_fs_discount_amount,
    calculate_enrollment_fees,
    get_enrollment_products_for_course,
)


def get_product_price_for_enrollment(product: Product, enrollment_date: date) -> Decimal:
    """
    商品の入会月別料金を取得

    ProductPrice（T05_商品料金）に入会月別料金が設定されている場合はそれを使用、
    なければ商品の基本価格（base_price）を使用する。

    Args:
        product: 商品
        enrollment_date: 入会日

    Returns:
        料金（Decimal）
    """
    if not product:
        return Decimal('0')

    enrollment_month = enrollment_date.month

    # ProductPriceから入会月別料金を取得
    try:
        product_price = ProductPrice.objects.filter(
            product=product,
            is_active=True
        ).first()

        if product_price:
            price = product_price.get_enrollment_price(enrollment_month)
            if price is not None:
                return Decimal(str(price))
    except Exception as e:
        print(f"[get_product_price_for_enrollment] Error: {e}", file=sys.stderr)

    # ProductPriceがない場合は基本価格を使用
    return product.base_price or Decimal('0')


def calculate_enrollment_tuition_tickets(start_date: date) -> int:
    """
    入会日から当月の追加チケット枚数を計算

    月途中入会の場合、残り週数に応じてチケット枚数を決定:
    - 1日〜10日入会: 3チケット（残り3週以上）
    - 11日〜20日入会: 2チケット（残り2週程度）
    - 21日以降入会: 1チケット（残り1週程度）
    """
    day = start_date.day

    if day <= 10:
        return 3
    elif day <= 20:
        return 2
    else:
        return 1


def get_enrollment_tuition_product(course: Course, tickets: int) -> Product:
    """
    コースに対応する入会時授業料商品を取得

    商品コード体系: {course_code_prefix}_51 (1回分), _52 (2回分), _53 (3回分)
    """
    if not course or tickets < 1 or tickets > 3:
        return None

    # コースコードから商品コードプレフィックスを推測
    # 例: "24AEC_1000009" → "24AEC_1000009_5X"
    course_code = course.course_code if course.course_code else ''

    # 対応する入会時授業料商品を検索
    product_code_suffix = f'_5{tickets}'  # _51, _52, _53

    # まず完全一致で検索
    product = Product.objects.filter(
        tenant_id=course.tenant_id,
        product_code__endswith=product_code_suffix,
        product_code__startswith=course_code[:course_code.rfind('_')] if '_' in course_code else course_code,
        is_enrollment_tuition=True,
        deleted_at__isnull=True,
        is_active=True,
    ).first()

    if product:
        return product

    # ブランドで検索（同じブランドの入会時授業料商品）
    if course.brand:
        product = Product.objects.filter(
            tenant_id=course.tenant_id,
            brand=course.brand,
            is_enrollment_tuition=True,
            product_name__contains=f'{tickets}回分',
            deleted_at__isnull=True,
            is_active=True,
        ).first()

        if product:
            return product

    return None


def calculate_prorated_by_day_of_week(start_date: date, day_of_week: int) -> dict:
    """
    曜日ベースの回数割計算

    開始日から月末までの指定曜日の回数と、月全体での回数から比率を計算。

    Args:
        start_date: 開始日
        day_of_week: 曜日（1=月, 2=火, 3=水, 4=木, 5=金, 6=土, 7=日）

    Returns:
        {
            'remaining_count': int,  # 開始日から月末までの回数
            'total_count': int,      # 月全体の回数
            'ratio': Decimal,        # 比率（remaining / total）
            'dates': list[date],     # 対象日のリスト
        }
    """
    if not start_date or day_of_week is None:
        return {
            'remaining_count': 0,
            'total_count': 0,
            'ratio': Decimal('0'),
            'dates': [],
        }

    # Python weekday: 0=月, 1=火, ... 6=日
    # 入力: 1=月, 2=火, ... 7=日
    python_weekday = day_of_week - 1 if day_of_week >= 1 else 6

    # 月初と月末を取得
    first_day = start_date.replace(day=1)
    last_day = start_date.replace(day=monthrange(start_date.year, start_date.month)[1])

    # 月全体での該当曜日をカウント
    total_dates = []
    current = first_day
    while current <= last_day:
        if current.weekday() == python_weekday:
            total_dates.append(current)
        current += timedelta(days=1)

    # 開始日以降の該当曜日をカウント
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


def calculate_prorated_current_month_fees(
    course: Course,
    start_date: date,
    day_of_week: int
) -> dict:
    """
    当月分の回数割料金を計算

    Args:
        course: コース
        start_date: 開始日
        day_of_week: 曜日（1=月, 2=火, 3=水, 4=木, 5=金, 6=土, 7=日）

    Returns:
        {
            'tuition': {
                'product': Product,
                'full_price': int,       # 満額
                'prorated_price': int,   # 回数割後の金額
                'remaining_count': int,
                'total_count': int,
            },
            'facility_fee': {...},
            'monthly_fee': {...},
            'total_prorated': int,      # 当月分合計
        }
    """
    from apps.contracts.models import CourseItem

    result = {
        'tuition': None,
        'facility_fee': None,
        'monthly_fee': None,
        'total_prorated': 0,
    }

    if not course or not start_date or day_of_week is None:
        return result

    # 回数割比率を計算
    proration = calculate_prorated_by_day_of_week(start_date, day_of_week)

    # 月初なら回数割不要
    if proration['ratio'] >= Decimal('1'):
        return result

    # CourseItemから商品を取得
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

        # ProductPriceから入会月別料金を取得
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
            'product': product,
            'product_id': str(product.id),
            'product_name': product.product_name,
            'full_price': full_price_with_tax,
            'prorated_price': prorated_price,
            'remaining_count': proration['remaining_count'],
            'total_count': proration['total_count'],
            'ratio': float(proration['ratio']),
            'dates': [d.isoformat() for d in proration['dates']],
        }

        # 授業料
        if product.item_type == Product.ItemType.TUITION:
            result['tuition'] = fee_info
            result['total_prorated'] += prorated_price

        # 設備費
        elif product.item_type == Product.ItemType.FACILITY:
            result['facility_fee'] = fee_info
            result['total_prorated'] += prorated_price

        # 月会費
        elif product.item_type == Product.ItemType.MONTHLY_FEE:
            result['monthly_fee'] = fee_info
            result['total_prorated'] += prorated_price

    return result


def get_monthly_tuition_prices(course: Course, start_date: date) -> dict:
    """
    コースの月別授業料を取得

    ProductPrice（T05_商品料金）から入会月別料金と請求月別料金を取得して返す。
    締日20日基準で請求対象月を計算。

    Args:
        course: コース
        start_date: 開始日（入会日）

    Returns:
        {
            'tuitionProduct': Product or None,
            'month1': int (請求月1),
            'month2': int (請求月2),
            'month1Price': int (月1の授業料・税込),
            'month2Price': int (月2の授業料・税込),
            'facilityFee': int (設備費・税込),
            'monthlyFee': int (月会費・税込),
        }
    """
    from apps.contracts.models import CourseItem

    result = {
        'tuitionProduct': None,
        'month1': start_date.month,
        'month2': (start_date.month % 12) + 1,
        'month1Price': 0,
        'month2Price': 0,
        'facilityFee': 0,
        'monthlyFee': 0,
    }

    if not course:
        return result

    # 月謝は翌月から開始（当月分は回数割で別途計算）
    # month1 = 翌月（最初の満額月謝）
    # month2 = 翌々月以降（通常月謝）
    current_month = start_date.month
    result['month1'] = (current_month % 12) + 1  # 翌月
    result['month2'] = ((current_month + 1) % 12) + 1  # 翌々月

    # CourseItemから授業料商品を取得
    course_items = CourseItem.objects.filter(
        course=course,
        is_active=True
    ).select_related('product').prefetch_related('product__prices')

    for ci in course_items:
        product = ci.product
        if not product or not product.is_active:
            continue

        tax_rate = product.tax_rate or Decimal('0.1')

        # 授業料（tuition）
        if product.item_type == Product.ItemType.TUITION:
            result['tuitionProduct'] = product

            # ProductPriceから月別料金を取得
            try:
                product_price = product.prices.filter(is_active=True).first()
                if product_price:
                    # 月1は入会月別料金
                    price1 = product_price.get_enrollment_price(result['month1'])
                    if price1 is not None:
                        result['month1Price'] = int(Decimal(str(price1)) * (1 + tax_rate))
                    else:
                        base_price = product.base_price or Decimal('0')
                        result['month1Price'] = int(base_price * (1 + tax_rate))

                    # 月2は請求月別料金
                    price2 = product_price.get_billing_price(result['month2'])
                    if price2 is not None:
                        result['month2Price'] = int(Decimal(str(price2)) * (1 + tax_rate))
                    else:
                        base_price = product.base_price or Decimal('0')
                        result['month2Price'] = int(base_price * (1 + tax_rate))
                else:
                    # ProductPriceがない場合は基本価格
                    base_price = product.base_price or Decimal('0')
                    price_with_tax = int(base_price * (1 + tax_rate))
                    result['month1Price'] = price_with_tax
                    result['month2Price'] = price_with_tax
            except Exception as e:
                print(f"[get_monthly_tuition_prices] Error getting tuition price: {e}", file=sys.stderr)
                base_price = product.base_price or Decimal('0')
                price_with_tax = int(base_price * (1 + tax_rate))
                result['month1Price'] = price_with_tax
                result['month2Price'] = price_with_tax

        # 設備費
        elif product.item_type == Product.ItemType.FACILITY:
            base_price = product.base_price or Decimal('0')
            result['facilityFee'] = int(base_price * (1 + tax_rate))

        # 月会費
        elif product.item_type == Product.ItemType.MONTHLY_FEE:
            base_price = product.base_price or Decimal('0')
            result['monthlyFee'] = int(base_price * (1 + tax_rate))

    return result


class PricingPreviewView(APIView):
    """料金プレビュー"""
    permission_classes = [IsAuthenticated]

    def _extract_billing_months(self, product_name: str) -> list:
        """商品名から請求月を抽出

        例:
        - 「半年払い（4月・10月）」→ [4, 10]
        - 「月払い」→ [] (毎月)
        - 「（4月・8月・12月）」→ [4, 8, 12]
        """
        import re
        months = []
        # 「○月」のパターンを抽出
        pattern = r'(\d+)月'
        matches = re.findall(pattern, product_name)
        if matches:
            months = [int(m) for m in matches]
        return months

    def post(self, request):
        """
        料金のプレビューを返す
        """
        import logging
        logger = logging.getLogger(__name__)

        # djangorestframework-camel-case がリクエストのcamelCaseをsnake_caseに変換する
        student_id = request.data.get('student_id')
        product_ids = request.data.get('product_ids', [])
        course_id = request.data.get('course_id')
        start_date_str = request.data.get('start_date')  # 開始日（入会時授業料計算用）
        day_of_week = request.data.get('day_of_week')  # 曜日（1=月〜7=日）

        logger.warning(f"[PricingPreview] POST received - student_id={student_id}, course_id={course_id}")
        print(f"[PricingPreview] student_id={student_id}, course_id={course_id}, product_ids={product_ids}, start_date={start_date_str}, day_of_week={day_of_week}", file=sys.stderr, flush=True)

        items = []
        subtotal = Decimal('0')
        enrollment_tuition_item = None  # 入会時授業料

        # 生徒からマイル情報を取得
        student = None
        guardian = None
        mile_info = None
        if student_id:
            try:
                student = Student.objects.select_related('guardian').get(id=student_id)
                guardian = student.guardian
                if guardian:
                    mile_balance = MileTransaction.get_balance(guardian)
                    can_use = MileTransaction.can_use_miles(guardian)
                    max_discount = MileTransaction.calculate_discount(mile_balance) if can_use and mile_balance >= 4 else Decimal('0')
                    mile_info = {
                        'balance': mile_balance,
                        'canUse': can_use,
                        'maxDiscount': int(max_discount),
                        'reason': None if can_use else 'コース契約が2つ以上必要です',
                    }
                    print(f"[PricingPreview] Mile info: balance={mile_balance}, canUse={can_use}, maxDiscount={max_discount}", file=sys.stderr)
            except Student.DoesNotExist:
                pass

        # 開始日をパース
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # コースIDから料金を取得（Courseまたは Pack）
        course = None
        pack = None
        if course_id:
            # まずCourseを検索
            try:
                course = Course.objects.get(id=course_id)
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
                if start_date and start_date.day > 1:
                    tickets = calculate_enrollment_tuition_tickets(start_date)
                    enrollment_product = get_enrollment_tuition_product(course, tickets)

                    if enrollment_product:
                        # ProductPrice（T05）から入会月別料金を取得
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
                            'tickets': tickets,  # チケット枚数
                            'isEnrollmentTuition': True,
                        }
                        items.append(enrollment_tuition_item)
                        subtotal += enrollment_price
                        print(f"[PricingPreview] Added enrollment tuition: {enrollment_product.product_name}, tickets={tickets}, price={enrollment_price}", file=sys.stderr)
                    else:
                        print(f"[PricingPreview] No enrollment tuition product found for {tickets} tickets", file=sys.stderr)

            except Course.DoesNotExist:
                # Courseが見つからない場合はPackを検索
                try:
                    pack = Pack.objects.get(id=course_id)
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

                    # パック内のコースごとの入会時授業料を計算（月途中入会の場合）
                    if start_date and start_date.day > 1:
                        pack_courses = pack.pack_courses.filter(is_active=True).select_related('course')
                        for pack_course in pack_courses:
                            pc_course = pack_course.course
                            if pc_course:
                                tickets = calculate_enrollment_tuition_tickets(start_date)
                                enrollment_product = get_enrollment_tuition_product(pc_course, tickets)

                                if enrollment_product:
                                    # ProductPrice（T05）から入会月別料金を取得
                                    enrollment_price = get_product_price_for_enrollment(enrollment_product, start_date)
                                    enrollment_tuition_item = {
                                        'productId': str(enrollment_product.id),
                                        'productName': f'{pc_course.course_name} - {enrollment_product.product_name}',
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
                                    items.append(enrollment_tuition_item)
                                    subtotal += enrollment_price
                                    print(f"[PricingPreview] Added pack course enrollment tuition: {enrollment_product.product_name}, tickets={tickets}, price={enrollment_price}", file=sys.stderr)

                except Pack.DoesNotExist:
                    print(f"[PricingPreview] Neither Course nor Pack found for id={course_id}", file=sys.stderr)

        # 商品IDから料金を取得
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

        # 追加料金と割引を計算
        additional_fees = {}
        discounts = []
        discount_total = Decimal('0')

        # CourseItemからコースに紐づく商品を取得
        from apps.contracts.models import CourseItem, ProductSetItem

        # コース商品一覧（そのまま表示用）
        course_items_list = []

        # 月別料金グループ
        billing_by_month = {
            'enrollment': {'label': '入会時費用', 'items': [], 'total': 0},
            'currentMonth': {'label': '', 'month': 0, 'items': [], 'total': 0},
            'month1': {'label': '', 'month': 0, 'items': [], 'total': 0},
            'month2': {'label': '', 'month': 0, 'items': [], 'total': 0},
        }

        # 教材費の選択肢（月払い、半年払いなど）
        textbook_options = []

        if course:
            course_items = CourseItem.objects.filter(
                course=course,
                is_active=True
            ).select_related('product')
            print(f"[PricingPreview] CourseItems count: {course_items.count()}, ProductSet: {course.product_set}", file=sys.stderr, flush=True)

            # 商品セット（ProductSet）の商品も追加
            if course.product_set:
                set_items = ProductSetItem.objects.filter(
                    product_set=course.product_set,
                    is_active=True
                ).select_related('product')
                for si in set_items:
                    product = si.product
                    if not product or not product.is_active:
                        continue
                    base_price = product.base_price or Decimal('0')
                    tax_rate = product.tax_rate or Decimal('0.1')
                    tax_amount = int(base_price * tax_rate)
                    price_with_tax = int(base_price) + tax_amount
                    item_data = {
                        'productId': str(product.id),
                        'productName': product.product_name,
                        'billingCategoryName': product.get_item_type_display(),  # 請求カテゴリ名
                        'itemType': product.item_type,
                        'quantity': si.quantity,
                        'unitPrice': int(base_price),
                        'priceWithTax': price_with_tax,
                        'taxRate': float(tax_rate),
                        'source': 'product_set',
                    }
                    course_items_list.append(item_data)
                    subtotal += Decimal(str(price_with_tax))

                    # 月別グループに振り分け
                    item_type = product.item_type
                    print(f"[PricingPreview] ProductSet Product: {product.product_name}, item_type: '{item_type}'", file=sys.stderr, flush=True)
                    if item_type == 'textbook':
                        # 教材費は選択肢として別管理（月額から除外）
                        textbook_options.append({
                            'productId': str(product.id),
                            'productCode': product.product_code,
                            'productName': product.product_name,
                            'itemType': item_type,
                            'unitPrice': int(base_price),
                            'priceWithTax': price_with_tax,
                            'taxRate': float(tax_rate),
                            'paymentType': 'monthly' if '月払い' in product.product_name else 'semi_annual' if '半年払い' in product.product_name or '半期' in product.product_name else 'annual',
                            'billingMonths': self._extract_billing_months(product.product_name),
                            'source': 'product_set',
                        })
                        print(f"[PricingPreview]   -> Added to textbook_options (not included in monthly total)", file=sys.stderr)
                    elif item_type in ['enrollment', 'enrollment_textbook', 'bag']:
                        billing_by_month['enrollment']['items'].append(item_data.copy())
                        billing_by_month['enrollment']['total'] += price_with_tax
                        print(f"[PricingPreview]   -> Added to enrollment", file=sys.stderr)
                    elif item_type in ['enrollment_monthly_fee', 'enrollment_facility']:
                        # 当月分（月会費・設備費のみ）
                        billing_by_month['currentMonth']['items'].append(item_data.copy())
                        billing_by_month['currentMonth']['total'] += price_with_tax
                        print(f"[PricingPreview]   -> Added to currentMonth", file=sys.stderr)
                    elif item_type == 'enrollment_tuition':
                        # 当月分授業料バリエーションはスキップ
                        print(f"[PricingPreview]   -> Skipped (enrollment_tuition variant)", file=sys.stderr)
                    elif item_type in ['tuition', 'monthly_fee', 'facility']:
                        billing_by_month['month1']['items'].append(item_data.copy())
                        billing_by_month['month1']['total'] += price_with_tax
                        billing_by_month['month2']['items'].append(item_data.copy())
                        billing_by_month['month2']['total'] += price_with_tax
                        print(f"[PricingPreview]   -> Added to month1 and month2", file=sys.stderr)
                    else:
                        print(f"[PricingPreview]   -> NOT MATCHED (item_type not in any group)", file=sys.stderr)

            for ci in course_items:
                product = ci.product
                if not product or not product.is_active:
                    continue

                base_price = product.base_price or Decimal('0')
                tax_rate = product.tax_rate or Decimal('0.1')
                tax_amount = int(base_price * tax_rate)
                price_with_tax = int(base_price) + tax_amount  # 税込価格

                # コース商品一覧に追加（そのまま表示用）
                item_data = {
                    'productId': str(product.id),
                    'productName': product.product_name,
                    'billingCategoryName': product.get_item_type_display(),  # 請求カテゴリ名
                    'itemType': product.item_type,
                    'quantity': ci.quantity,
                    'unitPrice': int(base_price),
                    'priceWithTax': price_with_tax,
                    'taxRate': float(tax_rate),
                    'source': 'course_item',
                }
                course_items_list.append(item_data)

                # 月別グループに振り分け
                item_type = product.item_type
                print(f"[PricingPreview] Product: {product.product_name}, item_type: '{item_type}'", file=sys.stderr, flush=True)
                if item_type == 'textbook':
                    # 教材費は選択肢として別管理（月額から除外）
                    textbook_options.append({
                        'productId': str(product.id),
                        'productCode': product.product_code,
                        'productName': product.product_name,
                        'itemType': item_type,
                        'unitPrice': int(base_price),
                        'priceWithTax': price_with_tax,
                        'taxRate': float(tax_rate),
                        'paymentType': 'monthly' if '月払い' in product.product_name else 'semi_annual' if '半年払い' in product.product_name or '半期' in product.product_name else 'annual',
                        'billingMonths': self._extract_billing_months(product.product_name),
                        'source': 'course_item',
                    })
                    print(f"[PricingPreview]   -> Added to textbook_options (not included in monthly total)", file=sys.stderr)
                elif item_type in ['enrollment', 'enrollment_textbook', 'bag']:
                    # 入会時費用（一回のみ）
                    billing_by_month['enrollment']['items'].append(item_data)
                    billing_by_month['enrollment']['total'] += price_with_tax
                    print(f"[PricingPreview]   -> Added to enrollment", file=sys.stderr)
                elif item_type in ['enrollment_monthly_fee', 'enrollment_facility']:
                    # 当月分（月会費・設備費のみ）- enrollment_tuitionは後で計算したものを追加
                    billing_by_month['currentMonth']['items'].append(item_data)
                    billing_by_month['currentMonth']['total'] += price_with_tax
                    print(f"[PricingPreview]   -> Added to currentMonth", file=sys.stderr)
                elif item_type == 'enrollment_tuition':
                    # 当月分授業料バリエーションはスキップ（後で計算したものを追加）
                    print(f"[PricingPreview]   -> Skipped (enrollment_tuition variant)", file=sys.stderr)
                elif item_type in ['tuition', 'monthly_fee', 'facility']:
                    # 月額料金（翌月・翌々月）
                    billing_by_month['month1']['items'].append(item_data.copy())
                    billing_by_month['month1']['total'] += price_with_tax
                    billing_by_month['month2']['items'].append(item_data.copy())
                    billing_by_month['month2']['total'] += price_with_tax
                    print(f"[PricingPreview]   -> Added to month1 and month2", file=sys.stderr)
                else:
                    print(f"[PricingPreview]   -> NOT MATCHED (item_type not in any group)", file=sys.stderr)

                # 入会金
                if product.item_type == Product.ItemType.ENROLLMENT:
                    additional_fees['enrollmentFee'] = {
                        'productId': str(product.id),
                        'productName': product.product_name,
                        'price': price_with_tax,  # 税込
                        'priceExcludingTax': int(base_price),  # 税抜
                        'taxRate': float(tax_rate),
                        'taxAmount': tax_amount,
                    }
                    subtotal += Decimal(str(price_with_tax))

                # 設備費
                elif product.item_type == Product.ItemType.FACILITY:
                    additional_fees['facilityFee'] = {
                        'productId': str(product.id),
                        'productName': product.product_name,
                        'price': price_with_tax,  # 税込
                        'priceExcludingTax': int(base_price),  # 税抜
                        'taxRate': float(tax_rate),
                        'taxAmount': tax_amount,
                    }
                    subtotal += Decimal(str(price_with_tax))

                # 教材費（入会時）
                elif product.item_type == Product.ItemType.ENROLLMENT_TEXTBOOK:
                    additional_fees['materialsFee'] = {
                        'productId': str(product.id),
                        'productName': product.product_name,
                        'price': price_with_tax,  # 税込
                        'priceExcludingTax': int(base_price),  # 税抜
                        'taxRate': float(tax_rate),
                        'taxAmount': tax_amount,
                    }
                    subtotal += Decimal(str(price_with_tax))

                # 月会費
                elif product.item_type == Product.ItemType.MONTHLY_FEE:
                    additional_fees['monthlyFee'] = {
                        'productId': str(product.id),
                        'productName': product.product_name,
                        'price': price_with_tax,  # 税込
                        'priceExcludingTax': int(base_price),  # 税抜
                        'taxRate': float(tax_rate),
                        'taxAmount': tax_amount,
                    }
                    subtotal += Decimal(str(price_with_tax))

        # ========================================
        # 入会時費用の自動計算（新ロジック）
        # ========================================
        enrollment_fees_calculated = []
        if course and start_date and day_of_week:
            try:
                # 追加チケット数を計算（曜日ベース）
                dow_int = int(day_of_week) if day_of_week else None
                if dow_int and 1 <= dow_int <= 7:
                    prorated_info = calculate_prorated_by_day_of_week(start_date, dow_int)
                    additional_tickets = prorated_info['remaining_count']
                    total_classes_in_month = prorated_info['total_count']

                    print(f"[PricingPreview] Enrollment fees calculation: additional_tickets={additional_tickets}, total_classes={total_classes_in_month}", file=sys.stderr)

                    # 入会時費用を計算
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
                        if fee['calculated_price'] >= 0:  # ¥0のバッグも含める
                            tax_rate = Decimal('0.1')
                            tax_amount = int(Decimal(str(fee['calculated_price'])) * tax_rate)
                            price_with_tax = fee['calculated_price'] + tax_amount

                            item_data = {
                                'productId': fee['product_id'],
                                'productCode': fee['product_code'],
                                'productName': fee['product_name'],
                                'billingCategoryName': fee['product_name'].split('【')[1].split('】')[0] if '【' in fee['product_name'] else fee['item_type'],
                                'itemType': fee['item_type'],
                                'quantity': 1,
                                'unitPrice': fee['calculated_price'],
                                'priceWithTax': price_with_tax,
                                'taxRate': float(tax_rate),
                                'calculationDetail': fee['calculation_detail'],
                            }
                            billing_by_month['enrollment']['items'].append(item_data)
                            billing_by_month['enrollment']['total'] += price_with_tax

                            # additional_feesにも追加（既存のフロントエンド互換）
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

        # マイル割引の計算（兄弟全員の合計マイル数ベース）
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

        # 月別授業料を取得（ProductPriceから）
        monthly_tuition = None
        if course and start_date:
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

            # 月別料金グループのラベルを設定
            current_month = start_date.month
            billing_by_month['currentMonth']['label'] = f'{current_month}月分（当月）'
            billing_by_month['currentMonth']['month'] = current_month
            billing_by_month['month1']['label'] = f'{monthly_tuition["month1"]}月分'
            billing_by_month['month1']['month'] = monthly_tuition['month1']
            billing_by_month['month2']['label'] = f'{monthly_tuition["month2"]}月分〜'
            billing_by_month['month2']['month'] = monthly_tuition['month2']
        else:
            # start_dateがない場合のデフォルトラベル
            from datetime import date as date_type
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

        # 当月分の回数割料金を計算（曜日が指定された場合）
        current_month_prorated = None
        if course and start_date and day_of_week:
            try:
                dow_int = int(day_of_week) if day_of_week else None
                if dow_int and 1 <= dow_int <= 7:
                    prorated_data = calculate_prorated_current_month_fees(course, start_date, dow_int)
                    if prorated_data['total_prorated'] > 0:
                        current_month_prorated = {
                            'tuition': {
                                'productId': prorated_data['tuition']['product_id'],
                                'productName': prorated_data['tuition']['product_name'],
                                'fullPrice': prorated_data['tuition']['full_price'],
                                'proratedPrice': prorated_data['tuition']['prorated_price'],
                            } if prorated_data['tuition'] else None,
                            'facilityFee': {
                                'productId': prorated_data['facility_fee']['product_id'],
                                'productName': prorated_data['facility_fee']['product_name'],
                                'fullPrice': prorated_data['facility_fee']['full_price'],
                                'proratedPrice': prorated_data['facility_fee']['prorated_price'],
                            } if prorated_data['facility_fee'] else None,
                            'monthlyFee': {
                                'productId': prorated_data['monthly_fee']['product_id'],
                                'productName': prorated_data['monthly_fee']['product_name'],
                                'fullPrice': prorated_data['monthly_fee']['full_price'],
                                'proratedPrice': prorated_data['monthly_fee']['prorated_price'],
                            } if prorated_data['monthly_fee'] else None,
                            'totalProrated': prorated_data['total_prorated'],
                            'remainingCount': prorated_data['tuition']['remaining_count'] if prorated_data['tuition'] else 0,
                            'totalCount': prorated_data['tuition']['total_count'] if prorated_data['tuition'] else 0,
                            'ratio': prorated_data['tuition']['ratio'] if prorated_data['tuition'] else 0,
                            'dates': prorated_data['tuition']['dates'] if prorated_data['tuition'] else [],
                        }
                        print(f"[PricingPreview] Current month prorated: {current_month_prorated}", file=sys.stderr)
            except (ValueError, TypeError) as e:
                print(f"[PricingPreview] Error calculating prorated fees: {e}", file=sys.stderr)

        # grandTotalを正しく計算（表示項目に基づく）
        # = 追加チケット + 入会金 + 教材費 + (月1授業料+設備費+月会費) + (月2授業料+設備費+月会費) - 割引
        enrollment_tuition_total = enrollment_tuition_item['total'] if enrollment_tuition_item else 0
        enrollment_fee = additional_fees.get('enrollmentFee', {}).get('price', 0)
        materials_fee = additional_fees.get('materialsFee', {}).get('price', 0)

        if monthly_tuition:
            month1_total = monthly_tuition['month1Price'] + monthly_tuition['facilityFee'] + monthly_tuition['monthlyFee']
            month2_total = monthly_tuition['month2Price'] + monthly_tuition['facilityFee'] + monthly_tuition['monthlyFee']
        else:
            # フォールバック：従来の計算
            month1_total = additional_fees.get('facilityFee', {}).get('price', 0) + additional_fees.get('monthlyFee', {}).get('price', 0)
            month2_total = month1_total

        grand_total = (
            enrollment_tuition_total +
            enrollment_fee +
            materials_fee +
            month1_total +
            month2_total -
            int(discount_total)
        )

        # 入会時授業料（計算されたもの）をcurrentMonthに追加
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

        print(f"[PricingPreview] grandTotal calculation: enrollment_tuition={enrollment_tuition_total}, enrollment_fee={enrollment_fee}, materials_fee={materials_fee}, month1={month1_total}, month2={month2_total}, discount={discount_total}, total={grand_total}", file=sys.stderr)
        print(f"[PricingPreview] billingByMonth: enrollment={len(billing_by_month['enrollment']['items'])} items, currentMonth={len(billing_by_month['currentMonth']['items'])} items, month1={len(billing_by_month['month1']['items'])} items, month2={len(billing_by_month['month2']['items'])} items", file=sys.stderr)

        # 入会時費用の項目を0円で追加（項目がない場合）
        enrollment_item_types = [item.get('itemType') for item in billing_by_month['enrollment']['items']]

        # 入会金が含まれていない場合、0円で追加
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

        # 教材費が含まれていない場合、0円で追加
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

        # 教材費選択肢のログ
        print(f"[PricingPreview] textbookOptions: {len(textbook_options)} items", file=sys.stderr)
        for opt in textbook_options:
            print(f"[PricingPreview]   - {opt['productName']}: {opt['paymentType']}, ¥{opt['unitPrice']}, billing={opt['billingMonths']}", file=sys.stderr)

        return Response({
            'items': items,
            'subtotal': int(subtotal),  # 税込合計（参考値）
            'taxTotal': 0,  # 税込価格のため別途税額なし
            'discounts': discounts,
            'discountTotal': int(discount_total),
            'companyContribution': 0,
            'schoolContribution': 0,
            'grandTotal': grand_total,
            'enrollmentTuition': enrollment_tuition_item,  # 入会時授業料情報
            'additionalFees': additional_fees,  # 入会金、設備費、教材費
            'monthlyTuition': monthly_tuition,  # 月別授業料
            'currentMonthProrated': current_month_prorated,  # 当月分回数割料金
            'courseItems': course_items_list,  # コース商品一覧（そのまま表示用）
            'billingByMonth': billing_by_month,  # 月別料金グループ
            'mileInfo': mile_info,  # マイル情報
            'enrollmentFeesCalculated': enrollment_fees_calculated,  # 入会時費用計算結果
            'textbookOptions': textbook_options,  # 教材費選択肢（月払い/半年払いなど）
        })


class PricingConfirmView(APIView):
    """購入確定"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        購入を確定する
        - StudentItemを作成
        - Taskを作成（作業一覧に追加）
        """
        # djangorestframework-camel-case がリクエストのcamelCaseをsnake_caseに変換する
        preview_id = request.data.get('preview_id')
        payment_method = request.data.get('payment_method')
        student_id = request.data.get('student_id')
        course_id = request.data.get('course_id')
        # 購入時に選択した情報
        brand_id = request.data.get('brand_id')
        school_id = request.data.get('school_id')
        start_date_str = request.data.get('start_date')
        # スケジュール情報（曜日・時間帯）
        schedules = request.data.get('schedules', [])
        ticket_id = request.data.get('ticket_id')
        # マイル使用
        miles_to_use = request.data.get('miles_to_use', 0)
        if miles_to_use:
            miles_to_use = int(miles_to_use)
        # 選択された教材費（複数選択可能）
        selected_textbook_ids = request.data.get('selected_textbook_ids', [])

        print(f"[PricingConfirm] preview_id={preview_id}, student_id={student_id}, course_id={course_id}", file=sys.stderr)
        print(f"[PricingConfirm] brand_id={brand_id}, school_id={school_id}, start_date={start_date_str}", file=sys.stderr)
        print(f"[PricingConfirm] schedules={schedules}, ticket_id={ticket_id}, miles_to_use={miles_to_use}", file=sys.stderr)
        print(f"[PricingConfirm] selected_textbook_ids={selected_textbook_ids}", file=sys.stderr)

        # 注文IDを生成
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # 現在の請求月
        today = date.today()
        billing_month = today.strftime('%Y-%m')

        student = None
        course = None
        pack = None  # パック購入の場合
        brand = None
        school = None
        start_date = None

        # 生徒を取得（guardianも一緒に取得）
        guardian = None
        mile_discount = Decimal('0')
        if student_id:
            try:
                student = Student.objects.select_related('guardian').get(id=student_id)
                guardian = student.guardian
            except Student.DoesNotExist:
                pass

        # マイル使用のバリデーションと割引計算
        if miles_to_use > 0 and guardian:
            mile_balance = MileTransaction.get_balance(guardian)
            can_use = MileTransaction.can_use_miles(guardian)
            if not can_use:
                return Response({
                    'error': 'マイルを使用するにはコース契約が2つ以上必要です',
                }, status=400)
            if miles_to_use > mile_balance:
                return Response({
                    'error': f'マイル残高が不足しています（残高: {mile_balance}pt）',
                }, status=400)
            if miles_to_use < 4:
                return Response({
                    'error': 'マイルは4pt以上から使用できます',
                }, status=400)
            mile_discount = MileTransaction.calculate_discount(miles_to_use)
            print(f"[PricingConfirm] Mile discount: {miles_to_use}pt -> ¥{mile_discount}", file=sys.stderr)

        # コースを取得（Courseまたは Pack）
        if course_id:
            try:
                course = Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                # Courseが見つからない場合はPackを検索
                try:
                    pack = Pack.objects.get(id=course_id)
                    print(f"[PricingConfirm] Found pack: {pack.pack_name}", file=sys.stderr)
                except Pack.DoesNotExist:
                    pass

        # preview_idがコースIDの場合
        if not course and not pack and preview_id:
            try:
                course = Course.objects.get(id=preview_id)
            except Course.DoesNotExist:
                try:
                    pack = Pack.objects.get(id=preview_id)
                    print(f"[PricingConfirm] Found pack from preview_id: {pack.pack_name}", file=sys.stderr)
                except Pack.DoesNotExist:
                    pass

        # ブランドを取得
        if brand_id:
            try:
                brand = Brand.objects.get(id=brand_id)
            except Brand.DoesNotExist:
                pass

        # 校舎を取得
        if school_id:
            try:
                school = School.objects.get(id=school_id)
            except School.DoesNotExist:
                pass

        # 開始日をパース
        if start_date_str:
            try:
                from datetime import datetime
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # スケジュール情報から曜日・時間を抽出（最初のスケジュールを使用）
        schedule_day_of_week = None
        schedule_start_time = None
        schedule_end_time = None
        selected_class_schedule = None  # 選択されたClassSchedule
        if schedules and len(schedules) > 0:
            first_schedule = schedules[0]
            # ClassSchedule IDを取得
            class_schedule_id = first_schedule.get('id')
            if class_schedule_id:
                try:
                    selected_class_schedule = ClassSchedule.objects.get(id=class_schedule_id)
                    # ClassScheduleから曜日・時間を取得
                    schedule_day_of_week = selected_class_schedule.day_of_week
                    schedule_start_time = selected_class_schedule.start_time
                    schedule_end_time = selected_class_schedule.end_time
                    print(f"[PricingConfirm] Found ClassSchedule: {selected_class_schedule.class_name} (id={class_schedule_id})", file=sys.stderr)
                except ClassSchedule.DoesNotExist:
                    print(f"[PricingConfirm] ClassSchedule not found: id={class_schedule_id}", file=sys.stderr)

            # ClassScheduleが見つからない場合はフォールバック（フロントエンドから送信された情報を使用）
            if not selected_class_schedule:
                day_of_week_str = first_schedule.get('day_of_week', '')
                # 曜日名を数値に変換（月=1, 火=2, ... 日=7）- ClassScheduleと同じエンコーディング
                day_name_to_int = {'月曜日': 1, '火曜日': 2, '水曜日': 3, '木曜日': 4, '金曜日': 5, '土曜日': 6, '日曜日': 7}
                schedule_day_of_week = day_name_to_int.get(day_of_week_str)
                # 時間を解析
                start_time_str = first_schedule.get('start_time', '')
                end_time_str = first_schedule.get('end_time', '')
                try:
                    from datetime import time
                    if start_time_str:
                        parts = start_time_str.split(':')
                        schedule_start_time = time(int(parts[0]), int(parts[1]))
                    if end_time_str:
                        parts = end_time_str.split(':')
                        schedule_end_time = time(int(parts[0]), int(parts[1]))
                except (ValueError, IndexError):
                    pass
            print(f"[PricingConfirm] Parsed schedule: day_of_week={schedule_day_of_week}, start_time={schedule_start_time}, end_time={schedule_end_time}, class_schedule={selected_class_schedule}", file=sys.stderr)

        # チケットを取得（クラス予約の場合）
        ticket = None
        if ticket_id:
            try:
                from apps.schools.models import Ticket
                ticket = Ticket.objects.get(id=ticket_id)
                print(f"[PricingConfirm] Found ticket: {ticket.ticket_name}", file=sys.stderr)
            except Exception as e:
                print(f"[PricingConfirm] Failed to get ticket: {e}", file=sys.stderr)

        # StudentItemを作成（コースまたはパックの商品構成から）
        print(f"[PricingConfirm] student={student}, course={course}, pack={pack}, brand={brand}, school={school}, start_date={start_date}", file=sys.stderr)
        enrollment_tuition_info = None  # 入会時授業料情報（タスク表示用）
        created_student_items = []
        product_name_for_task = None  # タスク表示用のコース/パック名
        created_contract = None  # 作成した契約

        if student and course:
            # 契約を作成
            contract_no = f"C{date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            created_contract = Contract.objects.create(
                tenant_id=student.tenant_id,
                contract_no=contract_no,
                student=student,
                guardian=student.guardian if student.guardian else None,
                school=school,
                brand=brand,
                course=course,
                contract_date=date.today(),
                start_date=start_date or date.today(),
                status=Contract.Status.ACTIVE,
            )
            print(f"[PricingConfirm] Created Contract: {contract_no}", file=sys.stderr)
            # コースに紐づく商品を取得して StudentItem を作成
            course_items = course.course_items.filter(is_active=True)
            print(f"[PricingConfirm] Found {course_items.count()} course_items", file=sys.stderr)

            for course_item in course_items:
                product = course_item.product
                # 教材費（textbook）は除外（別途選択した教材費を登録）
                if product and product.item_type == 'textbook':
                    print(f"[PricingConfirm] Skipping textbook from CourseItem: {product.product_name}", file=sys.stderr)
                    continue

                unit_price = course_item.get_price()

                StudentItem.objects.create(
                    tenant_id=student.tenant_id,
                    student=student,
                    contract=created_contract,  # 契約をリンク
                    product=product,
                    billing_month=billing_month,
                    quantity=course_item.quantity,
                    unit_price=unit_price,
                    discount_amount=0,
                    final_price=unit_price * course_item.quantity,
                    notes=f'注文番号: {order_id} / コース: {course.course_name}',
                    # 購入時に選択した情報を保存
                    brand=brand,
                    school=school,
                    course=course,
                    start_date=start_date,
                    # 授業スケジュール
                    day_of_week=schedule_day_of_week,
                    start_time=schedule_start_time,
                    end_time=schedule_end_time,
                    class_schedule=selected_class_schedule,  # 選択されたクラス
                )

            # 選択された教材費のStudentItemを作成
            if selected_textbook_ids:
                for textbook_id in selected_textbook_ids:
                    try:
                        textbook_product = Product.objects.get(id=textbook_id)
                        unit_price = textbook_product.base_price or Decimal('0')

                        StudentItem.objects.create(
                            tenant_id=student.tenant_id,
                            student=student,
                            contract=created_contract,
                            product=textbook_product,
                            billing_month=billing_month,
                            quantity=1,
                            unit_price=unit_price,
                            discount_amount=0,
                            final_price=unit_price,
                            notes=f'注文番号: {order_id} / 教材費（選択）: {textbook_product.product_name}',
                            brand=brand,
                            school=school,
                            course=course,
                            start_date=start_date,
                            day_of_week=schedule_day_of_week,
                            start_time=schedule_start_time,
                            end_time=schedule_end_time,
                            class_schedule=selected_class_schedule,
                        )
                        print(f"[PricingConfirm] Created selected textbook StudentItem: {textbook_product.product_name} = ¥{unit_price}", file=sys.stderr)

                    except Product.DoesNotExist:
                        print(f"[PricingConfirm] Selected textbook not found: {textbook_id}", file=sys.stderr)

            # StudentSchool（生徒所属）を作成/更新
            # これにより、カレンダー表示時に生徒がどの校舎に通っているかがわかる
            if school and brand:
                student_school, ss_created = StudentSchool.objects.get_or_create(
                    tenant_id=student.tenant_id,
                    student=student,
                    school=school,
                    brand=brand,
                    defaults={
                        'enrollment_status': 'active',
                        'start_date': start_date or date.today(),
                        'is_primary': not StudentSchool.objects.filter(
                            student=student, is_primary=True
                        ).exists(),  # 最初の所属なら主所属に設定
                    }
                )
                if ss_created:
                    print(f"[PricingConfirm] Created StudentSchool: student={student}, school={school}, brand={brand}", file=sys.stderr)
                else:
                    print(f"[PricingConfirm] StudentSchool already exists: student={student}, school={school}, brand={brand}", file=sys.stderr)

            # StudentEnrollment（受講履歴）を作成
            # これにより、入会・クラス変更・曜日変更の履歴が追跡できる
            if school and brand:
                enrollment = StudentEnrollment.create_enrollment(
                    student=student,
                    school=school,
                    brand=brand,
                    class_schedule=selected_class_schedule,  # schedulesから取得したClassScheduleを使用
                    change_type=StudentEnrollment.ChangeType.NEW_ENROLLMENT,
                    effective_date=start_date or date.today(),
                    notes=f'注文番号: {order_id} / コース: {course.course_name}',
                    # フロントエンドから送信されたスケジュール情報
                    day_of_week_override=schedule_day_of_week,
                    start_time_override=schedule_start_time,
                    end_time_override=schedule_end_time,
                )
                print(f"[PricingConfirm] Created StudentEnrollment: student={student}, school={school}, brand={brand}, class_schedule={selected_class_schedule}", file=sys.stderr)

                # 生徒のステータスを「入会」に更新（体験・登録のみの場合）
                if student.status in [Student.Status.REGISTERED, Student.Status.TRIAL]:
                    student.status = Student.Status.ENROLLED
                    student.save(update_fields=['status', 'updated_at'])
                    print(f"[PricingConfirm] Updated student status to ENROLLED: {student}", file=sys.stderr)

            # ========================================
            # 入会時費用を自動計算してStudentItemに追加（新ロジック）
            # ========================================
            if start_date and schedule_day_of_week:
                try:
                    # 追加チケット数を計算
                    prorated_info = calculate_prorated_by_day_of_week(start_date, schedule_day_of_week)
                    additional_tickets = prorated_info['remaining_count']
                    total_classes_in_month = prorated_info['total_count']

                    # 入会時費用を計算
                    enrollment_fees = calculate_enrollment_fees(
                        course=course,
                        tenant_id=str(student.tenant_id),
                        enrollment_date=start_date,
                        additional_tickets=additional_tickets,
                        total_classes_in_month=total_classes_in_month,
                        student=student,
                        guardian=guardian,
                    )

                    # 各入会時費用のStudentItemを作成
                    for fee in enrollment_fees:
                        if fee['calculated_price'] >= 0:  # ¥0のバッグも含める
                            # 商品を取得
                            try:
                                product = Product.objects.get(id=fee['product_id'])
                            except Product.DoesNotExist:
                                print(f"[PricingConfirm] Product not found: {fee['product_id']}", file=sys.stderr)
                                continue

                            StudentItem.objects.create(
                                tenant_id=student.tenant_id,
                                student=student,
                                contract=created_contract,
                                product=product,
                                billing_month=billing_month,
                                quantity=1,
                                unit_price=fee['calculated_price'],
                                discount_amount=0,
                                final_price=fee['calculated_price'],
                                notes=f'注文番号: {order_id} / {fee["calculation_detail"]}',
                                brand=brand,
                                school=school,
                                course=course,
                                start_date=start_date,
                                day_of_week=schedule_day_of_week,
                                start_time=schedule_start_time,
                                end_time=schedule_end_time,
                                class_schedule=selected_class_schedule,
                            )
                            print(f"[PricingConfirm] Created enrollment StudentItem: {fee['item_type']} = ¥{fee['calculated_price']}", file=sys.stderr)

                            # 入会時授業料情報（タスク表示用）
                            if fee['item_type'] == 'enrollment_tuition':
                                enrollment_tuition_info = f"{fee['product_name']} ¥{fee['calculated_price']:,}"

                except Exception as e:
                    print(f"[PricingConfirm] Error creating enrollment fees: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()

            # 当月分の回数割料金をStudentItemに追加（曜日が指定された場合）
            current_month_prorated_info = None
            if start_date and schedule_day_of_week and start_date.day > 1:
                prorated_data = calculate_prorated_current_month_fees(course, start_date, schedule_day_of_week)
                if prorated_data['total_prorated'] > 0:
                    prorated_items = []
                    # 授業料（回数割）
                    if prorated_data['tuition']:
                        StudentItem.objects.create(
                            tenant_id=student.tenant_id,
                            student=student,
                            contract=created_contract,
                            product=prorated_data['tuition']['product'],
                            billing_month=billing_month,
                            quantity=1,
                            unit_price=prorated_data['tuition']['prorated_price'],
                            discount_amount=0,
                            final_price=prorated_data['tuition']['prorated_price'],
                            notes=f'注文番号: {order_id} / 当月分授業料（回数割 {prorated_data["tuition"]["remaining_count"]}/{prorated_data["tuition"]["total_count"]}回）',
                            brand=brand,
                            school=school,
                            course=course,
                            start_date=start_date,
                            day_of_week=schedule_day_of_week,
                            start_time=schedule_start_time,
                            end_time=schedule_end_time,
                            class_schedule=selected_class_schedule,
                        )
                        prorated_items.append(f'授業料 ¥{prorated_data["tuition"]["prorated_price"]:,}')
                        print(f"[PricingConfirm] Created prorated tuition StudentItem: ¥{prorated_data['tuition']['prorated_price']}", file=sys.stderr)

                    # 設備費（回数割）
                    if prorated_data['facility_fee']:
                        StudentItem.objects.create(
                            tenant_id=student.tenant_id,
                            student=student,
                            contract=created_contract,
                            product=prorated_data['facility_fee']['product'],
                            billing_month=billing_month,
                            quantity=1,
                            unit_price=prorated_data['facility_fee']['prorated_price'],
                            discount_amount=0,
                            final_price=prorated_data['facility_fee']['prorated_price'],
                            notes=f'注文番号: {order_id} / 当月分設備費（回数割 {prorated_data["facility_fee"]["remaining_count"]}/{prorated_data["facility_fee"]["total_count"]}回）',
                            brand=brand,
                            school=school,
                            course=course,
                            start_date=start_date,
                            day_of_week=schedule_day_of_week,
                            start_time=schedule_start_time,
                            end_time=schedule_end_time,
                            class_schedule=selected_class_schedule,
                        )
                        prorated_items.append(f'設備費 ¥{prorated_data["facility_fee"]["prorated_price"]:,}')
                        print(f"[PricingConfirm] Created prorated facility fee StudentItem: ¥{prorated_data['facility_fee']['prorated_price']}", file=sys.stderr)

                    # 月会費（回数割）
                    if prorated_data['monthly_fee']:
                        StudentItem.objects.create(
                            tenant_id=student.tenant_id,
                            student=student,
                            contract=created_contract,
                            product=prorated_data['monthly_fee']['product'],
                            billing_month=billing_month,
                            quantity=1,
                            unit_price=prorated_data['monthly_fee']['prorated_price'],
                            discount_amount=0,
                            final_price=prorated_data['monthly_fee']['prorated_price'],
                            notes=f'注文番号: {order_id} / 当月分月会費（回数割 {prorated_data["monthly_fee"]["remaining_count"]}/{prorated_data["monthly_fee"]["total_count"]}回）',
                            brand=brand,
                            school=school,
                            course=course,
                            start_date=start_date,
                            day_of_week=schedule_day_of_week,
                            start_time=schedule_start_time,
                            end_time=schedule_end_time,
                            class_schedule=selected_class_schedule,
                        )
                        prorated_items.append(f'月会費 ¥{prorated_data["monthly_fee"]["prorated_price"]:,}')
                        print(f"[PricingConfirm] Created prorated monthly fee StudentItem: ¥{prorated_data['monthly_fee']['prorated_price']}", file=sys.stderr)

                    if prorated_items:
                        current_month_prorated_info = ' / '.join(prorated_items) + f' (合計 ¥{prorated_data["total_prorated"]:,})'

            # Taskを作成（作業一覧に追加）
            student_name = f'{student.last_name}{student.first_name}'
            task_description = f'保護者からの購入申請です。\n\n' \
                              f'生徒: {student_name}\n' \
                              f'コース: {course.course_name}\n' \
                              f'注文番号: {order_id}\n' \
                              f'支払方法: {payment_method or "未指定"}\n' \
                              f'請求月: {billing_month}'

            # 入会時授業料がある場合は追加
            if enrollment_tuition_info:
                task_description += f'\n入会時授業料: {enrollment_tuition_info}'

            # 当月分回数割料金がある場合は追加
            if current_month_prorated_info:
                task_description += f'\n当月分回数割: {current_month_prorated_info}'

            # マイル割引がある場合は追加
            if mile_discount > 0:
                task_description += f'\nマイル割引: {miles_to_use}pt使用 → ¥{int(mile_discount):,}引'

            Task.objects.create(
                tenant_id=student.tenant_id,
                task_type='request',
                title=f'【購入申請】{student_name} - {course.course_name}',
                description=task_description,
                status='new',
                priority='normal',
                student=student,
                guardian=student.guardian if hasattr(student, 'guardian') else None,
                school=course.school if hasattr(course, 'school') else None,
                brand=course.brand if hasattr(course, 'brand') else None,
                source_type='purchase',
                source_id=uuid.UUID(order_id.replace('ORD-', '').ljust(32, '0')[:32]) if len(order_id) > 4 else None,
                metadata={
                    'order_id': order_id,
                    'course_id': str(course.id),
                    'student_id': str(student.id),
                    'payment_method': payment_method,
                    'billing_month': billing_month,
                    'enrollment_tuition': enrollment_tuition_info,
                    'current_month_prorated': current_month_prorated_info,
                    'miles_used': miles_to_use if mile_discount > 0 else 0,
                    'mile_discount': int(mile_discount) if mile_discount > 0 else 0,
                },
            )
            product_name_for_task = course.course_name

        # パック購入の場合
        elif student and pack:
            # 契約を作成
            contract_no = f"C{date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            created_contract = Contract.objects.create(
                tenant_id=student.tenant_id,
                contract_no=contract_no,
                student=student,
                guardian=student.guardian if student.guardian else None,
                school=school,
                brand=brand,
                course=None,  # パックの場合はコースなし
                contract_date=date.today(),
                start_date=start_date or date.today(),
                status=Contract.Status.ACTIVE,
            )
            print(f"[PricingConfirm] Created Contract for Pack: {contract_no}", file=sys.stderr)

            # パック内のコースをすべて処理
            pack_courses = pack.pack_courses.filter(is_active=True).select_related('course')
            print(f"[PricingConfirm] Found pack with {pack_courses.count()} courses", file=sys.stderr)

            for pack_course in pack_courses:
                pc_course = pack_course.course
                if not pc_course:
                    continue

                # コースに紐づく商品を取得して StudentItem を作成
                course_items = pc_course.course_items.filter(is_active=True)
                for course_item in course_items:
                    product = course_item.product
                    unit_price = course_item.get_price()

                    StudentItem.objects.create(
                        tenant_id=student.tenant_id,
                        student=student,
                        contract=created_contract,  # 契約をリンク
                        product=product,
                        billing_month=billing_month,
                        quantity=course_item.quantity,
                        unit_price=unit_price,
                        discount_amount=0,
                        final_price=unit_price * course_item.quantity,
                        notes=f'注文番号: {order_id} / パック: {pack.pack_name} / コース: {pc_course.course_name}',
                        brand=brand or pc_course.brand,
                        school=school or pc_course.school,
                        course=pc_course,
                        start_date=start_date,
                        day_of_week=schedule_day_of_week,
                        start_time=schedule_start_time,
                        end_time=schedule_end_time,
                        class_schedule=selected_class_schedule,
                    )

                # 入会時授業料（追加チケット）
                if start_date and start_date.day > 1:
                    tickets = calculate_enrollment_tuition_tickets(start_date)
                    enrollment_product = get_enrollment_tuition_product(pc_course, tickets)

                    if enrollment_product:
                        # ProductPrice（T05）から入会月別料金を取得
                        enrollment_price = get_product_price_for_enrollment(enrollment_product, start_date)
                        StudentItem.objects.create(
                            tenant_id=student.tenant_id,
                            student=student,
                            contract=created_contract,  # 契約をリンク
                            product=enrollment_product,
                            billing_month=billing_month,
                            quantity=1,
                            unit_price=enrollment_price,
                            discount_amount=0,
                            final_price=enrollment_price,
                            notes=f'注文番号: {order_id} / 入会時授業料（{tickets}回分）/ コース: {pc_course.course_name}',
                            brand=brand or pc_course.brand,
                            school=school or pc_course.school,
                            course=pc_course,
                            start_date=start_date,
                        )
                        if enrollment_tuition_info:
                            enrollment_tuition_info += f' / {enrollment_product.product_name} ¥{int(enrollment_price):,}'
                        else:
                            enrollment_tuition_info = f'{enrollment_product.product_name} ¥{int(enrollment_price):,}'

            # パック直接商品（PackItem）を処理
            pack_items = pack.pack_items.filter(is_active=True).select_related('product')
            for pack_item in pack_items:
                product = pack_item.product
                unit_price = pack_item.get_price()

                StudentItem.objects.create(
                    tenant_id=student.tenant_id,
                    student=student,
                    contract=created_contract,  # 契約をリンク
                    product=product,
                    billing_month=billing_month,
                    quantity=pack_item.quantity,
                    unit_price=unit_price,
                    discount_amount=0,
                    final_price=unit_price * pack_item.quantity,
                    notes=f'注文番号: {order_id} / パック: {pack.pack_name}',
                    brand=brand or pack.brand,
                    school=school or pack.school,
                    start_date=start_date,
                )

            # StudentSchool（生徒所属）を作成/更新
            use_brand = brand or pack.brand
            use_school = school or pack.school
            if use_school and use_brand:
                student_school, ss_created = StudentSchool.objects.get_or_create(
                    tenant_id=student.tenant_id,
                    student=student,
                    school=use_school,
                    brand=use_brand,
                    defaults={
                        'enrollment_status': 'active',
                        'start_date': start_date or date.today(),
                        'is_primary': not StudentSchool.objects.filter(
                            student=student, is_primary=True
                        ).exists(),
                    }
                )
                if ss_created:
                    print(f"[PricingConfirm] Created StudentSchool for pack: student={student}, school={use_school}, brand={use_brand}", file=sys.stderr)

            # StudentEnrollment（受講履歴）を作成
            if use_school and use_brand:
                enrollment = StudentEnrollment.create_enrollment(
                    student=student,
                    school=use_school,
                    brand=use_brand,
                    class_schedule=selected_class_schedule,
                    change_type=StudentEnrollment.ChangeType.NEW_ENROLLMENT,
                    effective_date=start_date or date.today(),
                    notes=f'注文番号: {order_id} / パック: {pack.pack_name}',
                    day_of_week_override=schedule_day_of_week,
                    start_time_override=schedule_start_time,
                    end_time_override=schedule_end_time,
                )
                print(f"[PricingConfirm] Created StudentEnrollment for pack: student={student}, school={use_school}, brand={use_brand}", file=sys.stderr)

                # 生徒のステータスを「入会」に更新
                if student.status in [Student.Status.REGISTERED, Student.Status.TRIAL]:
                    student.status = Student.Status.ENROLLED
                    student.save(update_fields=['status', 'updated_at'])
                    print(f"[PricingConfirm] Updated student status to ENROLLED: {student}", file=sys.stderr)

            # Taskを作成
            student_name = f'{student.last_name}{student.first_name}'
            task_description = f'保護者からの購入申請です。\n\n' \
                              f'生徒: {student_name}\n' \
                              f'パック: {pack.pack_name}\n' \
                              f'注文番号: {order_id}\n' \
                              f'支払方法: {payment_method or "未指定"}\n' \
                              f'請求月: {billing_month}'

            if enrollment_tuition_info:
                task_description += f'\n入会時授業料: {enrollment_tuition_info}'

            if mile_discount > 0:
                task_description += f'\nマイル割引: {miles_to_use}pt使用 → ¥{int(mile_discount):,}引'

            Task.objects.create(
                tenant_id=student.tenant_id,
                task_type='request',
                title=f'【購入申請】{student_name} - {pack.pack_name}',
                description=task_description,
                status='new',
                priority='normal',
                student=student,
                guardian=student.guardian if hasattr(student, 'guardian') else None,
                school=use_school,
                brand=use_brand,
                source_type='purchase',
                source_id=uuid.UUID(order_id.replace('ORD-', '').ljust(32, '0')[:32]) if len(order_id) > 4 else None,
                metadata={
                    'order_id': order_id,
                    'pack_id': str(pack.id),
                    'student_id': str(student.id),
                    'payment_method': payment_method,
                    'billing_month': billing_month,
                    'enrollment_tuition': enrollment_tuition_info,
                    'miles_used': miles_to_use if mile_discount > 0 else 0,
                    'mile_discount': int(mile_discount) if mile_discount > 0 else 0,
                },
            )
            product_name_for_task = pack.pack_name

        # マイル使用の記録
        if miles_to_use > 0 and mile_discount > 0 and guardian and student:
            current_balance = MileTransaction.get_balance(guardian)
            new_balance = current_balance - miles_to_use
            product_name = product_name_for_task or (course.course_name if course else (pack.pack_name if pack else "不明"))
            MileTransaction.objects.create(
                tenant_id=student.tenant_id,
                guardian=guardian,
                transaction_type=MileTransaction.TransactionType.USE,
                miles=-miles_to_use,
                balance_after=new_balance,
                discount_amount=mile_discount,
                notes=f'注文番号: {order_id} / {product_name}',
            )
            print(f"[PricingConfirm] Created MileTransaction: -{miles_to_use}pt, discount=¥{mile_discount}, new_balance={new_balance}", file=sys.stderr)

        return Response({
            'orderId': order_id,
            'status': 'completed',
            'message': '購入申請が完了しました。確認後、ご連絡いたします。',
            'mileDiscount': int(mile_discount) if mile_discount > 0 else 0,
            'milesUsed': miles_to_use if mile_discount > 0 else 0,
        })

"""
Pricing Utils - 料金計算ヘルパー関数
"""
import sys
from datetime import date, timedelta
from decimal import Decimal
from calendar import monthrange

from apps.contracts.models import Course, Product, ProductPrice


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


def calculate_prorated_by_multiple_days(start_date: date, days_of_week: list) -> dict:
    """
    複数曜日での回数割計算

    Args:
        start_date: 開始日
        days_of_week: 曜日のリスト（1=月, 2=火, 3=水, 4=木, 5=金, 6=土, 7=日）

    Returns:
        {
            'remaining_count': int,  # 開始日から月末までの合計回数
            'total_count': int,      # 月全体の合計回数
            'ratio': Decimal,        # 比率（remaining / total）
            'dates': list[date],     # 対象日のリスト
        }
    """
    if not start_date or not days_of_week:
        return {
            'remaining_count': 0,
            'total_count': 0,
            'ratio': Decimal('0'),
            'dates': [],
        }

    total_remaining = 0
    total_count = 0
    all_dates = []

    for day_of_week in days_of_week:
        try:
            dow_int = int(day_of_week) if day_of_week else None
            if dow_int and 1 <= dow_int <= 7:
                proration = calculate_prorated_by_day_of_week(start_date, dow_int)
                total_remaining += proration['remaining_count']
                total_count += proration['total_count']
                all_dates.extend(proration['dates'])
        except (ValueError, TypeError):
            continue

    ratio = Decimal(str(total_remaining)) / Decimal(str(total_count)) if total_count > 0 else Decimal('0')

    return {
        'remaining_count': total_remaining,
        'total_count': total_count,
        'ratio': ratio,
        'dates': sorted(all_dates),
    }


def calculate_prorated_current_month_fees_multiple(
    course: Course,
    start_date: date,
    days_of_week: list
) -> dict:
    """
    複数曜日での当月分回数割料金を計算

    Args:
        course: コース
        start_date: 開始日
        days_of_week: 曜日のリスト（1=月, 2=火, 3=水, 4=木, 5=金, 6=土, 7=日）

    Returns:
        calculate_prorated_current_month_feesと同じ形式
    """
    from apps.contracts.models import CourseItem

    result = {
        'tuition': None,
        'facility_fee': None,
        'monthly_fee': None,
        'total_prorated': 0,
    }

    if not course or not start_date or not days_of_week:
        return result

    # 複数曜日での回数割比率を計算
    proration = calculate_prorated_by_multiple_days(start_date, days_of_week)

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

    # CourseItemsに設備費・月会費がない場合、ブランドレベルにフォールバック
    brand = course.brand
    if brand and course.tenant_id:
        # 設備費のフォールバック
        if result['facility_fee'] is None:
            facility_product = Product.objects.filter(
                tenant_id=course.tenant_id,
                brand=brand,
                item_type=Product.ItemType.FACILITY,
                is_active=True,
                deleted_at__isnull=True
            ).first()
            if facility_product:
                tax_rate = facility_product.tax_rate or Decimal('0.1')
                base_price = facility_product.base_price or Decimal('0')
                full_price_with_tax = int(base_price * (1 + tax_rate))
                prorated_price = int(Decimal(str(full_price_with_tax)) * proration['ratio'])
                result['facility_fee'] = {
                    'product': facility_product,
                    'product_id': str(facility_product.id),
                    'product_name': facility_product.product_name,
                    'full_price': full_price_with_tax,
                    'prorated_price': prorated_price,
                    'remaining_count': proration['remaining_count'],
                    'total_count': proration['total_count'],
                    'ratio': float(proration['ratio']),
                    'dates': [d.isoformat() for d in proration['dates']],
                }
                result['total_prorated'] += prorated_price

        # 月会費のフォールバック
        if result['monthly_fee'] is None:
            monthly_product = Product.objects.filter(
                tenant_id=course.tenant_id,
                brand=brand,
                item_type=Product.ItemType.MONTHLY_FEE,
                is_active=True,
                deleted_at__isnull=True
            ).first()
            if monthly_product:
                tax_rate = monthly_product.tax_rate or Decimal('0.1')
                base_price = monthly_product.base_price or Decimal('0')
                full_price_with_tax = int(base_price * (1 + tax_rate))
                prorated_price = int(Decimal(str(full_price_with_tax)) * proration['ratio'])
                result['monthly_fee'] = {
                    'product': monthly_product,
                    'product_id': str(monthly_product.id),
                    'product_name': monthly_product.product_name,
                    'full_price': full_price_with_tax,
                    'prorated_price': prorated_price,
                    'remaining_count': proration['remaining_count'],
                    'total_count': proration['total_count'],
                    'ratio': float(proration['ratio']),
                    'dates': [d.isoformat() for d in proration['dates']],
                }
                result['total_prorated'] += prorated_price

    return result


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

    # CourseItemsに設備費・月会費がない場合、ブランドレベルにフォールバック
    brand = course.brand
    if brand and course.tenant_id:
        # 設備費のフォールバック
        if result['facility_fee'] is None:
            facility_product = Product.objects.filter(
                tenant_id=course.tenant_id,
                brand=brand,
                item_type=Product.ItemType.FACILITY,
                is_active=True,
                deleted_at__isnull=True
            ).first()
            if facility_product:
                tax_rate = facility_product.tax_rate or Decimal('0.1')
                base_price = facility_product.base_price or Decimal('0')
                full_price_with_tax = int(base_price * (1 + tax_rate))
                prorated_price = int(Decimal(str(full_price_with_tax)) * proration['ratio'])
                result['facility_fee'] = {
                    'product': facility_product,
                    'product_id': str(facility_product.id),
                    'product_name': facility_product.product_name,
                    'full_price': full_price_with_tax,
                    'prorated_price': prorated_price,
                    'remaining_count': proration['remaining_count'],
                    'total_count': proration['total_count'],
                    'ratio': float(proration['ratio']),
                    'dates': [d.isoformat() for d in proration['dates']],
                }
                result['total_prorated'] += prorated_price
                print(f"[calculate_prorated] Added brand-level facility fee: ¥{prorated_price}", file=sys.stderr)

        # 月会費のフォールバック
        if result['monthly_fee'] is None:
            monthly_product = Product.objects.filter(
                tenant_id=course.tenant_id,
                brand=brand,
                item_type=Product.ItemType.MONTHLY_FEE,
                is_active=True,
                deleted_at__isnull=True
            ).first()
            if monthly_product:
                tax_rate = monthly_product.tax_rate or Decimal('0.1')
                base_price = monthly_product.base_price or Decimal('0')
                full_price_with_tax = int(base_price * (1 + tax_rate))
                prorated_price = int(Decimal(str(full_price_with_tax)) * proration['ratio'])
                result['monthly_fee'] = {
                    'product': monthly_product,
                    'product_id': str(monthly_product.id),
                    'product_name': monthly_product.product_name,
                    'full_price': full_price_with_tax,
                    'prorated_price': prorated_price,
                    'remaining_count': proration['remaining_count'],
                    'total_count': proration['total_count'],
                    'ratio': float(proration['ratio']),
                    'dates': [d.isoformat() for d in proration['dates']],
                }
                result['total_prorated'] += prorated_price
                print(f"[calculate_prorated] Added brand-level monthly fee: ¥{prorated_price}", file=sys.stderr)

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

    # CourseItemsに設備費・月会費がない場合、ブランドレベルにフォールバック
    brand = course.brand
    if brand and course.tenant_id:
        # 設備費のフォールバック
        if result['facilityFee'] == 0:
            facility_product = Product.objects.filter(
                tenant_id=course.tenant_id,
                brand=brand,
                item_type=Product.ItemType.FACILITY,
                is_active=True,
                deleted_at__isnull=True
            ).first()
            if facility_product:
                tax_rate = facility_product.tax_rate or Decimal('0.1')
                base_price = facility_product.base_price or Decimal('0')
                result['facilityFee'] = int(base_price * (1 + tax_rate))
                print(f"[get_monthly_tuition_prices] Added brand-level facility fee: {facility_product.product_name} = ¥{result['facilityFee']}", file=sys.stderr)

        # 月会費のフォールバック
        if result['monthlyFee'] == 0:
            monthly_product = Product.objects.filter(
                tenant_id=course.tenant_id,
                brand=brand,
                item_type=Product.ItemType.MONTHLY_FEE,
                is_active=True,
                deleted_at__isnull=True
            ).first()
            if monthly_product:
                tax_rate = monthly_product.tax_rate or Decimal('0.1')
                base_price = monthly_product.base_price or Decimal('0')
                result['monthlyFee'] = int(base_price * (1 + tax_rate))
                print(f"[get_monthly_tuition_prices] Added brand-level monthly fee: {monthly_product.product_name} = ¥{result['monthlyFee']}", file=sys.stderr)

    return result

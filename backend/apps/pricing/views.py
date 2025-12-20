"""
Pricing views - 料金計算・購入確認API
"""
import sys
import uuid
from datetime import date, datetime
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

    # 締日基準で請求月を計算（締日20日）
    current_month = start_date.month
    day = start_date.day
    is_after_closing = day > 20

    if is_after_closing:
        # 締日以降：翌月と翌々月
        result['month1'] = (current_month % 12) + 1
        result['month2'] = ((current_month + 1) % 12) + 1
    else:
        # 締日以前：当月と翌月
        result['month1'] = current_month
        result['month2'] = (current_month % 12) + 1

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

        logger.warning(f"[PricingPreview] POST received - student_id={student_id}, course_id={course_id}")
        print(f"[PricingPreview] student_id={student_id}, course_id={course_id}, product_ids={product_ids}, start_date={start_date_str}", file=sys.stderr, flush=True)

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
        from apps.contracts.models import CourseItem

        if course:
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
                price_with_tax = int(base_price) + tax_amount  # 税込価格

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

        print(f"[PricingPreview] grandTotal calculation: enrollment_tuition={enrollment_tuition_total}, enrollment_fee={enrollment_fee}, materials_fee={materials_fee}, month1={month1_total}, month2={month2_total}, discount={discount_total}, total={grand_total}", file=sys.stderr)

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
            'mileInfo': mile_info,  # マイル情報
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

        print(f"[PricingConfirm] preview_id={preview_id}, student_id={student_id}, course_id={course_id}", file=sys.stderr)
        print(f"[PricingConfirm] brand_id={brand_id}, school_id={school_id}, start_date={start_date_str}", file=sys.stderr)
        print(f"[PricingConfirm] schedules={schedules}, ticket_id={ticket_id}, miles_to_use={miles_to_use}", file=sys.stderr)

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
                guardian=student.guardians.first() if student.guardians.exists() else None,
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

            # 入会時授業料（追加チケット）を計算してStudentItemに追加
            if start_date and start_date.day > 1:
                tickets = calculate_enrollment_tuition_tickets(start_date)
                enrollment_product = get_enrollment_tuition_product(course, tickets)

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
                        notes=f'注文番号: {order_id} / 入会時授業料（{tickets}回分）',
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
                    enrollment_tuition_info = f'{enrollment_product.product_name} ¥{int(enrollment_price):,}'
                    print(f"[PricingConfirm] Created enrollment tuition StudentItem: {enrollment_product.product_name}, price={enrollment_price}", file=sys.stderr)

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
                guardian=student.guardians.first() if student.guardians.exists() else None,
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

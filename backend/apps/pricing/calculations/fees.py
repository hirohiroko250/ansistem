"""
Fee Calculation Functions - 料金計算関数
"""
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any

from apps.contracts.models import Course, Product
from apps.students.models import Student, Guardian
from .status import has_guardian_paid_enrollment_fee, has_student_received_bag
from .products import get_enrollment_products_for_course


def calculate_enrollment_fees(
    course: Course,
    tenant_id: str,
    enrollment_date: date,
    additional_tickets: int,
    total_classes_in_month: int = 4,
    student: 'Student' = None,
    guardian: 'Guardian' = None,
) -> List[Dict[str, Any]]:
    """入会時費用を計算

    計算ロジック:
    - 入会金: そのまま（世帯で1回のみ - 2回目以降は請求しない）
    - 入会時授業料: 単価(per_ticket_price) × 追加チケット数
    - 入会時月会費: 月会費 ÷ 月内授業回数 × 追加チケット数
    - 入会時設備費: 設備費 ÷ 月内授業回数 × 追加チケット数
    - 入会時教材費: enrollment_price_*（入会月に応じた傾斜料金）
    - バッグ: 初回のみ（2回目以降は請求しない）

    Args:
        course: コース
        tenant_id: テナントID
        enrollment_date: 入会日
        additional_tickets: 追加チケット数
        total_classes_in_month: 月内の総授業回数（デフォルト4回）
        student: 生徒（バッグ重複チェック用）
        guardian: 保護者（入会金重複チェック用）

    Returns:
        入会時費用のリスト
        [{
            'product_id': str,
            'product_code': str,
            'product_name': str,
            'item_type': str,
            'base_price': Decimal,
            'calculated_price': Decimal,
            'calculation_detail': str,
        }, ...]
    """
    enrollment_products = get_enrollment_products_for_course(course, tenant_id)
    enrollment_month = enrollment_date.month

    # 入会金支払い済みチェック（世帯単位）
    enrollment_fee_paid = False
    if guardian:
        enrollment_fee_paid = has_guardian_paid_enrollment_fee(guardian, tenant_id)
        if enrollment_fee_paid:
            print(f"[calculate_enrollment_fees] 入会金は支払い済み（世帯）", file=sys.stderr)

    # バッグ受け取り済みチェック（生徒単位）
    bag_received = False
    if student:
        bag_received = has_student_received_bag(student, tenant_id)
        if bag_received:
            print(f"[calculate_enrollment_fees] バッグは受け取り済み（生徒）", file=sys.stderr)

    results = []

    for product in enrollment_products:
        result = _calculate_single_enrollment_fee(
            product=product,
            course=course,
            tenant_id=tenant_id,
            enrollment_month=enrollment_month,
            additional_tickets=additional_tickets,
            total_classes_in_month=total_classes_in_month,
            enrollment_fee_paid=enrollment_fee_paid,
            bag_received=bag_received,
        )
        if result:
            results.append(result)
            print(f"[calculate_enrollment_fees] {result['item_type']}: {result['calculation_detail']}", file=sys.stderr)

    return results


def _calculate_single_enrollment_fee(
    product: Product,
    course: Course,
    tenant_id: str,
    enrollment_month: int,
    additional_tickets: int,
    total_classes_in_month: int,
    enrollment_fee_paid: bool,
    bag_received: bool,
) -> Dict[str, Any]:
    """単一の入会時費用を計算"""
    item_type = product.item_type
    base_price = product.base_price or Decimal('0')
    calculated_price = Decimal('0')
    calculation_detail = ''

    if item_type == Product.ItemType.ENROLLMENT:
        # 入会金: そのまま（世帯で1回のみ）
        if enrollment_fee_paid:
            print(f"[calculate_enrollment_fees] 入会金スキップ（支払い済み）", file=sys.stderr)
            return None
        calculated_price = base_price
        calculation_detail = f'入会金: ¥{base_price}'

    elif item_type == Product.ItemType.ENROLLMENT_TUITION:
        # 入会時授業料: 通常授業料の単価 × 追加チケット数
        tuition_product = Product.objects.filter(
            tenant_id=tenant_id,
            product_code__startswith=f"{course.course_code}_",
            item_type=Product.ItemType.TUITION,
            is_active=True,
            deleted_at__isnull=True
        ).first()
        per_ticket = tuition_product.per_ticket_price if tuition_product and tuition_product.per_ticket_price else Decimal('0')
        calculated_price = (per_ticket * additional_tickets).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        calculation_detail = f'単価¥{per_ticket} × {additional_tickets}回 = ¥{calculated_price}'

    elif item_type in [Product.ItemType.ENROLLMENT_MONTHLY_FEE, Product.ItemType.ENROLLMENT_FACILITY]:
        # 入会時月会費/設備費: 通常商品の月額 ÷ 月内授業回数 × 追加チケット数
        regular_item_type = Product.ItemType.MONTHLY_FEE if item_type == Product.ItemType.ENROLLMENT_MONTHLY_FEE else Product.ItemType.FACILITY
        regular_product = Product.objects.filter(
            tenant_id=tenant_id,
            product_code__startswith=f"{course.course_code}_",
            item_type=regular_item_type,
            is_active=True,
            deleted_at__isnull=True
        ).first()
        monthly_price = regular_product.base_price if regular_product else base_price

        if total_classes_in_month > 0 and additional_tickets > 0:
            per_class = monthly_price / Decimal(str(total_classes_in_month))
            calculated_price = (per_class * additional_tickets).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            calculation_detail = f'¥{monthly_price} ÷ {total_classes_in_month}回 × {additional_tickets}回 = ¥{calculated_price}'
        else:
            calculated_price = Decimal('0')
            calculation_detail = '追加チケットなし'

    elif item_type == Product.ItemType.ENROLLMENT_TEXTBOOK:
        # 入会時教材費: 入会月に応じた傾斜料金
        month_price_map = {
            1: product.enrollment_price_jan,
            2: product.enrollment_price_feb,
            3: product.enrollment_price_mar,
            4: product.enrollment_price_apr,
            5: product.enrollment_price_may,
            6: product.enrollment_price_jun,
            7: product.enrollment_price_jul,
            8: product.enrollment_price_aug,
            9: product.enrollment_price_sep,
            10: product.enrollment_price_oct,
            11: product.enrollment_price_nov,
            12: product.enrollment_price_dec,
        }
        calculated_price = month_price_map.get(enrollment_month) or base_price
        calculation_detail = f'{enrollment_month}月入会者料金: ¥{calculated_price}'

    elif item_type == Product.ItemType.BAG:
        # バッグ: 初回のみ（2回目以降は請求しない）
        if bag_received:
            print(f"[calculate_enrollment_fees] バッグスキップ（受け取り済み）", file=sys.stderr)
            return None
        calculated_price = base_price
        calculation_detail = f'初回プレゼント: ¥{base_price}'

    else:
        # その他の入会時費用: そのまま
        calculated_price = base_price
        calculation_detail = f'固定料金: ¥{base_price}'

    return {
        'product_id': str(product.id),
        'product_code': product.product_code,
        'product_name': product.product_name,
        'item_type': item_type,
        'base_price': int(base_price),
        'calculated_price': int(calculated_price),
        'calculation_detail': calculation_detail,
        'per_ticket_price': int(product.per_ticket_price or 0),
        'additional_tickets': additional_tickets,
    }

"""
Main Calculation Function - 全料金・割引計算
"""
import sys
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any

from apps.contracts.models import Course, Pack
from apps.students.models import Student, Guardian
from apps.schools.models import Brand
from .status import (
    has_guardian_paid_enrollment_fee,
    get_student_highest_facility_fee,
)
from .products import (
    get_enrollment_fee_product,
    get_facility_fee_product,
    get_materials_fee_product,
)
from .discounts import (
    get_active_fs_discount,
    calculate_mile_discount,
)


def calculate_all_fees_and_discounts(
    student: Student,
    guardian: Guardian,
    course: Optional[Course],
    pack: Optional[Pack],
    brand: Brand,
    tenant_id: str,
    start_date: Optional[date] = None,
    is_new_enrollment: bool = True
) -> Dict[str, Any]:
    """全ての料金と割引を計算

    Returns:
        {
            'enrollment_fee': {...},  # 入会金情報
            'facility_fee': {...},    # 設備費情報
            'materials_fee': {...},   # 教材費情報
            'fs_discount': {...},     # FS割引情報
            'mile_discount': {...},   # マイル割引き情報
        }
    """
    result = {
        'enrollment_fee': None,
        'facility_fee': None,
        'materials_fee': None,
        'fs_discount': None,
        'mile_discount': None,
    }

    # 1. 入会金チェック（世帯で1回のみ）
    if is_new_enrollment and not has_guardian_paid_enrollment_fee(guardian, tenant_id):
        enrollment_product = get_enrollment_fee_product(brand, tenant_id)
        if enrollment_product:
            price = enrollment_product.base_price or Decimal('0')
            result['enrollment_fee'] = {
                'product_id': str(enrollment_product.id),
                'product_name': enrollment_product.product_name,
                'price': int(price),
                'tax_rate': float(enrollment_product.tax_rate or Decimal('0.1')),
                'reason': '新規入会',
            }
            print(f"[PricingCalc] Enrollment fee: {enrollment_product.product_name} = ¥{price}", file=sys.stderr)
    else:
        print(f"[PricingCalc] Enrollment fee: already paid or not new enrollment", file=sys.stderr)

    # 2. 設備費チェック（生徒で1つ、最高額優先）
    current_facility_fee = get_student_highest_facility_fee(student, tenant_id)
    facility_product = get_facility_fee_product(brand, tenant_id)

    if facility_product:
        new_facility_fee = facility_product.base_price or Decimal('0')

        # 新しい設備費が既存より高い場合、差額を請求
        if new_facility_fee > current_facility_fee:
            fee_to_charge = new_facility_fee - current_facility_fee
            result['facility_fee'] = {
                'product_id': str(facility_product.id),
                'product_name': facility_product.product_name,
                'price': int(fee_to_charge),
                'original_price': int(new_facility_fee),
                'current_fee': int(current_facility_fee),
                'tax_rate': float(facility_product.tax_rate or Decimal('0.1')),
                'reason': '差額請求' if current_facility_fee > 0 else '新規',
            }
            print(f"[PricingCalc] Facility fee: {facility_product.product_name} = ¥{fee_to_charge} (diff from ¥{current_facility_fee})", file=sys.stderr)
        else:
            print(f"[PricingCalc] Facility fee: not charged (current ¥{current_facility_fee} >= new ¥{new_facility_fee})", file=sys.stderr)

    # 3. 教材費（入会時）
    use_course = course or (pack.pack_courses.first().course if pack and pack.pack_courses.exists() else None)
    if use_course and is_new_enrollment:
        materials_product = get_materials_fee_product(brand, use_course, tenant_id, is_enrollment=True)
        if materials_product:
            price = materials_product.base_price or Decimal('0')
            result['materials_fee'] = {
                'product_id': str(materials_product.id),
                'product_name': materials_product.product_name,
                'price': int(price),
                'tax_rate': float(materials_product.tax_rate or Decimal('0.1')),
            }
            print(f"[PricingCalc] Materials fee: {materials_product.product_name} = ¥{price}", file=sys.stderr)

    # 4. FS割引（友達紹介割引）
    fs_discount = get_active_fs_discount(guardian)
    if fs_discount:
        result['fs_discount'] = {
            'discount_id': str(fs_discount.id),
            'discount_type': fs_discount.discount_type,
            'discount_value': float(fs_discount.discount_value),
            'discount_name': 'FS割引（友達紹介）',
        }
        print(f"[PricingCalc] FS discount: {fs_discount.discount_type} = {fs_discount.discount_value}", file=sys.stderr)

    # 5. マイル割引き（兄弟全員の合計マイル数ベース）
    mile_discount_amount, total_miles, mile_discount_name = calculate_mile_discount(
        guardian=guardian,
        new_course=course,
        new_pack=pack
    )
    if mile_discount_amount > 0:
        result['mile_discount'] = {
            'discount_name': mile_discount_name,
            'discount_amount': int(mile_discount_amount),
            'total_miles': total_miles,
        }
        print(f"[PricingCalc] Mile discount: {mile_discount_name} = ¥{mile_discount_amount} (total {total_miles} miles)", file=sys.stderr)

    return result

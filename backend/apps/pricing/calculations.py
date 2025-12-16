"""
Pricing calculations - 料金計算ヘルパー関数
設備費、入会金、教材費、各種割引の計算ロジック
"""
import sys
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, List, Any, Tuple
from django.db.models import Q

from apps.contracts.models import Course, Pack, Product, Contract, StudentItem
from apps.students.models import Student, Guardian, FSDiscount, StudentEnrollment
from apps.schools.models import Brand


def get_active_contracts_count(student: Student) -> int:
    """生徒の有効な契約数を取得"""
    return Contract.objects.filter(
        student=student,
        status=Contract.Status.ACTIVE
    ).count()


def get_guardian_students_contracts_count(guardian: Guardian) -> int:
    """保護者の全生徒の有効な契約数を取得（兄弟含む）"""
    return Contract.objects.filter(
        guardian=guardian,
        status=Contract.Status.ACTIVE
    ).count()


def has_guardian_paid_enrollment_fee(guardian: Guardian, tenant_id: str) -> bool:
    """保護者（世帯）が入会金を支払い済みかチェック"""
    # StudentItemで入会金の履歴を確認
    enrollment_items = StudentItem.objects.filter(
        tenant_id=tenant_id,
        student__guardian=guardian,
        product__item_type=Product.ItemType.ENROLLMENT,
    ).exists()

    if enrollment_items:
        return True

    # 過去の契約から入会金支払いを確認
    # 有効な契約があれば、入会金は支払い済みとみなす
    has_active_contract = Contract.objects.filter(
        guardian=guardian,
        tenant_id=tenant_id,
        status=Contract.Status.ACTIVE
    ).exists()

    return has_active_contract


def get_student_highest_facility_fee(student: Student, tenant_id: str) -> Decimal:
    """生徒が現在支払っている最高額の設備費を取得"""
    # 現在の有効な契約に紐づく設備費を取得
    facility_items = StudentItem.objects.filter(
        tenant_id=tenant_id,
        student=student,
        product__item_type=Product.ItemType.FACILITY,
    ).order_by('-unit_price').first()

    if facility_items:
        return facility_items.unit_price

    return Decimal('0')


def get_enrollment_fee_product(brand: Brand, tenant_id: str) -> Optional[Product]:
    """ブランドの入会金商品を取得"""
    return Product.objects.filter(
        tenant_id=tenant_id,
        brand=brand,
        item_type=Product.ItemType.ENROLLMENT,
        is_active=True,
        deleted_at__isnull=True
    ).first()


def get_facility_fee_product(brand: Brand, tenant_id: str) -> Optional[Product]:
    """ブランドの設備費商品を取得"""
    return Product.objects.filter(
        tenant_id=tenant_id,
        brand=brand,
        item_type=Product.ItemType.FACILITY,
        is_active=True,
        deleted_at__isnull=True
    ).first()


def get_materials_fee_product(brand: Brand, course: Course, tenant_id: str, is_enrollment: bool = True) -> Optional[Product]:
    """教材費商品を取得

    Args:
        brand: ブランド
        course: コース
        tenant_id: テナントID
        is_enrollment: 入会時かどうか（入会時は入会時教材費）
    """
    item_type = Product.ItemType.ENROLLMENT_TEXTBOOK if is_enrollment else Product.ItemType.TEXTBOOK

    # まずコースに紐づく教材費を検索
    if course:
        course_items = course.course_items.filter(
            is_active=True,
            product__item_type=item_type,
            product__is_active=True,
            product__deleted_at__isnull=True
        ).select_related('product').first()

        if course_items:
            return course_items.product

    # ブランドの教材費を検索
    return Product.objects.filter(
        tenant_id=tenant_id,
        brand=brand,
        item_type=item_type,
        is_active=True,
        deleted_at__isnull=True
    ).first()


def get_active_fs_discount(guardian: Guardian) -> Optional[FSDiscount]:
    """保護者の有効なFS割引を取得"""
    today = date.today()
    return FSDiscount.objects.filter(
        guardian=guardian,
        status=FSDiscount.Status.ACTIVE,
        valid_from__lte=today,
        valid_until__gte=today
    ).first()


def calculate_fs_discount_amount(fs_discount: FSDiscount, subtotal: Decimal) -> Decimal:
    """FS割引額を計算"""
    if not fs_discount:
        return Decimal('0')

    if fs_discount.discount_type == FSDiscount.DiscountType.FIXED:
        return Decimal(str(fs_discount.discount_value))
    elif fs_discount.discount_type == FSDiscount.DiscountType.PERCENTAGE:
        return subtotal * Decimal(str(fs_discount.discount_value)) / Decimal('100')

    return Decimal('0')


def calculate_mile_discount(
    guardian: Guardian,
    new_course: Optional[Course] = None,
    new_pack: Optional[Pack] = None
) -> Tuple[Decimal, int, str]:
    """マイル割引を計算（兄弟全員の合計マイル数ベース）

    計算式: (合計マイル - 2) × 500円
    ※1コースのみの場合は割引なし

    Returns:
        (割引額, 合計マイル数, 割引名)
    """
    # 兄弟全員（保護者配下の全生徒）の有効な契約からマイル数を集計
    active_contracts = Contract.objects.filter(
        guardian=guardian,
        status=Contract.Status.ACTIVE
    ).select_related('course')

    total_miles = 0
    contract_count = 0

    for contract in active_contracts:
        if contract.course and contract.course.mile:
            total_miles += int(contract.course.mile)
            contract_count += 1

    # 新規コースのマイルを追加
    new_course_miles = 0
    if new_course and new_course.mile:
        new_course_miles = int(new_course.mile)
    elif new_pack:
        # パックの場合、パック内コースのマイル合計
        for pack_course in new_pack.pack_courses.select_related('course').all():
            if pack_course.course and pack_course.course.mile:
                new_course_miles += int(pack_course.course.mile)

    total_miles += new_course_miles
    total_contracts = contract_count + (1 if new_course or new_pack else 0)

    # 1コースのみの場合は割引なし
    if total_contracts <= 1:
        return (Decimal('0'), total_miles, '')

    # 割引計算: (合計マイル - 2) × 500円
    if total_miles > 2:
        discount_amount = (total_miles - 2) * 500
        return (Decimal(str(discount_amount)), total_miles, f'マイル割引き（{total_miles}マイル）')

    return (Decimal('0'), total_miles, '')


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

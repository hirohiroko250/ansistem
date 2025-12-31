"""
Discount Calculation Functions - 割引計算関数
"""
from datetime import date
from decimal import Decimal
from typing import Optional, Tuple

from apps.contracts.models import Course, Pack, Contract, CourseItem
from apps.students.models import Guardian, FSDiscount


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

    計算式: (合計マイル - 1) × 500円
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
        if not contract.course:
            continue

        # コースの商品構成からマイルを取得（授業料のみ）
        course_items = CourseItem.objects.filter(
            course=contract.course,
            is_active=True,
            product__item_type='tuition',  # 授業料のみ
            product__mile__gt=0
        ).select_related('product')

        contract_miles = 0
        for item in course_items:
            if item.product and item.product.mile:
                contract_miles += int(item.product.mile)

        if contract_miles > 0:
            total_miles += contract_miles
            contract_count += 1

    # 新規コースのマイルを追加
    new_course_miles = _calculate_new_course_miles(new_course, new_pack)
    total_miles += new_course_miles
    total_contracts = contract_count + (1 if new_course or new_pack else 0)

    # 1コースのみの場合は割引なし
    if total_contracts <= 1:
        return (Decimal('0'), total_miles, '')

    # 2マイル以上のコースがあるかチェック（ぽっきり以外）
    has_regular_course = _has_regular_course(active_contracts)

    # 割引計算
    # ぽっきり（1マイル）のみ: (合計 - 1) × 500円
    # 通常コース含む: (合計 - 2) × 500円
    if has_regular_course:
        # 通常コースあり: -2して計算
        if total_miles > 2:
            discount_amount = (total_miles - 2) * 500
            return (Decimal(str(discount_amount)), total_miles, f'マイル割引き（{total_miles}マイル）')
    else:
        # ぽっきりのみ: -1して計算
        if total_miles > 1:
            discount_amount = (total_miles - 1) * 500
            return (Decimal(str(discount_amount)), total_miles, f'マイル割引き（{total_miles}マイル）')

    return (Decimal('0'), total_miles, '')


def _calculate_new_course_miles(new_course: Optional[Course], new_pack: Optional[Pack]) -> int:
    """新規コースのマイル数を計算"""
    new_course_miles = 0

    if new_course:
        course_items = CourseItem.objects.filter(
            course=new_course,
            is_active=True,
            product__item_type='tuition',
            product__mile__gt=0
        ).select_related('product')
        for item in course_items:
            if item.product and item.product.mile:
                new_course_miles += int(item.product.mile)

    elif new_pack:
        # パックの場合、パック内コースのマイル合計
        for pack_course in new_pack.pack_courses.select_related('course').all():
            if pack_course.course:
                course_items = CourseItem.objects.filter(
                    course=pack_course.course,
                    is_active=True,
                    product__item_type='tuition',
                    product__mile__gt=0
                ).select_related('product')
                for item in course_items:
                    if item.product and item.product.mile:
                        new_course_miles += int(item.product.mile)

    return new_course_miles


def _has_regular_course(active_contracts) -> bool:
    """2マイル以上のコースがあるかチェック（ぽっきり以外）"""
    for contract in active_contracts:
        if not contract.course:
            continue
        course_items = CourseItem.objects.filter(
            course=contract.course,
            is_active=True,
            product__item_type='tuition',
            product__mile__gte=2  # 2マイル以上
        ).exists()
        if course_items:
            return True
    return False

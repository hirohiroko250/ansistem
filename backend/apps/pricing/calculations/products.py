"""
Product Lookup Functions - 商品検索関数
"""
import sys
from typing import Optional, List

from apps.contracts.models import Course, Product
from apps.schools.models import Brand


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


def get_enrollment_products_for_course(course: Course, tenant_id: str) -> List[Product]:
    """コースに対応する入会時商品を自動取得

    コースコードから入会時商品を検索して返す。
    例: コース 24AEC_1000007 の場合
        → 24AEC_1000007_50 (入会時授業料)
        → 24AEC_1000007_54 (入会時月会費)
        → 24AEC_1000007_55 (入会時設備費)
        → 24AEC_1000007_60 (入会時教材費)

    Args:
        course: コース
        tenant_id: テナントID

    Returns:
        入会時商品のリスト
    """
    if not course or not course.course_code:
        return []

    # 入会時商品のitem_type一覧
    enrollment_types = [
        Product.ItemType.ENROLLMENT,            # 入会金
        Product.ItemType.ENROLLMENT_TUITION,    # 入会時授業料
        Product.ItemType.ENROLLMENT_MONTHLY_FEE,# 入会時月会費
        Product.ItemType.ENROLLMENT_FACILITY,   # 入会時設備費
        Product.ItemType.ENROLLMENT_TEXTBOOK,   # 入会時教材費
        Product.ItemType.ENROLLMENT_EXPENSE,    # 入会時諸経費
        Product.ItemType.ENROLLMENT_MANAGEMENT, # 入会時総合指導管理費
        Product.ItemType.BAG,                   # バッグ（初回プレゼント）
    ]

    # コースコードのプレフィックスを取得（例: 24AEC_1000007）
    course_code = course.course_code

    # 同じコースコードプレフィックスの入会時商品を検索
    # 商品コード形式: {course_code}_{suffix} (例: 24AEC_1000007_5, 24AEC_1000007_50)
    products = Product.objects.filter(
        tenant_id=tenant_id,
        product_code__startswith=f"{course_code}_",
        item_type__in=enrollment_types,
        is_active=True,
        deleted_at__isnull=True
    ).order_by('product_code')

    print(f"[get_enrollment_products] Course: {course_code}, Found: {products.count()} enrollment products", file=sys.stderr)

    return list(products)

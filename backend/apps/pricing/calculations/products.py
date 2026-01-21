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

    コースコードから入会時商品を検索し、見つからない場合はブランドレベルにフォールバック。
    例: コース 24AEC_1000007 の場合
        → 24AEC_1000007_50 (入会時授業料)
        → 24AEC_1000007_54 (入会時月会費)
        → 24AEC_1000007_55 (入会時設備費)
        → 24AEC_1000007_60 (入会時教材費)
        → ブランドの入会金（コースレベルになければ）

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

    products_list = list(products)

    # tenant_idで見つからない場合、tenant_idフィルタなしで再検索
    if not products_list:
        products = Product.objects.filter(
            product_code__startswith=f"{course_code}_",
            item_type__in=enrollment_types,
            is_active=True,
            deleted_at__isnull=True
        ).order_by('product_code')
        products_list = list(products)
        if products_list:
            print(f"[get_enrollment_products] Course: {course_code}, Found {len(products_list)} products (fallback without tenant_id)", file=sys.stderr)

    found_types = {p.item_type for p in products_list}

    print(f"[get_enrollment_products] Course: {course_code}, tenant_id: {tenant_id}, Found: {len(products_list)} enrollment products", file=sys.stderr)

    # ブランドレベルの商品にフォールバック（コースレベルになければ）
    brand = course.brand
    if brand:
        # 入会金がなければブランドの入会金を追加
        if Product.ItemType.ENROLLMENT not in found_types:
            enrollment_product = Product.objects.filter(
                tenant_id=tenant_id,
                brand=brand,
                item_type=Product.ItemType.ENROLLMENT,
                is_active=True,
                deleted_at__isnull=True
            ).first()
            # tenant_idで見つからない場合はtenant_idフィルタなしで再検索
            if not enrollment_product:
                enrollment_product = Product.objects.filter(
                    brand=brand,
                    item_type=Product.ItemType.ENROLLMENT,
                    is_active=True,
                    deleted_at__isnull=True
                ).first()
            if enrollment_product:
                products_list.append(enrollment_product)
                print(f"[get_enrollment_products] Added brand-level enrollment fee: {enrollment_product.product_name}", file=sys.stderr)

        # 入会時設備費がなければ通常の設備費を入会時設備費として追加
        if Product.ItemType.ENROLLMENT_FACILITY not in found_types:
            # まずコースレベルの設備費を検索
            facility_product = Product.objects.filter(
                tenant_id=tenant_id,
                product_code__startswith=f"{course_code}_",
                item_type=Product.ItemType.FACILITY,
                is_active=True,
                deleted_at__isnull=True
            ).first()
            # tenant_idで見つからない場合はtenant_idフィルタなしで再検索
            if not facility_product:
                facility_product = Product.objects.filter(
                    product_code__startswith=f"{course_code}_",
                    item_type=Product.ItemType.FACILITY,
                    is_active=True,
                    deleted_at__isnull=True
                ).first()

            # コースレベルになければブランドレベルを検索
            if not facility_product:
                facility_product = Product.objects.filter(
                    tenant_id=tenant_id,
                    brand=brand,
                    item_type=Product.ItemType.FACILITY,
                    is_active=True,
                    deleted_at__isnull=True
                ).first()
            # tenant_idで見つからない場合はtenant_idフィルタなしで再検索
            if not facility_product:
                facility_product = Product.objects.filter(
                    brand=brand,
                    item_type=Product.ItemType.FACILITY,
                    is_active=True,
                    deleted_at__isnull=True
                ).first()

            if facility_product:
                # 通常設備費を入会時設備費の代わりとして追加（item_typeを変更した仮想商品）
                # Note: calculate_enrollment_fees でitem_typeをチェックして計算する
                products_list.append(facility_product)
                print(f"[get_enrollment_products] Added facility fee (as enrollment_facility): {facility_product.product_name}", file=sys.stderr)

    return products_list

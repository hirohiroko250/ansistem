"""
Pricing Calculations Package - 料金計算ヘルパー関数

モジュール構成:
- status.py: 契約・生徒ステータス確認関数
- products.py: 商品検索関数
- fees.py: 料金計算関数
- discounts.py: 割引計算関数
- main.py: 全料金・割引計算
"""
# Status check functions
from .status import (
    get_active_contracts_count,
    get_guardian_students_contracts_count,
    has_guardian_paid_enrollment_fee,
    has_student_received_bag,
    get_student_highest_facility_fee,
)

# Product lookup functions
from .products import (
    get_enrollment_fee_product,
    get_facility_fee_product,
    get_materials_fee_product,
    get_enrollment_products_for_course,
)

# Fee calculation functions
from .fees import calculate_enrollment_fees

# Discount calculation functions
from .discounts import (
    get_active_fs_discount,
    calculate_fs_discount_amount,
    calculate_mile_discount,
)

# Main calculation function
from .main import calculate_all_fees_and_discounts

__all__ = [
    # Status
    'get_active_contracts_count',
    'get_guardian_students_contracts_count',
    'has_guardian_paid_enrollment_fee',
    'has_student_received_bag',
    'get_student_highest_facility_fee',
    # Products
    'get_enrollment_fee_product',
    'get_facility_fee_product',
    'get_materials_fee_product',
    'get_enrollment_products_for_course',
    # Fees
    'calculate_enrollment_fees',
    # Discounts
    'get_active_fs_discount',
    'calculate_fs_discount_amount',
    'calculate_mile_discount',
    # Main
    'calculate_all_fees_and_discounts',
]

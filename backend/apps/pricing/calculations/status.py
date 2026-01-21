"""
Status Check Functions - 契約・生徒ステータス確認関数
"""
from decimal import Decimal

from apps.contracts.models import Contract, Product, StudentItem
from apps.students.models import Student, Guardian


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
    """保護者（世帯）が入会金を支払い済みかチェック

    以下のいずれかに該当する場合、入会金は支払い済みとみなす:
    1. StudentItemに入会金の履歴がある
    2. 過去に契約がある（インポートデータ含む、ステータス問わず）
    """
    if not guardian:
        return False

    # StudentItemで入会金の履歴を確認
    enrollment_items = StudentItem.objects.filter(
        tenant_id=tenant_id,
        student__guardian=guardian,
        product__item_type=Product.ItemType.ENROLLMENT,
        deleted_at__isnull=True,
    ).exists()

    if enrollment_items:
        return True

    # 過去の契約から入会金支払いを確認
    has_any_contract = Contract.objects.filter(
        guardian=guardian,
        tenant_id=tenant_id,
    ).exists()

    return has_any_contract


def has_student_received_bag(student: Student, tenant_id: str) -> bool:
    """生徒がバッグを受け取り済みかチェック

    以下のいずれかに該当する場合、バッグは受け取り済みとみなす:
    1. StudentItemにバッグの履歴がある
    2. 過去に契約がある（インポートデータ含む、ステータス問わず）
    """
    if not student:
        return False

    # StudentItemでバッグの履歴を確認
    bag_items = StudentItem.objects.filter(
        tenant_id=tenant_id,
        student=student,
        product__item_type=Product.ItemType.BAG,
        deleted_at__isnull=True,
    ).exists()

    if bag_items:
        return True

    # 過去の契約からバッグ受け取りを確認
    has_any_contract = Contract.objects.filter(
        student=student,
        tenant_id=tenant_id,
    ).exists()

    return has_any_contract


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

"""
StudentItem Creation Helpers - StudentItem作成ヘルパー
"""
import logging
from datetime import date, time
from decimal import Decimal
from typing import Optional, Dict, List, Any, Tuple

from apps.contracts.models import Course, Product, Contract, StudentItem
from apps.students.models import Student, Guardian
from apps.schools.models import Brand, School, ClassSchedule
from apps.pricing.calculations import calculate_enrollment_fees
from apps.pricing.services.preview_service import PricingPreviewService

logger = logging.getLogger(__name__)


def create_student_items_from_course(
    student: Student,
    contract: Contract,
    course: Course,
    billing_month: str,
    order_id: str,
    brand: Optional[Brand],
    school: Optional[School],
    start_date: Optional[date],
    day_of_week: Optional[int],
    start_time: Optional[time],
    end_time: Optional[time],
    class_schedule: Optional[ClassSchedule],
    exclude_textbooks: bool = True
) -> List[StudentItem]:
    """コース商品からStudentItemを作成

    Args:
        student: 生徒
        contract: 契約
        course: コース
        billing_month: 請求月
        order_id: 注文ID
        brand: ブランド
        school: 校舎
        start_date: 開始日
        day_of_week: 曜日
        start_time: 開始時間
        end_time: 終了時間
        class_schedule: クラススケジュール
        exclude_textbooks: 教材費を除外するか

    Returns:
        作成したStudentItemのリスト
    """
    created_items = []
    course_items = course.course_items.filter(is_active=True).select_related('product')

    for course_item in course_items:
        product = course_item.product
        if not product:
            continue

        # 教材費は除外（別途選択した教材費を登録）
        if exclude_textbooks and product.item_type == 'textbook':
            continue

        unit_price = course_item.get_price()

        item = StudentItem.objects.create(
            tenant_id=student.tenant_id,
            student=student,
            contract=contract,
            product=product,
            billing_month=billing_month,
            quantity=course_item.quantity,
            unit_price=unit_price,
            discount_amount=0,
            final_price=unit_price * course_item.quantity,
            notes=f'注文番号: {order_id} / コース: {course.course_name}',
            brand=brand,
            school=school,
            course=course,
            start_date=start_date,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            class_schedule=class_schedule,
        )
        created_items.append(item)

    return created_items


def create_textbook_student_items(
    student: Student,
    contract: Contract,
    textbook_ids: List[str],
    billing_month: str,
    order_id: str,
    brand: Optional[Brand],
    school: Optional[School],
    course: Optional[Course],
    start_date: Optional[date],
    day_of_week: Optional[int],
    start_time: Optional[time],
    end_time: Optional[time],
    class_schedule: Optional[ClassSchedule]
) -> List[StudentItem]:
    """選択された教材費のStudentItemを作成

    入会時は傾斜料金（入会月に応じた価格）を使用し、
    2ヶ月目以降は標準価格（base_price）を使用する
    """
    created_items = []

    # 入会月を取得（入会時の傾斜料金計算用）
    enrollment_month = start_date.month if start_date else None

    for textbook_id in textbook_ids:
        try:
            textbook_product = Product.objects.get(id=textbook_id)

            # 入会時は傾斜料金を使用
            if enrollment_month:
                unit_price = Decimal(str(textbook_product.get_price_for_enrollment_month(enrollment_month)))
            else:
                unit_price = textbook_product.base_price or Decimal('0')

            item = StudentItem.objects.create(
                tenant_id=student.tenant_id,
                student=student,
                contract=contract,
                product=textbook_product,
                billing_month=billing_month,
                quantity=1,
                unit_price=unit_price,
                discount_amount=0,
                final_price=unit_price,
                notes=f'注文番号: {order_id} / 教材費（選択・{enrollment_month}月入会）: {textbook_product.product_name}',
                brand=brand,
                school=school,
                course=course,
                start_date=start_date,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                class_schedule=class_schedule,
            )
            created_items.append(item)
            logger.info(f"Created textbook StudentItem: {textbook_product.product_name} = ¥{unit_price} (enrollment month: {enrollment_month})")

        except Product.DoesNotExist:
            logger.warning(f"Selected textbook not found: {textbook_id}")

    return created_items


def create_enrollment_fee_student_items(
    student: Student,
    guardian: Optional[Guardian],
    contract: Contract,
    course: Course,
    start_date: date,
    day_of_week: int,
    billing_month: str,
    order_id: str,
    brand: Optional[Brand],
    school: Optional[School],
    start_time: Optional[time],
    end_time: Optional[time],
    class_schedule: Optional[ClassSchedule]
) -> Tuple[List[StudentItem], Optional[str]]:
    """入会時費用のStudentItemを作成

    Returns:
        (created_items, enrollment_tuition_info)
    """
    created_items = []
    enrollment_tuition_info = None

    try:
        prorated_info = PricingPreviewService.calculate_prorated_by_day_of_week(start_date, day_of_week)
        additional_tickets = prorated_info['remaining_count']
        total_classes_in_month = prorated_info['total_count']

        enrollment_fees = calculate_enrollment_fees(
            course=course,
            tenant_id=str(student.tenant_id),
            enrollment_date=start_date,
            additional_tickets=additional_tickets,
            total_classes_in_month=total_classes_in_month,
            student=student,
            guardian=guardian,
        )

        for fee in enrollment_fees:
            if fee['calculated_price'] >= 0:
                try:
                    product = Product.objects.get(id=fee['product_id'])
                except Product.DoesNotExist:
                    continue

                item = StudentItem.objects.create(
                    tenant_id=student.tenant_id,
                    student=student,
                    contract=contract,
                    product=product,
                    billing_month=billing_month,
                    quantity=1,
                    unit_price=fee['calculated_price'],
                    discount_amount=0,
                    final_price=fee['calculated_price'],
                    notes=f'注文番号: {order_id} / {fee["calculation_detail"]}',
                    brand=brand,
                    school=school,
                    course=course,
                    start_date=start_date,
                    day_of_week=day_of_week,
                    start_time=start_time,
                    end_time=end_time,
                    class_schedule=class_schedule,
                )
                created_items.append(item)

                if fee['item_type'] == 'enrollment_tuition':
                    enrollment_tuition_info = f"{fee['product_name']} ¥{fee['calculated_price']:,}"

    except Exception as e:
        logger.error(f"Error creating enrollment fees: {e}")

    return created_items, enrollment_tuition_info

"""
PricingConfirmationService - 購入確定サービス

購入確定、契約・StudentItem作成のビジネスロジック
"""
import uuid
import logging
from datetime import date
from typing import Optional, Dict, List, Any

from django.db import transaction

from apps.contracts.models import Course
from apps.students.models import Student
from apps.schools.models import Brand, School
from .helpers import (
    validate_mile_usage,
    parse_schedules,
    create_contract,
    create_student_items_from_course,
    create_textbook_student_items,
    create_enrollment_fee_student_items,
    create_student_school,
    create_student_enrollment,
    update_student_status,
    create_enrollment_task,
)

logger = logging.getLogger(__name__)


class PricingConfirmationService:
    """購入確定サービス"""

    # ヘルパー関数をクラスメソッドとして公開（後方互換性）
    validate_mile_usage = staticmethod(validate_mile_usage)
    parse_schedules = staticmethod(parse_schedules)
    create_contract = staticmethod(create_contract)
    create_student_items_from_course = staticmethod(create_student_items_from_course)
    create_textbook_student_items = staticmethod(create_textbook_student_items)
    create_enrollment_fee_student_items = staticmethod(create_enrollment_fee_student_items)
    create_student_school = staticmethod(create_student_school)
    create_student_enrollment = staticmethod(create_student_enrollment)
    update_student_status = staticmethod(update_student_status)
    create_enrollment_task = staticmethod(create_enrollment_task)

    @classmethod
    @transaction.atomic
    def confirm_purchase(
        cls,
        student: Student,
        course: Course,
        brand: Optional[Brand],
        school: Optional[School],
        start_date: Optional[date],
        schedules: List[Dict[str, Any]],
        selected_textbook_ids: List[str],
        miles_to_use: int = 0
    ) -> Dict[str, Any]:
        """購入を確定

        Args:
            student: 生徒
            course: コース
            brand: ブランド
            school: 校舎
            start_date: 開始日
            schedules: スケジュール情報
            selected_textbook_ids: 選択された教材費ID
            miles_to_use: 使用マイル数

        Returns:
            確定結果
        """
        guardian = student.guardian
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        billing_month = date.today().strftime('%Y-%m')

        # マイルバリデーション
        is_valid, error_message, mile_discount = validate_mile_usage(guardian, miles_to_use)
        if not is_valid:
            return {'success': False, 'error': error_message}

        # スケジュール解析
        day_of_week, start_time, end_time, class_schedule = parse_schedules(schedules)

        # 契約作成
        contract = create_contract(student, course, brand, school, start_date)

        # コース商品のStudentItem作成
        create_student_items_from_course(
            student=student,
            contract=contract,
            course=course,
            billing_month=billing_month,
            order_id=order_id,
            brand=brand,
            school=school,
            start_date=start_date,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            class_schedule=class_schedule,
        )

        # 選択された教材費のStudentItem作成
        if selected_textbook_ids:
            create_textbook_student_items(
                student=student,
                contract=contract,
                textbook_ids=selected_textbook_ids,
                billing_month=billing_month,
                order_id=order_id,
                brand=brand,
                school=school,
                course=course,
                start_date=start_date,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                class_schedule=class_schedule,
            )

        # 生徒所属の作成
        if school and brand:
            create_student_school(student, school, brand, start_date)

            # 受講履歴の作成
            create_student_enrollment(
                student=student,
                school=school,
                brand=brand,
                class_schedule=class_schedule,
                start_date=start_date,
                order_id=order_id,
                course_name=course.course_name,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
            )

            # 生徒ステータス更新
            update_student_status(student)

        # 入会時費用のStudentItem作成
        enrollment_tuition_info = None
        if start_date and day_of_week:
            _, enrollment_tuition_info = create_enrollment_fee_student_items(
                student=student,
                guardian=guardian,
                contract=contract,
                course=course,
                start_date=start_date,
                day_of_week=day_of_week,
                billing_month=billing_month,
                order_id=order_id,
                brand=brand,
                school=school,
                start_time=start_time,
                end_time=end_time,
                class_schedule=class_schedule,
            )

        # マイル使用
        if miles_to_use > 0 and guardian:
            from apps.billing.services import MileCalculationService
            MileCalculationService.use_miles(
                guardian=guardian,
                miles=miles_to_use,
                notes=f'注文番号: {order_id} でのマイル使用'
            )

        # タスク作成
        task = create_enrollment_task(
            student=student,
            guardian=guardian,
            course=course,
            school=school,
            brand=brand,
            order_id=order_id,
        )

        return {
            'success': True,
            'order_id': order_id,
            'contract_id': str(contract.id),
            'contract_no': contract.contract_no,
            'task_id': str(task.id),
            'mile_discount': int(mile_discount),
            'enrollment_tuition_info': enrollment_tuition_info,
        }

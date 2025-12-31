"""
Enrollment Helpers - 生徒所属・受講履歴作成ヘルパー
"""
import uuid
from datetime import date, time
from decimal import Decimal
from typing import Optional, Tuple

from apps.contracts.models import Course, Contract
from apps.students.models import Student, Guardian, StudentSchool, StudentEnrollment
from apps.schools.models import Brand, School, ClassSchedule
from apps.billing.models import MileTransaction
from apps.tasks.models import Task


def validate_mile_usage(
    guardian: Guardian,
    miles_to_use: int
) -> Tuple[bool, str, Decimal]:
    """マイル使用のバリデーション

    Args:
        guardian: 保護者
        miles_to_use: 使用マイル数

    Returns:
        (is_valid, error_message, discount_amount)
    """
    if miles_to_use <= 0:
        return True, '', Decimal('0')

    if not guardian:
        return False, '保護者情報が見つかりません', Decimal('0')

    mile_balance = MileTransaction.get_balance(guardian)
    can_use = MileTransaction.can_use_miles(guardian)

    if not can_use:
        return False, 'マイルを使用するにはコース契約が2つ以上必要です', Decimal('0')

    if miles_to_use > mile_balance:
        return False, f'マイル残高が不足しています（残高: {mile_balance}pt）', Decimal('0')

    if miles_to_use < 4:
        return False, 'マイルは4pt以上から使用できます', Decimal('0')

    discount_amount = MileTransaction.calculate_discount(miles_to_use)
    return True, '', discount_amount


def parse_schedules(schedules):
    """スケジュール情報をパース

    Args:
        schedules: スケジュール情報リスト

    Returns:
        (day_of_week, start_time, end_time, class_schedule)
    """
    if not schedules:
        return None, None, None, None

    first_schedule = schedules[0]
    class_schedule_id = first_schedule.get('id')

    if class_schedule_id:
        try:
            class_schedule = ClassSchedule.objects.get(id=class_schedule_id)
            return (
                class_schedule.day_of_week,
                class_schedule.start_time,
                class_schedule.end_time,
                class_schedule
            )
        except ClassSchedule.DoesNotExist:
            pass

    # フォールバック
    day_of_week_str = first_schedule.get('day_of_week', '')
    day_name_to_int = {
        '月曜日': 1, '火曜日': 2, '水曜日': 3, '木曜日': 4,
        '金曜日': 5, '土曜日': 6, '日曜日': 7
    }
    day_of_week = day_name_to_int.get(day_of_week_str)

    start_time_obj = None
    end_time_obj = None

    try:
        start_time_str = first_schedule.get('start_time', '')
        end_time_str = first_schedule.get('end_time', '')

        if start_time_str:
            parts = start_time_str.split(':')
            start_time_obj = time(int(parts[0]), int(parts[1]))
        if end_time_str:
            parts = end_time_str.split(':')
            end_time_obj = time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        pass

    return day_of_week, start_time_obj, end_time_obj, None


def create_contract(
    student: Student,
    course: Course,
    brand: Optional[Brand],
    school: Optional[School],
    start_date: Optional[date]
) -> Contract:
    """契約を作成

    Args:
        student: 生徒
        course: コース
        brand: ブランド
        school: 校舎
        start_date: 開始日

    Returns:
        Contract
    """
    contract_no = f"C{date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

    contract = Contract.objects.create(
        tenant_id=student.tenant_id,
        contract_no=contract_no,
        student=student,
        guardian=student.guardian,
        school=school,
        brand=brand,
        course=course,
        contract_date=date.today(),
        start_date=start_date or date.today(),
        status=Contract.Status.ACTIVE,
    )

    return contract


def create_student_school(
    student: Student,
    school: School,
    brand: Brand,
    start_date: Optional[date]
) -> Tuple[StudentSchool, bool]:
    """生徒所属を作成/更新"""
    student_school, created = StudentSchool.objects.get_or_create(
        tenant_id=student.tenant_id,
        student=student,
        school=school,
        brand=brand,
        defaults={
            'enrollment_status': 'active',
            'start_date': start_date or date.today(),
            'is_primary': not StudentSchool.objects.filter(
                student=student, is_primary=True
            ).exists(),
        }
    )
    return student_school, created


def create_student_enrollment(
    student: Student,
    school: School,
    brand: Brand,
    class_schedule: Optional[ClassSchedule],
    start_date: Optional[date],
    order_id: str,
    course_name: str,
    day_of_week: Optional[int],
    start_time: Optional[time],
    end_time: Optional[time]
) -> StudentEnrollment:
    """受講履歴を作成"""
    enrollment = StudentEnrollment.create_enrollment(
        student=student,
        school=school,
        brand=brand,
        class_schedule=class_schedule,
        change_type=StudentEnrollment.ChangeType.NEW_ENROLLMENT,
        effective_date=start_date or date.today(),
        notes=f'注文番号: {order_id} / コース: {course_name}',
        day_of_week_override=day_of_week,
        start_time_override=start_time,
        end_time_override=end_time,
    )
    return enrollment


def update_student_status(student: Student) -> bool:
    """生徒ステータスを更新（入会に変更）"""
    if student.status in [Student.Status.REGISTERED, Student.Status.TRIAL]:
        student.status = Student.Status.ENROLLED
        student.save(update_fields=['status', 'updated_at'])
        return True
    return False


def create_enrollment_task(
    student: Student,
    guardian: Optional[Guardian],
    course: Course,
    school: Optional[School],
    brand: Optional[Brand],
    order_id: str
) -> Task:
    """入会申請タスクを作成"""
    task = Task.objects.create(
        tenant_id=student.tenant_id,
        task_type=Task.TaskType.ENROLLMENT_REQUEST,
        priority=Task.Priority.HIGH,
        title=f'{student.full_name}様 入会申請',
        description=f'''
入会申請が届きました。

【注文情報】
注文番号: {order_id}
コース名: {course.course_name if course else '未指定'}
校舎: {school.school_name if school else '未指定'}
ブランド: {brand.brand_name if brand else '未指定'}

【生徒情報】
生徒名: {student.full_name}
保護者名: {guardian.full_name if guardian else '未登録'}

【対応事項】
- 入会書類の確認
- 初回レッスン日の調整
- 保護者への連絡
'''.strip(),
        student=student,
        status=Task.Status.PENDING,
    )
    return task

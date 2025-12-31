"""
Confirm Helpers - 購入確定用ヘルパー関数
"""
import sys
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from apps.contracts.models import Course, Pack, StudentItem, Product, Contract
from apps.students.models import Student, StudentSchool, StudentEnrollment
from apps.tasks.models import Task
from apps.schools.models import Brand, School, ClassSchedule
from apps.billing.models import MileTransaction

from apps.pricing.views.utils import (
    get_product_price_for_enrollment,
    calculate_enrollment_tuition_tickets,
    get_enrollment_tuition_product,
)


def parse_request_data(request):
    """リクエストデータを解析"""
    return {
        'preview_id': request.data.get('preview_id'),
        'payment_method': request.data.get('payment_method'),
        'student_id': request.data.get('student_id'),
        'course_id': request.data.get('course_id'),
        'brand_id': request.data.get('brand_id'),
        'school_id': request.data.get('school_id'),
        'start_date_str': request.data.get('start_date'),
        'schedules': request.data.get('schedules', []),
        'ticket_id': request.data.get('ticket_id'),
        'miles_to_use': int(request.data.get('miles_to_use', 0) or 0),
        'selected_textbook_ids': request.data.get('selected_textbook_ids', []),
    }


def get_student_and_guardian(student_id):
    """生徒と保護者を取得"""
    student = None
    guardian = None
    if student_id:
        try:
            student = Student.objects.select_related('guardian').get(id=student_id)
            guardian = student.guardian
        except Student.DoesNotExist:
            pass
    return student, guardian


def validate_miles(miles_to_use, guardian):
    """マイル使用のバリデーション"""
    if miles_to_use <= 0 or not guardian:
        return None, Decimal('0')

    mile_balance = MileTransaction.get_balance(guardian)
    can_use = MileTransaction.can_use_miles(guardian)

    if not can_use:
        return {'error': 'マイルを使用するにはコース契約が2つ以上必要です'}, Decimal('0')
    if miles_to_use > mile_balance:
        return {'error': f'マイル残高が不足しています（残高: {mile_balance}pt）'}, Decimal('0')
    if miles_to_use < 4:
        return {'error': 'マイルは4pt以上から使用できます'}, Decimal('0')

    mile_discount = MileTransaction.calculate_discount(miles_to_use)
    print(f"[PricingConfirm] Mile discount: {miles_to_use}pt -> ¥{mile_discount}", file=sys.stderr)
    return None, mile_discount


def get_course_or_pack(course_id, preview_id):
    """コースまたはパックを取得"""
    course = None
    pack = None

    if course_id:
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            try:
                pack = Pack.objects.get(id=course_id)
                print(f"[PricingConfirm] Found pack: {pack.pack_name}", file=sys.stderr)
            except Pack.DoesNotExist:
                pass

    if not course and not pack and preview_id:
        try:
            course = Course.objects.get(id=preview_id)
        except Course.DoesNotExist:
            try:
                pack = Pack.objects.get(id=preview_id)
                print(f"[PricingConfirm] Found pack from preview_id: {pack.pack_name}", file=sys.stderr)
            except Pack.DoesNotExist:
                pass

    return course, pack


def get_brand_and_school(brand_id, school_id):
    """ブランドと校舎を取得"""
    brand = None
    school = None

    if brand_id:
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            pass

    if school_id:
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            pass

    return brand, school


def parse_start_date(start_date_str):
    """開始日をパース"""
    if start_date_str:
        try:
            return datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    return None


def parse_schedule_info(schedules):
    """スケジュール情報を解析"""
    schedule_day_of_week = None
    schedule_start_time = None
    schedule_end_time = None
    selected_class_schedule = None

    if not schedules or len(schedules) == 0:
        return schedule_day_of_week, schedule_start_time, schedule_end_time, selected_class_schedule

    first_schedule = schedules[0]
    class_schedule_id = first_schedule.get('id')

    if class_schedule_id:
        try:
            selected_class_schedule = ClassSchedule.objects.get(id=class_schedule_id)
            schedule_day_of_week = selected_class_schedule.day_of_week
            schedule_start_time = selected_class_schedule.start_time
            schedule_end_time = selected_class_schedule.end_time
            print(f"[PricingConfirm] Found ClassSchedule: {selected_class_schedule.class_name} (id={class_schedule_id})", file=sys.stderr)
        except ClassSchedule.DoesNotExist:
            print(f"[PricingConfirm] ClassSchedule not found: id={class_schedule_id}", file=sys.stderr)

    # フォールバック
    if not selected_class_schedule:
        day_of_week_str = first_schedule.get('day_of_week', '')
        day_name_to_int = {'月曜日': 1, '火曜日': 2, '水曜日': 3, '木曜日': 4, '金曜日': 5, '土曜日': 6, '日曜日': 7}
        schedule_day_of_week = day_name_to_int.get(day_of_week_str)

        start_time_str = first_schedule.get('start_time', '')
        end_time_str = first_schedule.get('end_time', '')
        try:
            if start_time_str:
                parts = start_time_str.split(':')
                schedule_start_time = time(int(parts[0]), int(parts[1]))
            if end_time_str:
                parts = end_time_str.split(':')
                schedule_end_time = time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            pass

    print(f"[PricingConfirm] Parsed schedule: day_of_week={schedule_day_of_week}, start_time={schedule_start_time}, end_time={schedule_end_time}", file=sys.stderr)
    return schedule_day_of_week, schedule_start_time, schedule_end_time, selected_class_schedule


def get_ticket(ticket_id):
    """チケットを取得"""
    if not ticket_id:
        return None
    try:
        from apps.schools.models import Ticket
        ticket = Ticket.objects.get(id=ticket_id)
        print(f"[PricingConfirm] Found ticket: {ticket.ticket_name}", file=sys.stderr)
        return ticket
    except Exception as e:
        print(f"[PricingConfirm] Failed to get ticket: {e}", file=sys.stderr)
        return None


def create_contract(student, school, brand, course, start_date):
    """契約を作成"""
    contract_no = f"C{date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    contract = Contract.objects.create(
        tenant_id=student.tenant_id,
        contract_no=contract_no,
        student=student,
        guardian=student.guardian if student.guardian else None,
        school=school,
        brand=brand,
        course=course,
        contract_date=date.today(),
        start_date=start_date or date.today(),
        status=Contract.Status.ACTIVE,
    )
    print(f"[PricingConfirm] Created Contract: {contract_no}", file=sys.stderr)
    return contract


def create_student_item(student, contract, product, billing_month, order_id,
                        unit_price, quantity, notes_suffix,
                        brand, school, course, start_date,
                        schedule_day_of_week, schedule_start_time, schedule_end_time,
                        selected_class_schedule):
    """StudentItemを作成"""
    return StudentItem.objects.create(
        tenant_id=student.tenant_id,
        student=student,
        contract=contract,
        product=product,
        billing_month=billing_month,
        quantity=quantity,
        unit_price=unit_price,
        discount_amount=0,
        final_price=unit_price * quantity,
        notes=f'注文番号: {order_id} / {notes_suffix}',
        brand=brand,
        school=school,
        course=course,
        start_date=start_date,
        day_of_week=schedule_day_of_week,
        start_time=schedule_start_time,
        end_time=schedule_end_time,
        class_schedule=selected_class_schedule,
    )


def create_student_school(student, school, brand, start_date):
    """StudentSchoolを作成/更新"""
    if not school or not brand:
        return None, False

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

    if created:
        print(f"[PricingConfirm] Created StudentSchool: student={student}, school={school}, brand={brand}", file=sys.stderr)
    else:
        print(f"[PricingConfirm] StudentSchool already exists: student={student}, school={school}, brand={brand}", file=sys.stderr)

    return student_school, created


def create_student_enrollment(student, school, brand, selected_class_schedule,
                               start_date, order_id, product_name,
                               schedule_day_of_week, schedule_start_time, schedule_end_time):
    """StudentEnrollmentを作成"""
    if not school or not brand:
        return None

    enrollment = StudentEnrollment.create_enrollment(
        student=student,
        school=school,
        brand=brand,
        class_schedule=selected_class_schedule,
        change_type=StudentEnrollment.ChangeType.NEW_ENROLLMENT,
        effective_date=start_date or date.today(),
        notes=f'注文番号: {order_id} / {product_name}',
        day_of_week_override=schedule_day_of_week,
        start_time_override=schedule_start_time,
        end_time_override=schedule_end_time,
    )
    print(f"[PricingConfirm] Created StudentEnrollment: student={student}, school={school}, brand={brand}", file=sys.stderr)

    # 生徒のステータスを「入会」に更新
    if student.status in [Student.Status.REGISTERED, Student.Status.TRIAL]:
        student.status = Student.Status.ENROLLED
        student.save(update_fields=['status', 'updated_at'])
        print(f"[PricingConfirm] Updated student status to ENROLLED: {student}", file=sys.stderr)

    return enrollment


def create_purchase_task(student, product_name, order_id, payment_method, billing_month,
                          enrollment_tuition_info, current_month_prorated_info,
                          miles_to_use, mile_discount, course=None, pack=None,
                          school=None, brand=None):
    """購入申請タスクを作成"""
    student_name = f'{student.last_name}{student.first_name}'
    product_type = 'コース' if course else 'パック'

    task_description = f'保護者からの購入申請です。\n\n' \
                       f'生徒: {student_name}\n' \
                       f'{product_type}: {product_name}\n' \
                       f'注文番号: {order_id}\n' \
                       f'支払方法: {payment_method or "未指定"}\n' \
                       f'請求月: {billing_month}'

    if enrollment_tuition_info:
        task_description += f'\n入会時授業料: {enrollment_tuition_info}'
    if current_month_prorated_info:
        task_description += f'\n当月分回数割: {current_month_prorated_info}'
    if mile_discount > 0:
        task_description += f'\nマイル割引: {miles_to_use}pt使用 → ¥{int(mile_discount):,}引'

    metadata = {
        'order_id': order_id,
        'student_id': str(student.id),
        'payment_method': payment_method,
        'billing_month': billing_month,
        'enrollment_tuition': enrollment_tuition_info,
        'current_month_prorated': current_month_prorated_info,
        'miles_used': miles_to_use if mile_discount > 0 else 0,
        'mile_discount': int(mile_discount) if mile_discount > 0 else 0,
    }

    if course:
        metadata['course_id'] = str(course.id)
        use_school = school or (course.school if hasattr(course, 'school') else None)
        use_brand = brand or (course.brand if hasattr(course, 'brand') else None)
    else:
        metadata['pack_id'] = str(pack.id)
        use_school = school
        use_brand = brand

    Task.objects.create(
        tenant_id=student.tenant_id,
        task_type='request',
        title=f'【購入申請】{student_name} - {product_name}',
        description=task_description,
        status='new',
        priority='normal',
        student=student,
        guardian=student.guardian if hasattr(student, 'guardian') else None,
        school=use_school,
        brand=use_brand,
        source_type='purchase',
        source_id=uuid.UUID(order_id.replace('ORD-', '').ljust(32, '0')[:32]) if len(order_id) > 4 else None,
        metadata=metadata,
    )


def record_mile_usage(student, guardian, miles_to_use, mile_discount, order_id, product_name):
    """マイル使用を記録"""
    if miles_to_use <= 0 or mile_discount <= 0 or not guardian or not student:
        return

    current_balance = MileTransaction.get_balance(guardian)
    new_balance = current_balance - miles_to_use

    MileTransaction.objects.create(
        tenant_id=student.tenant_id,
        guardian=guardian,
        transaction_type=MileTransaction.TransactionType.USE,
        miles=-miles_to_use,
        balance_after=new_balance,
        discount_amount=mile_discount,
        notes=f'注文番号: {order_id} / {product_name}',
    )
    print(f"[PricingConfirm] Created MileTransaction: -{miles_to_use}pt, discount=¥{mile_discount}, new_balance={new_balance}", file=sys.stderr)

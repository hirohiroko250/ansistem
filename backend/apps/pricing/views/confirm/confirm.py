"""
Pricing Confirm View - 購入確定API
"""
import sys
import uuid
from datetime import date
from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.contracts.models import Product
from apps.pricing.calculations import calculate_enrollment_fees

from apps.pricing.views.utils import (
    get_product_price_for_enrollment,
    calculate_enrollment_tuition_tickets,
    get_enrollment_tuition_product,
    calculate_prorated_by_day_of_week,
    calculate_prorated_current_month_fees,
)
from .helpers import (
    parse_request_data,
    get_student_and_guardian,
    validate_miles,
    get_course_or_pack,
    get_brand_and_school,
    parse_start_date,
    parse_schedule_info,
    get_ticket,
    create_contract,
    create_student_item,
    create_student_school,
    create_student_enrollment,
    create_purchase_task,
    record_mile_usage,
)


class PricingConfirmView(APIView):
    """購入確定"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """購入を確定する"""
        # リクエスト解析
        data = parse_request_data(request)
        self._log_request(data)

        # 注文ID・請求月
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        billing_month = date.today().strftime('%Y-%m')

        # 生徒・保護者取得
        student, guardian = get_student_and_guardian(data['student_id'])

        # マイルバリデーション
        mile_error, mile_discount = validate_miles(data['miles_to_use'], guardian)
        if mile_error:
            return Response(mile_error, status=400)

        # コース/パック取得
        course, pack = get_course_or_pack(data['course_id'], data['preview_id'])

        # ブランド・校舎・開始日取得
        brand, school = get_brand_and_school(data['brand_id'], data['school_id'])
        start_date = parse_start_date(data['start_date_str'])

        # スケジュール情報解析
        schedule_day_of_week, schedule_start_time, schedule_end_time, selected_class_schedule = \
            parse_schedule_info(data['schedules'])

        # チケット取得
        ticket = get_ticket(data['ticket_id'])

        # 購入処理
        print(f"[PricingConfirm] student={student}, course={course}, pack={pack}, brand={brand}, school={school}, start_date={start_date}", file=sys.stderr)

        enrollment_tuition_info = None
        current_month_prorated_info = None
        product_name_for_task = None

        if student and course:
            enrollment_tuition_info, current_month_prorated_info, product_name_for_task = \
                self._process_course_purchase(
                    student, course, guardian, brand, school, start_date,
                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                    selected_class_schedule, order_id, billing_month,
                    data['payment_method'], data['selected_textbook_ids'],
                    data['miles_to_use'], mile_discount
                )

        elif student and pack:
            enrollment_tuition_info, product_name_for_task = \
                self._process_pack_purchase(
                    student, pack, guardian, brand, school, start_date,
                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                    selected_class_schedule, order_id, billing_month,
                    data['payment_method'], data['miles_to_use'], mile_discount
                )

        # マイル使用記録
        product_name = product_name_for_task or (course.course_name if course else (pack.pack_name if pack else "不明"))
        record_mile_usage(student, guardian, data['miles_to_use'], mile_discount, order_id, product_name)

        return Response({
            'orderId': order_id,
            'status': 'completed',
            'message': '購入申請が完了しました。確認後、ご連絡いたします。',
            'mileDiscount': int(mile_discount) if mile_discount > 0 else 0,
            'milesUsed': data['miles_to_use'] if mile_discount > 0 else 0,
        })

    def _log_request(self, data):
        """リクエストをログ出力"""
        print(f"[PricingConfirm] ========== REQUEST DATA ==========", file=sys.stderr)
        print(f"[PricingConfirm] preview_id={data['preview_id']}, student_id={data['student_id']}, course_id={data['course_id']}", file=sys.stderr)
        print(f"[PricingConfirm] brand_id={data['brand_id']} (type={type(data['brand_id']).__name__})", file=sys.stderr)
        print(f"[PricingConfirm] school_id={data['school_id']} (type={type(data['school_id']).__name__})", file=sys.stderr)
        print(f"[PricingConfirm] start_date={data['start_date_str']} (type={type(data['start_date_str']).__name__})", file=sys.stderr)
        print(f"[PricingConfirm] schedules={data['schedules']}, ticket_id={data['ticket_id']}, miles_to_use={data['miles_to_use']}", file=sys.stderr)
        print(f"[PricingConfirm] selected_textbook_ids={data['selected_textbook_ids']} (type={type(data['selected_textbook_ids']).__name__}, len={len(data['selected_textbook_ids']) if data['selected_textbook_ids'] else 0})", file=sys.stderr)
        print(f"[PricingConfirm] ===================================", file=sys.stderr)

    def _process_course_purchase(self, student, course, guardian, brand, school, start_date,
                                   schedule_day_of_week, schedule_start_time, schedule_end_time,
                                   selected_class_schedule, order_id, billing_month,
                                   payment_method, selected_textbook_ids, miles_to_use, mile_discount):
        """コース購入処理"""
        # 契約作成
        contract = create_contract(student, school, brand, course, start_date)

        # コースアイテムからStudentItem作成
        course_items = course.course_items.filter(is_active=True)
        print(f"[PricingConfirm] Found {course_items.count()} course_items", file=sys.stderr)

        for course_item in course_items:
            product = course_item.product
            if product and product.item_type == 'textbook':
                print(f"[PricingConfirm] Skipping textbook from CourseItem: {product.product_name}", file=sys.stderr)
                continue

            create_student_item(
                student, contract, product, billing_month, order_id,
                course_item.get_price(), course_item.quantity,
                f'コース: {course.course_name}',
                brand, school, course, start_date,
                schedule_day_of_week, schedule_start_time, schedule_end_time,
                selected_class_schedule
            )

        # 選択された教材費
        self._create_selected_textbooks(
            student, contract, selected_textbook_ids, billing_month, order_id,
            brand, school, course, start_date,
            schedule_day_of_week, schedule_start_time, schedule_end_time,
            selected_class_schedule
        )

        # StudentSchool作成
        create_student_school(student, school, brand, start_date)

        # StudentEnrollment作成
        create_student_enrollment(
            student, school, brand, selected_class_schedule,
            start_date, order_id, f'コース: {course.course_name}',
            schedule_day_of_week, schedule_start_time, schedule_end_time
        )

        # 入会時費用計算・作成
        enrollment_tuition_info = None
        if start_date and schedule_day_of_week:
            enrollment_tuition_info = self._create_enrollment_fees(
                student, contract, course, guardian, start_date, schedule_day_of_week,
                billing_month, order_id, brand, school,
                schedule_start_time, schedule_end_time, selected_class_schedule
            )

        # 当月分回数割
        current_month_prorated_info = None
        if start_date and schedule_day_of_week and start_date.day > 1:
            current_month_prorated_info = self._create_prorated_fees(
                student, contract, course, start_date, schedule_day_of_week,
                billing_month, order_id, brand, school,
                schedule_start_time, schedule_end_time, selected_class_schedule
            )

        # タスク作成
        create_purchase_task(
            student, course.course_name, order_id, payment_method, billing_month,
            enrollment_tuition_info, current_month_prorated_info,
            miles_to_use, mile_discount, course=course, school=school, brand=brand
        )

        return enrollment_tuition_info, current_month_prorated_info, course.course_name

    def _process_pack_purchase(self, student, pack, guardian, brand, school, start_date,
                                schedule_day_of_week, schedule_start_time, schedule_end_time,
                                selected_class_schedule, order_id, billing_month,
                                payment_method, miles_to_use, mile_discount):
        """パック購入処理"""
        # 契約作成
        contract = create_contract(student, school, brand, None, start_date)
        print(f"[PricingConfirm] Created Contract for Pack: {contract.contract_no}", file=sys.stderr)

        enrollment_tuition_info = None

        # パック内コース処理
        pack_courses = pack.pack_courses.filter(is_active=True).select_related('course')
        print(f"[PricingConfirm] Found pack with {pack_courses.count()} courses", file=sys.stderr)

        for pack_course in pack_courses:
            pc_course = pack_course.course
            if not pc_course:
                continue

            course_items = pc_course.course_items.filter(is_active=True)
            for course_item in course_items:
                product = course_item.product
                create_student_item(
                    student, contract, product, billing_month, order_id,
                    course_item.get_price(), course_item.quantity,
                    f'パック: {pack.pack_name} / コース: {pc_course.course_name}',
                    brand or pc_course.brand, school or pc_course.school, pc_course, start_date,
                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                    selected_class_schedule
                )

            # 入会時授業料
            if start_date and start_date.day > 1:
                tickets = calculate_enrollment_tuition_tickets(start_date)
                enrollment_product = get_enrollment_tuition_product(pc_course, tickets)

                if enrollment_product:
                    enrollment_price = get_product_price_for_enrollment(enrollment_product, start_date)
                    create_student_item(
                        student, contract, enrollment_product, billing_month, order_id,
                        enrollment_price, 1,
                        f'入会時授業料（{tickets}回分）/ コース: {pc_course.course_name}',
                        brand or pc_course.brand, school or pc_course.school, pc_course, start_date,
                        schedule_day_of_week, schedule_start_time, schedule_end_time,
                        selected_class_schedule
                    )
                    info = f'{enrollment_product.product_name} ¥{int(enrollment_price):,}'
                    enrollment_tuition_info = f'{enrollment_tuition_info} / {info}' if enrollment_tuition_info else info

        # パック直接商品
        pack_items = pack.pack_items.filter(is_active=True).select_related('product')
        for pack_item in pack_items:
            product = pack_item.product
            create_student_item(
                student, contract, product, billing_month, order_id,
                pack_item.get_price(), pack_item.quantity,
                f'パック: {pack.pack_name}',
                brand or pack.brand, school or pack.school, None, start_date,
                schedule_day_of_week, schedule_start_time, schedule_end_time,
                selected_class_schedule
            )

        # StudentSchool・Enrollment作成
        use_brand = brand or pack.brand
        use_school = school or pack.school
        create_student_school(student, use_school, use_brand, start_date)
        create_student_enrollment(
            student, use_school, use_brand, selected_class_schedule,
            start_date, order_id, f'パック: {pack.pack_name}',
            schedule_day_of_week, schedule_start_time, schedule_end_time
        )

        # タスク作成
        create_purchase_task(
            student, pack.pack_name, order_id, payment_method, billing_month,
            enrollment_tuition_info, None,
            miles_to_use, mile_discount, pack=pack, school=use_school, brand=use_brand
        )

        return enrollment_tuition_info, pack.pack_name

    def _create_selected_textbooks(self, student, contract, selected_textbook_ids,
                                    billing_month, order_id, brand, school, course, start_date,
                                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                                    selected_class_schedule):
        """選択された教材費のStudentItemを作成"""
        print(f"[PricingConfirm] _create_selected_textbooks called with: selected_textbook_ids={selected_textbook_ids}", file=sys.stderr)
        if not selected_textbook_ids:
            print(f"[PricingConfirm] No textbook IDs provided, skipping textbook creation", file=sys.stderr)
            return

        enrollment_month = start_date.month if start_date else None
        print(f"[PricingConfirm] Creating textbooks with enrollment_month={enrollment_month}", file=sys.stderr)
        for textbook_id in selected_textbook_ids:
            try:
                textbook_product = Product.objects.get(id=textbook_id)
                if enrollment_month:
                    unit_price = Decimal(str(textbook_product.get_price_for_enrollment_month(enrollment_month)))
                else:
                    unit_price = textbook_product.base_price or Decimal('0')

                create_student_item(
                    student, contract, textbook_product, billing_month, order_id,
                    unit_price, 1,
                    f'教材費（選択・{enrollment_month}月入会）: {textbook_product.product_name}',
                    brand, school, course, start_date,
                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                    selected_class_schedule
                )
                print(f"[PricingConfirm] Created selected textbook StudentItem: {textbook_product.product_name} = ¥{unit_price}", file=sys.stderr)

            except Product.DoesNotExist:
                print(f"[PricingConfirm] Selected textbook not found: {textbook_id}", file=sys.stderr)

    def _create_enrollment_fees(self, student, contract, course, guardian, start_date,
                                 schedule_day_of_week, billing_month, order_id,
                                 brand, school, schedule_start_time, schedule_end_time,
                                 selected_class_schedule):
        """入会時費用を計算してStudentItemを作成"""
        enrollment_tuition_info = None

        try:
            prorated_info = calculate_prorated_by_day_of_week(start_date, schedule_day_of_week)
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
                        print(f"[PricingConfirm] Product not found: {fee['product_id']}", file=sys.stderr)
                        continue

                    create_student_item(
                        student, contract, product, billing_month, order_id,
                        fee['calculated_price'], 1, fee['calculation_detail'],
                        brand, school, course, start_date,
                        schedule_day_of_week, schedule_start_time, schedule_end_time,
                        selected_class_schedule
                    )
                    print(f"[PricingConfirm] Created enrollment StudentItem: {fee['item_type']} = ¥{fee['calculated_price']}", file=sys.stderr)

                    if fee['item_type'] == 'enrollment_tuition':
                        enrollment_tuition_info = f"{fee['product_name']} ¥{fee['calculated_price']:,}"

        except Exception as e:
            print(f"[PricingConfirm] Error creating enrollment fees: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

        return enrollment_tuition_info

    def _create_prorated_fees(self, student, contract, course, start_date,
                               schedule_day_of_week, billing_month, order_id,
                               brand, school, schedule_start_time, schedule_end_time,
                               selected_class_schedule):
        """当月分回数割料金を作成"""
        prorated_data = calculate_prorated_current_month_fees(course, start_date, schedule_day_of_week)
        if prorated_data['total_prorated'] <= 0:
            return None

        prorated_items = []

        # 授業料
        if prorated_data['tuition']:
            self._create_prorated_item(
                student, contract, prorated_data['tuition'], '授業料',
                billing_month, order_id, brand, school, course, start_date,
                schedule_day_of_week, schedule_start_time, schedule_end_time,
                selected_class_schedule
            )
            prorated_items.append(f'授業料 ¥{prorated_data["tuition"]["prorated_price"]:,}')

        # 設備費
        if prorated_data['facility_fee']:
            self._create_prorated_item(
                student, contract, prorated_data['facility_fee'], '設備費',
                billing_month, order_id, brand, school, course, start_date,
                schedule_day_of_week, schedule_start_time, schedule_end_time,
                selected_class_schedule
            )
            prorated_items.append(f'設備費 ¥{prorated_data["facility_fee"]["prorated_price"]:,}')

        # 月会費
        if prorated_data['monthly_fee']:
            self._create_prorated_item(
                student, contract, prorated_data['monthly_fee'], '月会費',
                billing_month, order_id, brand, school, course, start_date,
                schedule_day_of_week, schedule_start_time, schedule_end_time,
                selected_class_schedule
            )
            prorated_items.append(f'月会費 ¥{prorated_data["monthly_fee"]["prorated_price"]:,}')

        if prorated_items:
            return ' / '.join(prorated_items) + f' (合計 ¥{prorated_data["total_prorated"]:,})'
        return None

    def _create_prorated_item(self, student, contract, item_data, fee_name,
                               billing_month, order_id, brand, school, course, start_date,
                               schedule_day_of_week, schedule_start_time, schedule_end_time,
                               selected_class_schedule):
        """回数割アイテムを作成"""
        notes = f'当月分{fee_name}（回数割 {item_data["remaining_count"]}/{item_data["total_count"]}回）'
        create_student_item(
            student, contract, item_data['product'], billing_month, order_id,
            item_data['prorated_price'], 1, notes,
            brand, school, course, start_date,
            schedule_day_of_week, schedule_start_time, schedule_end_time,
            selected_class_schedule
        )
        print(f"[PricingConfirm] Created prorated {fee_name} StudentItem: ¥{item_data['prorated_price']}", file=sys.stderr)

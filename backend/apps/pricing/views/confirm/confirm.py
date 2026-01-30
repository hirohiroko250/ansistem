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

from apps.contracts.models import Product, CourseItem
from apps.pricing.calculations import calculate_enrollment_fees
from apps.core.exceptions import OZAException

from apps.pricing.views.utils import (
    get_product_price_for_enrollment,
    calculate_enrollment_tuition_tickets,
    get_enrollment_tuition_product,
    calculate_prorated_by_day_of_week,
    calculate_prorated_current_month_fees,
    get_monthly_tuition_prices,
)
from .helpers import (
    parse_request_data,
    get_student_and_guardian,
    validate_miles,
    get_course_or_pack,
    get_brand_and_school,
    parse_start_date,
    parse_schedule_info,
    parse_all_schedules,
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

    def _calculate_billing_months(self, start_date):
        """前払い制の請求月を計算

        締日ロジック：
        - 各月の請求締日は前月15日前後
        - 例: 2月請求の締め = 1月15日
        - 締日を過ぎた場合、その月の請求には含められない

        Args:
            start_date: 入会開始日

        Returns:
            dict: {
                'billingMonth': str,       # 実際の請求月 (2026-03形式) - 全アイテムに使用
                'serviceMonths': list,     # サービス提供月のリスト (notes用)
                'currentMonthLabel': str,  # 当月ラベル (例: "1月")
                'month1Label': str,        # 翌月ラベル (例: "2月")
                'month2Label': str,        # 翌々月ラベル (例: "3月")
            }
        """
        from apps.billing.models import BillingPeriod

        today = date.today()
        if start_date:
            base_date = start_date
        else:
            base_date = today

        # サービス提供月を計算
        current_month = base_date.month
        current_year = base_date.year

        month1_num = (current_month % 12) + 1
        year1 = current_year if month1_num > current_month else current_year + 1

        month2_num = ((current_month + 1) % 12) + 1
        year2 = current_year if month2_num > current_month else current_year + 1

        # 次の未確定の請求月を探す
        # 今月から順番にチェックして、最初の未確定月を見つける
        billing_month = None
        billing_year = today.year
        billing_month_num = today.month

        for offset in range(6):  # 最大6ヶ月先まで確認
            check_month = ((today.month - 1 + offset) % 12) + 1
            check_year = today.year + ((today.month - 1 + offset) // 12)

            is_confirmed = BillingPeriod.objects.filter(
                year=check_year,
                month=check_month,
                is_closed=True,
            ).exists()

            if not is_confirmed:
                billing_year = check_year
                billing_month_num = check_month
                billing_month = f'{check_year}-{check_month:02d}'
                print(f"[PricingConfirm] Found next open billing period: {billing_month}", file=sys.stderr)
                break

        # 見つからない場合は3ヶ月後をデフォルトにする
        if not billing_month:
            fallback_month = ((today.month + 1) % 12) + 1
            fallback_year = today.year if fallback_month > today.month else today.year + 1
            billing_month = f'{fallback_year}-{fallback_month:02d}'
            print(f"[PricingConfirm] No open billing period found, using fallback: {billing_month}", file=sys.stderr)

        return {
            'billingMonth': billing_month,  # 全アイテムで使用する請求月
            'serviceMonths': [
                {'month': current_month, 'year': current_year, 'label': f'{current_month}月分（当月）'},
                {'month': month1_num, 'year': year1, 'label': f'{month1_num}月分'},
                {'month': month2_num, 'year': year2, 'label': f'{month2_num}月分'},
            ],
            'currentMonthLabel': f'{current_month}月',
            'month1Label': f'{month1_num}月',
            'month2Label': f'{month2_num}月',
        }

    def post(self, request):
        """購入を確定する"""
        import logging
        logger = logging.getLogger(__name__)
        try:
            return self._process_post(request)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"[PricingConfirm] ERROR: {e}\n{error_trace}")
            print(f"[PricingConfirm] ERROR: {e}", flush=True)
            print(error_trace, flush=True)
            raise OZAException(str(e), status_code=500)

    def _process_post(self, request):
        """購入確定の実処理"""
        # リクエスト解析
        data = parse_request_data(request)
        self._log_request(data)

        # 注文ID
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

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

        # ブランド・校舎のフォールバック（リクエストに含まれない場合）
        if not brand:
            if course and getattr(course, 'brand', None):
                brand = course.brand
            elif pack and getattr(pack, 'brand', None):
                brand = pack.brand
            elif student and getattr(student, 'primary_brand', None):
                brand = student.primary_brand
            if brand:
                print(f"[PricingConfirm] Brand resolved via fallback: {brand}", file=sys.stderr)

        if not school:
            if course and getattr(course, 'school', None):
                school = course.school
            elif pack and getattr(pack, 'school', None):
                school = pack.school
            elif student and getattr(student, 'primary_school', None):
                school = student.primary_school
            if school:
                print(f"[PricingConfirm] School resolved via fallback: {school}", file=sys.stderr)

        # スケジュール情報解析（最初の1件 + 全件）
        schedule_day_of_week, schedule_start_time, schedule_end_time, selected_class_schedule = \
            parse_schedule_info(data['schedules'])
        all_schedules = parse_all_schedules(data['schedules'])

        # チケット取得
        ticket = get_ticket(data['ticket_id'])

        # 重複購入チェック（べき等性）
        duplicate_result = self._check_duplicate_purchase(
            student, course, pack, selected_class_schedule, schedule_day_of_week, schedule_start_time
        )
        if duplicate_result:
            print(f"[PricingConfirm] Duplicate purchase detected, returning existing order", file=sys.stderr)
            return Response(duplicate_result)

        # 前払い制の請求月を計算
        billing_months = self._calculate_billing_months(start_date)
        print(f"[PricingConfirm] billing_months={billing_months}", file=sys.stderr)

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
                    selected_class_schedule, order_id, billing_months,
                    data['payment_method'], data['selected_textbook_ids'],
                    data['miles_to_use'], mile_discount,
                    all_schedules=all_schedules
                )

        elif student and pack:
            enrollment_tuition_info, product_name_for_task = \
                self._process_pack_purchase(
                    student, pack, guardian, brand, school, start_date,
                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                    selected_class_schedule, order_id, billing_months,
                    data['payment_method'], data['miles_to_use'], mile_discount,
                    all_schedules=all_schedules
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

    def _check_duplicate_purchase(self, student, course, pack, selected_class_schedule,
                                   schedule_day_of_week, schedule_start_time):
        """重複購入チェック（べき等性のため）

        同じ生徒・コース・クラスの組み合わせで既に購入済みの場合、
        成功レスポンスを返して重複作成を防ぐ
        """
        from apps.contracts.models import StudentItem

        if not student:
            return None

        # コース購入の重複チェック
        if course:
            existing = StudentItem.objects.filter(
                student=student,
                course=course,
                class_schedule=selected_class_schedule,
                day_of_week=schedule_day_of_week,
                start_time=schedule_start_time,
                deleted_at__isnull=True,
            ).first()

            if existing:
                print(f"[PricingConfirm] Found existing StudentItem: {existing.id} for course={course.course_name}", file=sys.stderr)
                return {
                    'orderId': existing.notes.split('注文番号: ')[1].split(' /')[0] if '注文番号:' in (existing.notes or '') else 'EXISTING',
                    'status': 'already_completed',
                    'message': 'この購入は既に完了しています。',
                    'mileDiscount': 0,
                    'milesUsed': 0,
                }

        # パック購入の重複チェック
        if pack:
            # パックの場合はパック内のコースで確認
            existing = StudentItem.objects.filter(
                student=student,
                class_schedule=selected_class_schedule,
                day_of_week=schedule_day_of_week,
                start_time=schedule_start_time,
                deleted_at__isnull=True,
                notes__contains=pack.pack_name,
            ).first()

            if existing:
                print(f"[PricingConfirm] Found existing StudentItem: {existing.id} for pack={pack.pack_name}", file=sys.stderr)
                return {
                    'orderId': existing.notes.split('注文番号: ')[1].split(' /')[0] if '注文番号:' in (existing.notes or '') else 'EXISTING',
                    'status': 'already_completed',
                    'message': 'この購入は既に完了しています。',
                    'mileDiscount': 0,
                    'milesUsed': 0,
                }

        return None

    def _process_course_purchase(self, student, course, guardian, brand, school, start_date,
                                   schedule_day_of_week, schedule_start_time, schedule_end_time,
                                   selected_class_schedule, order_id, billing_months,
                                   payment_method, selected_textbook_ids, miles_to_use, mile_discount,
                                   all_schedules=None):
        """コース購入処理（前払い制対応・合算請求）

        全てのアイテムを同じ請求月（次の未確定請求期間）に合算する。
        例: 1月16日入会で1月・2月請求確定済の場合
            → 1月分（日割）+ 2月分 + 3月分 を全て「3月請求」に合算

        Args:
            billing_months: {
                'billingMonth': str,       # 実際の請求月（全アイテム共通）
                'serviceMonths': list,     # サービス提供月のリスト
                'currentMonthLabel': str,
                'month1Label': str,
                'month2Label': str,
            }
        """
        # 契約作成
        contract = create_contract(student, school, brand, course, start_date)

        # 全アイテムに使用する請求月
        billing_month = billing_months['billingMonth']
        service_months = billing_months['serviceMonths']

        print(f"[PricingConfirm] All items will use billing_month: {billing_month}", file=sys.stderr)

        # コースアイテムからStudentItem作成
        course_items = course.course_items.filter(is_active=True)
        print(f"[PricingConfirm] Found {course_items.count()} course_items", file=sys.stderr)

        # 月額料金のタイプ
        recurring_types = ['tuition', 'monthly_fee', 'facility']

        for course_item in course_items:
            product = course_item.product
            if product and product.item_type == 'textbook':
                print(f"[PricingConfirm] Skipping textbook from CourseItem: {product.product_name}", file=sys.stderr)
                continue

            # 入会月別料金を使用（start_dateがある場合）
            if start_date and product:
                unit_price = get_product_price_for_enrollment(product, start_date)
                print(f"[PricingConfirm] Using enrollment month price for {product.product_name}: ¥{unit_price} (month={start_date.month})", file=sys.stderr)
            else:
                unit_price = course_item.get_price()
                print(f"[PricingConfirm] Using base price for {product.product_name if product else 'unknown'}: ¥{unit_price}", file=sys.stderr)

            # 月額料金（tuition, monthly_fee, facility）の場合は各サービス月分を作成
            if product and product.item_type in recurring_types:
                # 翌月分（2月）
                month1_label = service_months[1]['label'] if len(service_months) > 1 else '翌月分'
                create_student_item(
                    student, contract, product, billing_month, order_id,
                    unit_price, course_item.quantity,
                    f'コース: {course.course_name} / {month1_label}',
                    brand, school, course, start_date,
                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                    selected_class_schedule
                )
                print(f"[PricingConfirm] Created StudentItem for {month1_label}: {product.product_name}", file=sys.stderr)

                # 翌々月分（3月）
                month2_label = service_months[2]['label'] if len(service_months) > 2 else '翌々月分'
                create_student_item(
                    student, contract, product, billing_month, order_id,
                    unit_price, course_item.quantity,
                    f'コース: {course.course_name} / {month2_label}',
                    brand, school, course, start_date,
                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                    selected_class_schedule
                )
                print(f"[PricingConfirm] Created StudentItem for {month2_label}: {product.product_name}", file=sys.stderr)
            else:
                # 入会金等の一回のみの費用
                create_student_item(
                    student, contract, product, billing_month, order_id,
                    unit_price, course_item.quantity,
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

        # StudentEnrollment作成（複数曜日対応）
        if all_schedules and len(all_schedules) > 1:
            # 複数スケジュール: 各曜日ごとにEnrollmentを作成
            print(f"[PricingConfirm] Creating {len(all_schedules)} enrollments for multiple schedules", file=sys.stderr)
            for idx, sched in enumerate(all_schedules):
                sched_school = sched.get('school') or school
                create_student_enrollment(
                    student, sched_school, brand, sched['class_schedule'],
                    start_date, order_id, f'コース: {course.course_name}',
                    sched['day_of_week'], sched['start_time'], sched['end_time'],
                    is_additional=(idx > 0)  # 2つ目以降は既存を終了しない
                )
                # 追加校舎がある場合はStudentSchoolも作成
                if sched_school and sched_school != school:
                    create_student_school(student, sched_school, brand, start_date)

            # 追加曜日のStudentItem作成（カレンダー表示用）
            # カレンダーはStudentItemのclass_schedule_idを参照するため、
            # 2つ目以降のスケジュールにも紐付くStudentItemが必要
            tuition_product = None
            for ci in course_items:
                if ci.product and ci.product.item_type == 'tuition':
                    tuition_product = ci.product
                    break

            for idx, sched in enumerate(all_schedules[1:], 2):
                sched_school = sched.get('school') or school
                ref_product = tuition_product or (course_items.first().product if course_items.exists() else None)
                if ref_product:
                    create_student_item(
                        student, contract, ref_product, billing_month, order_id,
                        Decimal('0'), 1,
                        f'コース: {course.course_name} / 追加曜日{idx}登録',
                        brand, sched_school, course, start_date,
                        sched['day_of_week'], sched['start_time'], sched['end_time'],
                        sched['class_schedule']
                    )
                    print(f"[PricingConfirm] Created additional schedule StudentItem for day={sched['day_of_week']}", file=sys.stderr)
        else:
            # 単一スケジュール（従来通り）
            create_student_enrollment(
                student, school, brand, selected_class_schedule,
                start_date, order_id, f'コース: {course.course_name}',
                schedule_day_of_week, schedule_start_time, schedule_end_time
            )

        # 入会時費用計算・作成（当月日割分）
        enrollment_tuition_info = None
        if start_date and schedule_day_of_week:
            enrollment_tuition_info = self._create_enrollment_fees(
                student, contract, course, guardian, start_date, schedule_day_of_week,
                billing_month, order_id, brand, school,
                schedule_start_time, schedule_end_time, selected_class_schedule
            )

        # 当月分回数割（日割）
        current_month_prorated_info = None
        if start_date and schedule_day_of_week and start_date.day > 1:
            current_month_label = service_months[0]['label'] if service_months else '当月分'
            current_month_prorated_info = self._create_prorated_fees(
                student, contract, course, start_date, schedule_day_of_week,
                billing_month, order_id, brand, school,
                schedule_start_time, schedule_end_time, selected_class_schedule,
                current_month_label
            )

        # タスク作成
        service_month_labels = ' / '.join([m['label'] for m in service_months])
        billing_summary = f"請求月: {billing_month} ({service_month_labels})"
        create_purchase_task(
            student, course.course_name, order_id, payment_method, billing_summary,
            enrollment_tuition_info, current_month_prorated_info,
            miles_to_use, mile_discount, course=course, school=school, brand=brand
        )

        return enrollment_tuition_info, current_month_prorated_info, course.course_name

    def _process_pack_purchase(self, student, pack, guardian, brand, school, start_date,
                                schedule_day_of_week, schedule_start_time, schedule_end_time,
                                selected_class_schedule, order_id, billing_months,
                                payment_method, miles_to_use, mile_discount,
                                all_schedules=None):
        """パック購入処理（前払い制対応・合算請求）

        全てのアイテムを同じ請求月（次の未確定請求期間）に合算する。
        """
        # 契約作成
        contract = create_contract(student, school, brand, None, start_date)
        print(f"[PricingConfirm] Created Contract for Pack: {contract.contract_no}", file=sys.stderr)

        # 全アイテムに使用する請求月
        billing_month = billing_months['billingMonth']
        service_months = billing_months['serviceMonths']
        enrollment_tuition_info = None

        print(f"[PricingConfirm] All pack items will use billing_month: {billing_month}", file=sys.stderr)

        # 月額料金のタイプ
        recurring_types = ['tuition', 'monthly_fee', 'facility']

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
                # 入会月別料金を使用（start_dateがある場合）
                if start_date and product:
                    unit_price = get_product_price_for_enrollment(product, start_date)
                    print(f"[PricingConfirm] Pack: Using enrollment month price for {product.product_name}: ¥{unit_price} (month={start_date.month})", file=sys.stderr)
                else:
                    unit_price = course_item.get_price()

                # 月額料金は各サービス月分を作成（全て同じ請求月billing_monthに合算）
                if product and product.item_type in recurring_types:
                    # 翌月分
                    month1_label = service_months[1]['label'] if len(service_months) > 1 else '翌月分'
                    create_student_item(
                        student, contract, product, billing_month, order_id,
                        unit_price, course_item.quantity,
                        f'パック: {pack.pack_name} / コース: {pc_course.course_name} / {month1_label}',
                        brand or pc_course.brand, school or pc_course.school, pc_course, start_date,
                        schedule_day_of_week, schedule_start_time, schedule_end_time,
                        selected_class_schedule
                    )
                    # 翌々月分
                    month2_label = service_months[2]['label'] if len(service_months) > 2 else '翌々月分'
                    create_student_item(
                        student, contract, product, billing_month, order_id,
                        unit_price, course_item.quantity,
                        f'パック: {pack.pack_name} / コース: {pc_course.course_name} / {month2_label}',
                        brand or pc_course.brand, school or pc_course.school, pc_course, start_date,
                        schedule_day_of_week, schedule_start_time, schedule_end_time,
                        selected_class_schedule
                    )
                else:
                    create_student_item(
                        student, contract, product, billing_month, order_id,
                        unit_price, course_item.quantity,
                        f'パック: {pack.pack_name} / コース: {pc_course.course_name}',
                        brand or pc_course.brand, school or pc_course.school, pc_course, start_date,
                        schedule_day_of_week, schedule_start_time, schedule_end_time,
                        selected_class_schedule
                    )

            # 入会時授業料（日割分）
            if start_date and start_date.day > 1:
                tickets = calculate_enrollment_tuition_tickets(start_date)
                enrollment_product = get_enrollment_tuition_product(pc_course, tickets)

                if enrollment_product:
                    current_month_label = service_months[0]['label'] if service_months else '当月分'
                    enrollment_price = get_product_price_for_enrollment(enrollment_product, start_date)
                    create_student_item(
                        student, contract, enrollment_product, billing_month, order_id,
                        enrollment_price, 1,
                        f'入会時授業料（{tickets}回分）/ コース: {pc_course.course_name} / {current_month_label}',
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
            # 入会月別料金を使用（start_dateがある場合）
            if start_date and product:
                unit_price = get_product_price_for_enrollment(product, start_date)
                print(f"[PricingConfirm] PackItem: Using enrollment month price for {product.product_name}: ¥{unit_price} (month={start_date.month})", file=sys.stderr)
            else:
                unit_price = pack_item.get_price()

            # 月額料金は各サービス月分を作成
            if product and product.item_type in recurring_types:
                month1_label = service_months[1]['label'] if len(service_months) > 1 else '翌月分'
                create_student_item(
                    student, contract, product, billing_month, order_id,
                    unit_price, pack_item.quantity,
                    f'パック: {pack.pack_name} / {month1_label}',
                    brand or pack.brand, school or pack.school, None, start_date,
                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                    selected_class_schedule
                )
                month2_label = service_months[2]['label'] if len(service_months) > 2 else '翌々月分'
                create_student_item(
                    student, contract, product, billing_month, order_id,
                    unit_price, pack_item.quantity,
                    f'パック: {pack.pack_name} / {month2_label}',
                    brand or pack.brand, school or pack.school, None, start_date,
                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                    selected_class_schedule
                )
            else:
                create_student_item(
                    student, contract, product, billing_month, order_id,
                    unit_price, pack_item.quantity,
                    f'パック: {pack.pack_name}',
                    brand or pack.brand, school or pack.school, None, start_date,
                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                    selected_class_schedule
                )

        # StudentSchool・Enrollment作成（複数曜日対応）
        use_brand = brand or pack.brand
        use_school = school or pack.school
        create_student_school(student, use_school, use_brand, start_date)

        if all_schedules and len(all_schedules) > 1:
            # 複数スケジュール: 各曜日ごとにEnrollmentを作成
            print(f"[PricingConfirm] Pack: Creating {len(all_schedules)} enrollments for multiple schedules", file=sys.stderr)
            for idx, sched in enumerate(all_schedules):
                sched_school = sched.get('school') or use_school
                create_student_enrollment(
                    student, sched_school, use_brand, sched['class_schedule'],
                    start_date, order_id, f'パック: {pack.pack_name}',
                    sched['day_of_week'], sched['start_time'], sched['end_time'],
                    is_additional=(idx > 0)
                )
                if sched_school and sched_school != use_school:
                    create_student_school(student, sched_school, use_brand, start_date)

            # 追加曜日のStudentItem作成（カレンダー表示用）
            first_product = None
            for pc in pack_courses:
                if pc.course:
                    ci = pc.course.course_items.filter(is_active=True, product__item_type='tuition').first()
                    if ci and ci.product:
                        first_product = ci.product
                        break

            for idx, sched in enumerate(all_schedules[1:], 2):
                sched_school = sched.get('school') or use_school
                if first_product:
                    create_student_item(
                        student, contract, first_product, billing_month, order_id,
                        Decimal('0'), 1,
                        f'パック: {pack.pack_name} / 追加曜日{idx}登録',
                        use_brand, sched_school, None, start_date,
                        sched['day_of_week'], sched['start_time'], sched['end_time'],
                        sched['class_schedule']
                    )
                    print(f"[PricingConfirm] Pack: Created additional schedule StudentItem for day={sched['day_of_week']}", file=sys.stderr)
        else:
            create_student_enrollment(
                student, use_school, use_brand, selected_class_schedule,
                start_date, order_id, f'パック: {pack.pack_name}',
                schedule_day_of_week, schedule_start_time, schedule_end_time
            )

        # タスク作成
        service_month_labels = ' / '.join([m['label'] for m in service_months])
        billing_summary = f"請求月: {billing_month} ({service_month_labels})"
        create_purchase_task(
            student, pack.pack_name, order_id, payment_method, billing_summary,
            enrollment_tuition_info, None,
            miles_to_use, mile_discount, pack=pack, school=use_school, brand=use_brand
        )

        return enrollment_tuition_info, pack.pack_name

    def _create_selected_textbooks(self, student, contract, selected_textbook_ids,
                                    billing_month, order_id, brand, school, course, start_date,
                                    schedule_day_of_week, schedule_start_time, schedule_end_time,
                                    selected_class_schedule):
        """選択された教材費のStudentItemを作成し、Contractに保存"""
        print(f"[PricingConfirm] _create_selected_textbooks called with: selected_textbook_ids={selected_textbook_ids}", file=sys.stderr)
        if not selected_textbook_ids:
            print(f"[PricingConfirm] No textbook IDs provided, skipping textbook creation", file=sys.stderr)
            return

        enrollment_month = start_date.month if start_date else None
        print(f"[PricingConfirm] Creating textbooks with enrollment_month={enrollment_month}", file=sys.stderr)

        # 選択された教材を取得してContractに保存
        selected_products = []
        for textbook_id in selected_textbook_ids:
            try:
                textbook_product = Product.objects.get(id=textbook_id)
                selected_products.append(textbook_product)

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

        # Contract.selected_textbooksに保存
        if selected_products and contract:
            contract.selected_textbooks.set(selected_products)
            print(f"[PricingConfirm] Saved {len(selected_products)} textbooks to Contract.selected_textbooks", file=sys.stderr)

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
                               selected_class_schedule, current_month_label='当月分'):
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
                selected_class_schedule, current_month_label
            )
            prorated_items.append(f'授業料 ¥{prorated_data["tuition"]["prorated_price"]:,}')

        # 設備費
        if prorated_data['facility_fee']:
            self._create_prorated_item(
                student, contract, prorated_data['facility_fee'], '設備費',
                billing_month, order_id, brand, school, course, start_date,
                schedule_day_of_week, schedule_start_time, schedule_end_time,
                selected_class_schedule, current_month_label
            )
            prorated_items.append(f'設備費 ¥{prorated_data["facility_fee"]["prorated_price"]:,}')

        # 月会費
        if prorated_data['monthly_fee']:
            self._create_prorated_item(
                student, contract, prorated_data['monthly_fee'], '月会費',
                billing_month, order_id, brand, school, course, start_date,
                schedule_day_of_week, schedule_start_time, schedule_end_time,
                selected_class_schedule, current_month_label
            )
            prorated_items.append(f'月会費 ¥{prorated_data["monthly_fee"]["prorated_price"]:,}')

        if prorated_items:
            return ' / '.join(prorated_items) + f' (合計 ¥{prorated_data["total_prorated"]:,})'
        return None

    def _create_prorated_item(self, student, contract, item_data, fee_name,
                               billing_month, order_id, brand, school, course, start_date,
                               schedule_day_of_week, schedule_start_time, schedule_end_time,
                               selected_class_schedule, month_label='当月分'):
        """回数割アイテムを作成"""
        notes = f'{month_label}{fee_name}（回数割 {item_data["remaining_count"]}/{item_data["total_count"]}回）'
        create_student_item(
            student, contract, item_data['product'], billing_month, order_id,
            item_data['prorated_price'], 1, notes,
            brand, school, course, start_date,
            schedule_day_of_week, schedule_start_time, schedule_end_time,
            selected_class_schedule
        )
        print(f"[PricingConfirm] Created prorated {fee_name} StudentItem: ¥{item_data['prorated_price']}", file=sys.stderr)

"""
Pricing views - 料金計算・購入確認API
"""
import sys
import uuid
from datetime import date, datetime
from decimal import Decimal
from calendar import monthrange
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.contracts.models import Course, StudentItem, Product
from apps.students.models import Student
from apps.tasks.models import Task
from apps.schools.models import Brand, School


def calculate_enrollment_tuition_tickets(start_date: date) -> int:
    """
    入会日から当月の追加チケット枚数を計算

    月途中入会の場合、残り週数に応じてチケット枚数を決定:
    - 1日〜10日入会: 3チケット（残り3週以上）
    - 11日〜20日入会: 2チケット（残り2週程度）
    - 21日以降入会: 1チケット（残り1週程度）
    """
    day = start_date.day

    if day <= 10:
        return 3
    elif day <= 20:
        return 2
    else:
        return 1


def get_enrollment_tuition_product(course: Course, tickets: int) -> Product:
    """
    コースに対応する入会時授業料商品を取得

    商品コード体系: {course_code_prefix}_51 (1回分), _52 (2回分), _53 (3回分)
    """
    if not course or tickets < 1 or tickets > 3:
        return None

    # コースコードから商品コードプレフィックスを推測
    # 例: "24AEC_1000009" → "24AEC_1000009_5X"
    course_code = course.course_code if course.course_code else ''

    # 対応する入会時授業料商品を検索
    product_code_suffix = f'_5{tickets}'  # _51, _52, _53

    # まず完全一致で検索
    product = Product.objects.filter(
        tenant_id=course.tenant_id,
        product_code__endswith=product_code_suffix,
        product_code__startswith=course_code[:course_code.rfind('_')] if '_' in course_code else course_code,
        is_enrollment_tuition=True,
        deleted_at__isnull=True,
        is_active=True,
    ).first()

    if product:
        return product

    # ブランドで検索（同じブランドの入会時授業料商品）
    if course.brand:
        product = Product.objects.filter(
            tenant_id=course.tenant_id,
            brand=course.brand,
            is_enrollment_tuition=True,
            product_name__contains=f'{tickets}回分',
            deleted_at__isnull=True,
            is_active=True,
        ).first()

        if product:
            return product

    return None


class PricingPreviewView(APIView):
    """料金プレビュー"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        料金のプレビューを返す
        """
        # djangorestframework-camel-case がリクエストのcamelCaseをsnake_caseに変換する
        student_id = request.data.get('student_id')
        product_ids = request.data.get('product_ids', [])
        course_id = request.data.get('course_id')
        start_date_str = request.data.get('start_date')  # 開始日（入会時授業料計算用）

        print(f"[PricingPreview] student_id={student_id}, course_id={course_id}, product_ids={product_ids}, start_date={start_date_str}", file=sys.stderr)

        items = []
        subtotal = Decimal('0')
        enrollment_tuition_item = None  # 入会時授業料

        # 開始日をパース
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # コースIDから料金を取得
        course = None
        if course_id:
            try:
                course = Course.objects.get(id=course_id)
                price = course.get_price()
                print(f"[PricingPreview] Found course: {course.course_name}, price={price}", file=sys.stderr)
                item = {
                    'productId': str(course.id),
                    'productName': course.course_name,
                    'productType': 'tuition',
                    'unitPrice': int(price),
                    'quantity': 1,
                    'subtotal': int(price),
                    'taxRate': 0.1,
                    'taxAmount': int(price * Decimal('0.1')),
                    'discountAmount': 0,
                    'total': int(price * Decimal('1.1')),
                }
                items.append(item)
                subtotal += price

                # 入会時授業料（追加チケット）を計算
                if start_date and start_date.day > 1:
                    tickets = calculate_enrollment_tuition_tickets(start_date)
                    enrollment_product = get_enrollment_tuition_product(course, tickets)

                    if enrollment_product:
                        enrollment_price = enrollment_product.base_price
                        enrollment_tuition_item = {
                            'productId': str(enrollment_product.id),
                            'productName': enrollment_product.product_name,
                            'productType': 'enrollment_tuition',
                            'unitPrice': int(enrollment_price),
                            'quantity': 1,
                            'subtotal': int(enrollment_price),
                            'taxRate': 0.1,
                            'taxAmount': int(enrollment_price * Decimal('0.1')),
                            'discountAmount': 0,
                            'total': int(enrollment_price * Decimal('1.1')),
                            'tickets': tickets,  # チケット枚数
                            'isEnrollmentTuition': True,
                        }
                        items.append(enrollment_tuition_item)
                        subtotal += enrollment_price
                        print(f"[PricingPreview] Added enrollment tuition: {enrollment_product.product_name}, tickets={tickets}, price={enrollment_price}", file=sys.stderr)
                    else:
                        print(f"[PricingPreview] No enrollment tuition product found for {tickets} tickets", file=sys.stderr)

            except Course.DoesNotExist:
                pass

        # 商品IDから料金を取得
        for product_id in product_ids:
            if product_id == course_id:
                continue  # コースと重複する場合はスキップ
            try:
                product = Product.objects.get(id=product_id)
                price = product.base_price
                item = {
                    'productId': str(product.id),
                    'productName': product.product_name,
                    'productType': product.item_type,
                    'unitPrice': int(price),
                    'quantity': 1,
                    'subtotal': int(price),
                    'taxRate': float(product.tax_rate),
                    'taxAmount': int(price * product.tax_rate),
                    'discountAmount': 0,
                    'total': int(price * (1 + product.tax_rate)),
                }
                items.append(item)
                subtotal += price
            except Product.DoesNotExist:
                pass

        tax_total = int(subtotal * Decimal('0.1'))
        grand_total = int(subtotal) + tax_total

        return Response({
            'items': items,
            'subtotal': int(subtotal),
            'taxTotal': tax_total,
            'discounts': [],
            'discountTotal': 0,
            'companyContribution': 0,
            'schoolContribution': 0,
            'grandTotal': grand_total,
            'enrollmentTuition': enrollment_tuition_item,  # 入会時授業料情報
        })


class PricingConfirmView(APIView):
    """購入確定"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        購入を確定する
        - StudentItemを作成
        - Taskを作成（作業一覧に追加）
        """
        # djangorestframework-camel-case がリクエストのcamelCaseをsnake_caseに変換する
        preview_id = request.data.get('preview_id')
        payment_method = request.data.get('payment_method')
        student_id = request.data.get('student_id')
        course_id = request.data.get('course_id')
        # 購入時に選択した情報
        brand_id = request.data.get('brand_id')
        school_id = request.data.get('school_id')
        start_date_str = request.data.get('start_date')

        print(f"[PricingConfirm] preview_id={preview_id}, student_id={student_id}, course_id={course_id}", file=sys.stderr)
        print(f"[PricingConfirm] brand_id={brand_id}, school_id={school_id}, start_date={start_date_str}", file=sys.stderr)

        # 注文IDを生成
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # 現在の請求月
        today = date.today()
        billing_month = today.strftime('%Y-%m')

        student = None
        course = None
        brand = None
        school = None
        start_date = None

        # 生徒を取得
        if student_id:
            try:
                student = Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                pass

        # コースを取得
        if course_id:
            try:
                course = Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                pass

        # preview_idがコースIDの場合
        if not course and preview_id:
            try:
                course = Course.objects.get(id=preview_id)
            except Course.DoesNotExist:
                pass

        # ブランドを取得
        if brand_id:
            try:
                brand = Brand.objects.get(id=brand_id)
            except Brand.DoesNotExist:
                pass

        # 校舎を取得
        if school_id:
            try:
                school = School.objects.get(id=school_id)
            except School.DoesNotExist:
                pass

        # 開始日をパース
        if start_date_str:
            try:
                from datetime import datetime
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # StudentItemを作成（コースの商品構成から）
        print(f"[PricingConfirm] student={student}, course={course}, brand={brand}, school={school}, start_date={start_date}", file=sys.stderr)
        enrollment_tuition_info = None  # 入会時授業料情報（タスク表示用）

        if student and course:
            # コースに紐づく商品を取得して StudentItem を作成
            course_items = course.course_items.filter(is_active=True)
            print(f"[PricingConfirm] Found {course_items.count()} course_items", file=sys.stderr)

            for course_item in course_items:
                product = course_item.product
                unit_price = course_item.get_price()

                StudentItem.objects.create(
                    tenant_id=student.tenant_id,
                    student=student,
                    product=product,
                    billing_month=billing_month,
                    quantity=course_item.quantity,
                    unit_price=unit_price,
                    discount_amount=0,
                    final_price=unit_price * course_item.quantity,
                    notes=f'注文番号: {order_id} / コース: {course.course_name}',
                    # 購入時に選択した情報を保存
                    brand=brand,
                    school=school,
                    course=course,
                    start_date=start_date,
                )

            # 入会時授業料（追加チケット）を計算してStudentItemに追加
            if start_date and start_date.day > 1:
                tickets = calculate_enrollment_tuition_tickets(start_date)
                enrollment_product = get_enrollment_tuition_product(course, tickets)

                if enrollment_product:
                    enrollment_price = enrollment_product.base_price
                    StudentItem.objects.create(
                        tenant_id=student.tenant_id,
                        student=student,
                        product=enrollment_product,
                        billing_month=billing_month,
                        quantity=1,
                        unit_price=enrollment_price,
                        discount_amount=0,
                        final_price=enrollment_price,
                        notes=f'注文番号: {order_id} / 入会時授業料（{tickets}回分）',
                        brand=brand,
                        school=school,
                        course=course,
                        start_date=start_date,
                    )
                    enrollment_tuition_info = f'{enrollment_product.product_name} ¥{int(enrollment_price):,}'
                    print(f"[PricingConfirm] Created enrollment tuition StudentItem: {enrollment_product.product_name}, price={enrollment_price}", file=sys.stderr)

            # Taskを作成（作業一覧に追加）
            student_name = f'{student.last_name}{student.first_name}'
            task_description = f'保護者からの購入申請です。\n\n' \
                              f'生徒: {student_name}\n' \
                              f'コース: {course.course_name}\n' \
                              f'注文番号: {order_id}\n' \
                              f'支払方法: {payment_method or "未指定"}\n' \
                              f'請求月: {billing_month}'

            # 入会時授業料がある場合は追加
            if enrollment_tuition_info:
                task_description += f'\n入会時授業料: {enrollment_tuition_info}'

            Task.objects.create(
                tenant_id=student.tenant_id,
                task_type='request',
                title=f'【購入申請】{student_name} - {course.course_name}',
                description=task_description,
                status='new',
                priority='normal',
                student=student,
                guardian=student.guardian if hasattr(student, 'guardian') else None,
                school=course.school if hasattr(course, 'school') else None,
                brand=course.brand if hasattr(course, 'brand') else None,
                source_type='purchase',
                source_id=uuid.UUID(order_id.replace('ORD-', '').ljust(32, '0')[:32]) if len(order_id) > 4 else None,
                metadata={
                    'order_id': order_id,
                    'course_id': str(course.id),
                    'student_id': str(student.id),
                    'payment_method': payment_method,
                    'billing_month': billing_month,
                    'enrollment_tuition': enrollment_tuition_info,
                },
            )

        return Response({
            'orderId': order_id,
            'status': 'completed',
            'message': '購入申請が完了しました。確認後、ご連絡いたします。',
        })

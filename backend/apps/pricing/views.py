"""
Pricing views - 料金計算・購入確認API
"""
import sys
import uuid
from datetime import date
from decimal import Decimal
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.contracts.models import Course, StudentItem, Product
from apps.students.models import Student
from apps.tasks.models import Task
from apps.schools.models import Brand, School


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

        print(f"[PricingPreview] student_id={student_id}, course_id={course_id}, product_ids={product_ids}", file=sys.stderr)

        items = []
        subtotal = Decimal('0')

        # コースIDから料金を取得
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

            # Taskを作成（作業一覧に追加）
            student_name = f'{student.last_name}{student.first_name}'
            Task.objects.create(
                tenant_id=student.tenant_id,
                task_type='request',
                title=f'【購入申請】{student_name} - {course.course_name}',
                description=f'保護者からの購入申請です。\n\n'
                           f'生徒: {student_name}\n'
                           f'コース: {course.course_name}\n'
                           f'注文番号: {order_id}\n'
                           f'支払方法: {payment_method or "未指定"}\n'
                           f'請求月: {billing_month}',
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
                },
            )

        return Response({
            'orderId': order_id,
            'status': 'completed',
            'message': '購入申請が完了しました。確認後、ご連絡いたします。',
        })

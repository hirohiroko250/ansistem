"""
Student Info Mixin - 生徒・保護者情報取得
"""
import sys
from datetime import datetime
from decimal import Decimal

from apps.students.models import Student
from apps.billing.models import MileTransaction


class StudentInfoMixin:
    """生徒・保護者情報取得のMixin"""

    def _parse_request_data(self, request):
        """リクエストデータを解析"""
        return {
            'student_id': request.data.get('student_id'),
            'product_ids': request.data.get('product_ids', []),
            'course_id': request.data.get('course_id'),
            'start_date_str': request.data.get('start_date'),
            'day_of_week': request.data.get('day_of_week'),
        }

    def _get_student_info(self, student_id):
        """生徒・保護者・マイル情報を取得"""
        student = None
        guardian = None
        mile_info = None

        if student_id:
            try:
                student = Student.objects.select_related('guardian').get(id=student_id)
                guardian = student.guardian
                if guardian:
                    mile_balance = MileTransaction.get_balance(guardian)
                    can_use = MileTransaction.can_use_miles(guardian)
                    max_discount = MileTransaction.calculate_discount(mile_balance) if can_use and mile_balance >= 4 else Decimal('0')
                    mile_info = {
                        'balance': mile_balance,
                        'canUse': can_use,
                        'maxDiscount': int(max_discount),
                        'reason': None if can_use else 'コース契約が2つ以上必要です',
                    }
                    print(f"[PricingPreview] Mile info: balance={mile_balance}, canUse={can_use}, maxDiscount={max_discount}", file=sys.stderr)
            except Student.DoesNotExist:
                pass

        return student, guardian, mile_info

    def _parse_start_date(self, start_date_str):
        """開始日をパース"""
        if start_date_str:
            try:
                return datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        return None

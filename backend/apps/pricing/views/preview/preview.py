"""
Pricing Preview View - 料金プレビューAPI
"""
import sys
from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .helpers import process_product_ids, process_course_items
from .mixins import StudentInfoMixin, EnrollmentFeesMixin, BillingCalculationMixin


class PricingPreviewView(StudentInfoMixin, EnrollmentFeesMixin, BillingCalculationMixin, APIView):
    """料金プレビュー"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """料金のプレビューを返す"""
        import logging
        logger = logging.getLogger(__name__)

        # リクエストデータを解析
        data = self._parse_request_data(request)
        logger.warning(f"[PricingPreview] POST received - student_id={data['student_id']}, course_id={data['course_id']}")
        print(f"[PricingPreview] student_id={data['student_id']}, course_id={data['course_id']}, product_ids={data['product_ids']}, start_date={data['start_date_str']}, day_of_week={data['day_of_week']}", file=sys.stderr, flush=True)

        # 初期化
        items = []
        subtotal = Decimal('0')
        enrollment_tuition_item = None

        # 生徒・保護者・マイル情報を取得
        student, guardian, mile_info = self._get_student_info(data['student_id'])

        # 開始日をパース
        start_date = self._parse_start_date(data['start_date_str'])

        # コース/パック処理
        course, pack, items, subtotal, enrollment_tuition_item = self._process_course_or_pack(
            data['course_id'], start_date, items, subtotal
        )

        # 商品ID処理
        items, subtotal = process_product_ids(data['product_ids'], data['course_id'], items, subtotal)

        # 月別料金グループ初期化
        billing_by_month = self._init_billing_by_month()
        textbook_options = []
        course_items_list = []
        additional_fees = {}

        # コースアイテム処理
        if course:
            billing_by_month, textbook_options, additional_fees, subtotal, course_items_list = process_course_items(
                course, start_date, billing_by_month, textbook_options, additional_fees, subtotal, course_items_list
            )

        # 入会時費用計算
        enrollment_fees_calculated = []
        if course and start_date and data['day_of_week']:
            enrollment_fees_calculated, billing_by_month, additional_fees = self._calculate_enrollment_fees(
                course, start_date, data['day_of_week'], student, guardian,
                billing_by_month, additional_fees
            )

        # マイル割引計算
        discounts, discount_total = self._calculate_discounts(guardian, course, pack)

        # 月別授業料を取得
        monthly_tuition = self._get_monthly_tuition(course, start_date)

        # 月別ラベルを設定
        billing_by_month = self._setup_billing_labels(billing_by_month, start_date, monthly_tuition)

        # 当月分回数割料金を計算
        current_month_prorated = self._calculate_current_month_prorated(
            course, start_date, data['day_of_week']
        )

        # 合計金額を計算
        grand_total = self._calculate_grand_total(
            enrollment_tuition_item, additional_fees, monthly_tuition, discount_total
        )

        # 回数割料金をbilling_by_monthに反映
        billing_by_month = self._apply_prorated_fees(
            billing_by_month, current_month_prorated, enrollment_tuition_item
        )

        # 入会時費用の項目を0円で追加（項目がない場合）
        billing_by_month = self._ensure_enrollment_items(billing_by_month)

        # ログ出力
        self._log_results(
            enrollment_tuition_item, additional_fees, monthly_tuition,
            discount_total, grand_total, billing_by_month, textbook_options
        )

        return Response({
            'items': items,
            'subtotal': int(subtotal),
            'taxTotal': 0,
            'discounts': discounts,
            'discountTotal': int(discount_total),
            'companyContribution': 0,
            'schoolContribution': 0,
            'grandTotal': grand_total,
            'enrollmentTuition': enrollment_tuition_item,
            'additionalFees': additional_fees,
            'monthlyTuition': monthly_tuition,
            'currentMonthProrated': current_month_prorated,
            'courseItems': course_items_list,
            'billingByMonth': billing_by_month,
            'mileInfo': mile_info,
            'enrollmentFeesCalculated': enrollment_fees_calculated,
            'textbookOptions': textbook_options,
        })

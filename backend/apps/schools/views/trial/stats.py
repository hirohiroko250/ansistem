"""
Trial Stats Views - 体験予約統計Views
PublicTrialStatsView
"""
from datetime import date
import calendar as cal
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.db.models import Q

from ...models import Brand, BrandCategory, School, Grade


class PublicTrialStatsView(APIView):
    """体験予約統計API（認証不要）

    学年・ブランドカテゴリ・校舎ごとの体験予約人数を集計して返す
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        体験予約の統計情報を返す
        ?group_by=grade|brand_category|school (デフォルト: grade)
        ?year=2025&month=12 (オプション：期間指定)
        """
        from apps.students.models import TrialBooking

        group_by = request.query_params.get('group_by', 'grade')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        # 基本クエリ：キャンセル以外の体験予約
        queryset = TrialBooking.objects.exclude(
            status=TrialBooking.Status.CANCELLED
        ).select_related('student', 'school', 'brand')

        # 期間フィルタ
        if year and month:
            try:
                year = int(year)
                month = int(month)
                first_day = date(year, month, 1)
                last_day = date(year, month, cal.monthrange(year, month)[1])
                queryset = queryset.filter(trial_date__gte=first_day, trial_date__lte=last_day)
            except (ValueError, TypeError):
                pass

        result = []

        if group_by == 'grade':
            # 学年ごとに集計
            grades = Grade.objects.filter(is_active=True).order_by('sort_order')

            for grade in grades:
                count = queryset.filter(student__grade=grade).count()
                result.append({
                    'id': str(grade.id),
                    'code': grade.grade_code,
                    'name': grade.grade_name,
                    'shortName': grade.grade_name_short,
                    'category': grade.category,
                    'trialCount': count,
                })

            # 学年未設定の体験予約
            no_grade_count = queryset.filter(
                Q(student__grade__isnull=True) | Q(student__isnull=True)
            ).count()
            if no_grade_count > 0:
                result.append({
                    'id': None,
                    'code': 'none',
                    'name': '未設定',
                    'shortName': '未設定',
                    'category': None,
                    'trialCount': no_grade_count,
                })

        elif group_by == 'brand_category':
            # ブランドカテゴリごとに集計
            categories = BrandCategory.objects.filter(is_active=True).order_by('sort_order')

            for category in categories:
                brand_ids = Brand.objects.filter(category=category).values_list('id', flat=True)
                count = queryset.filter(brand_id__in=brand_ids).count()
                result.append({
                    'id': str(category.id),
                    'code': category.category_code,
                    'name': category.category_name,
                    'trialCount': count,
                })

            # カテゴリなしブランドの体験予約
            no_category_brands = Brand.objects.filter(category__isnull=True).values_list('id', flat=True)
            no_category_count = queryset.filter(brand_id__in=no_category_brands).count()
            if no_category_count > 0:
                result.append({
                    'id': None,
                    'code': 'none',
                    'name': '未分類',
                    'trialCount': no_category_count,
                })

        elif group_by == 'school':
            # 校舎ごとに集計
            schools = School.objects.filter(is_active=True, deleted_at__isnull=True).order_by('school_name')

            for school in schools:
                count = queryset.filter(school=school).count()
                result.append({
                    'id': str(school.id),
                    'code': school.school_code,
                    'name': school.school_name,
                    'prefecture': school.prefecture,
                    'city': school.city,
                    'trialCount': count,
                })

        # 合計
        total_count = queryset.count()

        return Response({
            'groupBy': group_by,
            'year': year,
            'month': month,
            'totalCount': total_count,
            'stats': result
        })

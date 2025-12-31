"""
Trial Lookup Views - 校舎・チケット検索Views
PublicSchoolsByTicketView, PublicTicketsBySchoolView
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from ...models import School, ClassSchedule


class PublicSchoolsByTicketView(APIView):
    """チケットが開講している校舎一覧API（認証不要）

    特定のチケットIDに対して、開講時間割が存在する校舎の一覧を返す
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        ?ticket_id=Ti10000063 でチケットIDを指定
        ?brand_id=xxx でブランドフィルタリング（オプション）
        """
        ticket_id = request.query_params.get('ticket_id')
        brand_id = request.query_params.get('brand_id')

        if not ticket_id:
            return Response(
                {'error': 'ticket_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ClassScheduleから該当チケットが開講している校舎を取得
        queryset = ClassSchedule.objects.filter(
            ticket_id=ticket_id,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('school')

        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        # 校舎のユニーク取得
        school_ids = queryset.values_list('school_id', flat=True).distinct()
        schools = School.objects.filter(id__in=school_ids, deleted_at__isnull=True).order_by('school_name')

        result = []
        for school in schools:
            # 住所を結合
            address_parts = [
                school.prefecture or '',
                school.city or '',
                school.address1 or '',
                school.address2 or '',
                school.address3 or ''
            ]
            full_address = ''.join(part for part in address_parts if part)

            result.append({
                'id': str(school.id),
                'name': school.school_name,
                'code': school.school_code,
                'address': full_address,
                'phone': school.phone or '',
                'latitude': float(school.latitude) if school.latitude else None,
                'longitude': float(school.longitude) if school.longitude else None,
            })

        return Response(result)


class PublicTicketsBySchoolView(APIView):
    """校舎で開講しているチケット一覧API（認証不要）

    特定の校舎IDに対して、開講時間割が存在するチケットIDの一覧を返す
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        ?school_id=xxx で校舎IDを指定
        """
        school_id = request.query_params.get('school_id')

        if not school_id:
            return Response(
                {'error': 'school_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ClassScheduleから該当校舎で開講しているチケットを取得
        ticket_ids = ClassSchedule.objects.filter(
            school_id=school_id,
            is_active=True,
            deleted_at__isnull=True
        ).values_list('ticket_id', flat=True).distinct()

        result = list(set(ticket_ids))

        return Response({
            'schoolId': school_id,
            'ticketIds': result
        })

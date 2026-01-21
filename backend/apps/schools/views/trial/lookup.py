"""
Trial Lookup Views - 校舎・チケット検索Views
PublicSchoolsByTicketView, PublicTicketsBySchoolView
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from ...models import School, ClassSchedule
from apps.contracts.models import Ticket


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
    フロントエンドと一致させるため、ticket_idを「T」プレフィックス形式に正規化して返す
    """
    permission_classes = [AllowAny]

    @staticmethod
    def normalize_ticket_id(ticket_id: str) -> str:
        """チケットIDを正規化（T形式に統一）

        ClassSchedule.ticket_idは「Ti」または「Ch」プレフィックスを持つ場合がある
        Ticket.ticket_codeは「T」プレフィックス形式
        これらを統一して比較できるようにする

        例:
        - Ti10000063 → T10000063
        - Ch10000063 → T10000063
        - T10000063 → T10000063
        """
        if not ticket_id:
            return ticket_id
        if ticket_id.startswith('Ti'):
            return f'T{ticket_id[2:]}'
        if ticket_id.startswith('Ch'):
            return f'T{ticket_id[2:]}'
        return ticket_id

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
        # ticket_idはUUIDまたはTi/Ch形式のコードが入っている可能性がある
        ticket_ids = ClassSchedule.objects.filter(
            school_id=school_id,
            is_active=True,
            deleted_at__isnull=True
        ).values_list('ticket_id', flat=True).distinct()

        # ユニークなticket_idsを収集
        unique_ticket_ids = set(tid for tid in ticket_ids if tid)

        # ticket_codeのリストを作成
        ticket_codes = []

        for tid in unique_ticket_ids:
            # UUIDかどうかを判定（ハイフンを含むか、または36文字）
            is_uuid = '-' in tid or len(tid) == 36

            if is_uuid:
                # UUIDの場合、Ticketテーブルからticket_codeを取得
                try:
                    ticket = Ticket.objects.get(id=tid)
                    if ticket.ticket_code:
                        ticket_codes.append(self.normalize_ticket_id(ticket.ticket_code))
                except Ticket.DoesNotExist:
                    # チケットが見つからない場合はスキップ
                    pass
            else:
                # Ti/Ch/T形式のコードの場合は正規化して追加
                ticket_codes.append(self.normalize_ticket_id(tid))

        # 重複を除去
        normalized_ids = list(set(ticket_codes))

        return Response({
            'schoolId': school_id,
            'ticketIds': normalized_ids
        })

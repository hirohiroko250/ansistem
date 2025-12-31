"""
ChatLog Views - チャットログ管理Views
ChatLogViewSet
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count

from apps.core.permissions import IsTenantUser
from ..models import ChatLog
from ..serializers import ChatLogSerializer, ChatLogListSerializer


class ChatLogViewSet(viewsets.ReadOnlyModelViewSet):
    """チャットログビューセット（管理者向け）"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        from apps.core.permissions import is_admin_user
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = ChatLog.objects.select_related('school', 'guardian', 'brand', 'message')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        # フィルタリング
        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)

        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(guardian_id=guardian_id)

        sender_type = self.request.query_params.get('sender_type')
        if sender_type:
            queryset = queryset.filter(sender_type=sender_type)

        # 日付範囲フィルタ
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)

        # 検索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(content__icontains=search) |
                Q(guardian_name__icontains=search) |
                Q(school_name__icontains=search) |
                Q(brand_name__icontains=search)
            )

        return queryset.order_by('-timestamp')

    def get_serializer_class(self):
        if self.action == 'list':
            return ChatLogListSerializer
        return ChatLogSerializer

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """チャットログの統計情報"""
        queryset = self.get_queryset()

        stats = {
            'total_messages': queryset.count(),
            'by_sender_type': {},
            'by_brand': {},
            'by_school': {},
        }

        # 送信者タイプ別
        for sender_type in ['GUARDIAN', 'STAFF', 'BOT']:
            stats['by_sender_type'][sender_type] = queryset.filter(
                sender_type=sender_type
            ).count()

        # ブランド別
        brand_stats = queryset.values('brand_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        stats['by_brand'] = {item['brand_name']: item['count'] for item in brand_stats}

        # 校舎別
        school_stats = queryset.values('school_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        stats['by_school'] = {
            item['school_name'] or 'その他': item['count']
            for item in school_stats
        }

        return Response(stats)

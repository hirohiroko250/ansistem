"""
Notification Views - 通知管理Views
NotificationViewSet
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.core.permissions import IsTenantUser
from ..models import Notification
from ..serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """通知ビューセット"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return Notification.objects.filter(
            tenant_id=tenant_id,
            user=self.request.user
        )

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """既読にする"""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """全て既読にする"""
        self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """未読数"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})

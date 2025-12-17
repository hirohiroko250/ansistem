"""
Tenants Views
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Tenant
from .serializers import TenantSerializer, TenantDetailSerializer


class TenantViewSet(viewsets.ReadOnlyModelViewSet):
    """テナント一覧・詳細API（読み取り専用）"""
    queryset = Tenant.objects.filter(is_active=True).order_by('tenant_code')
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TenantDetailSerializer
        return TenantSerializer

    @action(detail=False, methods=['get'])
    def all(self, request):
        """全テナント一覧（active含む）"""
        queryset = Tenant.objects.all().order_by('tenant_code')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

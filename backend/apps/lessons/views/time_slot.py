"""
TimeSlot Views - 時間割Views
TimeSlotViewSet
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models import TimeSlot
from ..serializers import TimeSlotSerializer


class TimeSlotViewSet(viewsets.ModelViewSet):
    """時間割 ViewSet"""
    queryset = TimeSlot.objects.all()
    serializer_class = TimeSlotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = TimeSlot.objects.filter(is_active=True)
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        school_id = self.request.query_params.get('school')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        return queryset

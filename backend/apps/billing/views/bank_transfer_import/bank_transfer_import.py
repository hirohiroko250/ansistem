"""
BankTransferImport ViewSet - 振込インポート管理API
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.billing.models import BankTransferImport
from apps.billing.serializers import BankTransferImportSerializer
from .mixins import (
    BankTransferImportUploadMixin,
    BankTransferImportConfirmMixin,
    BankTransferImportSearchMixin,
)


@extend_schema_view(
    list=extend_schema(summary='振込インポートバッチ一覧'),
    retrieve=extend_schema(summary='振込インポートバッチ詳細'),
)
class BankTransferImportViewSet(
    BankTransferImportUploadMixin,
    BankTransferImportConfirmMixin,
    BankTransferImportSearchMixin,
    viewsets.ModelViewSet
):
    """振込インポート管理API"""
    serializer_class = BankTransferImportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.core.permissions import is_admin_user

        queryset = BankTransferImport.objects.select_related('imported_by', 'confirmed_by')

        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=self.request.user.tenant_id)

        return queryset.order_by('-imported_at')

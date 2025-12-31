"""
Contract Views - 契約管理
ContractViewSet
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.core.permissions import IsTenantUser
from .mixins import (
    ContractCSVMixin,
    DiscountActionsMixin,
    CustomerActionsMixin,
    ChangeActionsMixin,
)


class ContractViewSet(
    ContractCSVMixin,
    DiscountActionsMixin,
    CustomerActionsMixin,
    ChangeActionsMixin,
    viewsets.ModelViewSet
):
    """契約ビューセット

    Mixins:
    - ContractCSVMixin: CSV設定・コアメソッド
    - DiscountActionsMixin: 割引管理アクション
    - CustomerActionsMixin: 顧客向けアクション
    - ChangeActionsMixin: 変更申請アクション
    """
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

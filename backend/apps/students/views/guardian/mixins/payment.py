"""
Payment Actions Mixin - 支払い情報関連アクション
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.students.serializers import (
    GuardianPaymentSerializer, GuardianPaymentUpdateSerializer,
)


class PaymentActionsMixin:
    """支払い情報関連アクション"""

    @action(detail=True, methods=['get'])
    def payment(self, request, pk=None):
        """保護者の支払い情報取得"""
        guardian = self.get_object()
        serializer = GuardianPaymentSerializer(guardian)
        return Response(serializer.data)

    @action(detail=True, methods=['put', 'patch'])
    def payment_update(self, request, pk=None):
        """保護者の支払い情報更新"""
        guardian = self.get_object()
        serializer = GuardianPaymentUpdateSerializer(guardian, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # 更新後のデータを返す
        return Response(GuardianPaymentSerializer(guardian).data)

    @action(detail=False, methods=['get'])
    def my_payment(self, request):
        """ログイン中の保護者の支払い情報取得"""
        if not hasattr(request.user, 'guardian_profile') or not request.user.guardian_profile:
            return Response(
                {'error': '保護者プロファイルが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        guardian = request.user.guardian_profile
        serializer = GuardianPaymentSerializer(guardian)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def my_payment_update(self, request):
        """ログイン中の保護者の支払い情報更新"""
        if not hasattr(request.user, 'guardian_profile') or not request.user.guardian_profile:
            return Response(
                {'error': '保護者プロファイルが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        guardian = request.user.guardian_profile
        serializer = GuardianPaymentUpdateSerializer(guardian, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(GuardianPaymentSerializer(guardian).data)

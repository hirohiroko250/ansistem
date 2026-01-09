"""
Friendship Views - 友達紹介API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django.utils import timezone

from ..models import Guardian, FriendshipRegistration, FSDiscount


class FriendshipViewSet(viewsets.GenericViewSet):
    """友達紹介API"""
    permission_classes = [IsAuthenticated]

    def get_guardian(self):
        """現在のユーザーの保護者を取得"""
        user = self.request.user
        if hasattr(user, 'guardian_profile') and user.guardian_profile:
            return user.guardian_profile
        return None

    @action(detail=False, methods=['get'])
    def my_code(self, request):
        """自分の紹介コードを取得

        GET /api/v1/students/friendship/my_code/
        """
        guardian = self.get_guardian()
        if not guardian:
            return Response(
                {'success': False, 'error': {'message': '保護者情報が見つかりません'}},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'success': True,
            'data': {
                'referral_code': guardian.guardian_no,
                'name': guardian.full_name,
            }
        })

    @action(detail=False, methods=['post'])
    def register(self, request):
        """友達コードで紹介登録

        POST /api/v1/students/friendship/register/
        {
            "referral_code": "80000001"
        }
        """
        guardian = self.get_guardian()
        if not guardian:
            return Response(
                {'success': False, 'error': {'message': '保護者情報が見つかりません'}},
                status=status.HTTP_404_NOT_FOUND
            )

        referral_code = request.data.get('referral_code', '').strip()
        if not referral_code:
            return Response(
                {'success': False, 'error': {'message': '紹介コードを入力してください'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 自分のコードは登録不可
        if referral_code == guardian.guardian_no:
            return Response(
                {'success': False, 'error': {'message': '自分のコードは登録できません'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 紹介者を検索
        try:
            referrer = Guardian.objects.get(
                guardian_no=referral_code,
                tenant_id=guardian.tenant_id
            )
        except Guardian.DoesNotExist:
            return Response(
                {'success': False, 'error': {'message': '紹介コードが見つかりません'}},
                status=status.HTTP_404_NOT_FOUND
            )

        # 既に友達関係がある場合
        if FriendshipRegistration.are_friends(guardian, referrer):
            return Response(
                {'success': False, 'error': {'message': '既に友達登録済みです'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 既存の申請があるか確認
        existing = FriendshipRegistration.objects.filter(
            models.Q(requester=guardian, target=referrer) |
            models.Q(requester=referrer, target=guardian)
        ).first()

        if existing:
            if existing.status == FriendshipRegistration.Status.PENDING:
                # 相手からの申請がある場合は自動承認
                if existing.requester == referrer:
                    existing.accept()
                    return Response({
                        'success': True,
                        'data': {
                            'message': '友達登録が完了しました！相互に500円割引が適用されます。',
                            'status': 'accepted',
                            'friend_name': referrer.full_name,
                        }
                    })
                else:
                    return Response(
                        {'success': False, 'error': {'message': '既に申請済みです'}},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif existing.status == FriendshipRegistration.Status.REJECTED:
                return Response(
                    {'success': False, 'error': {'message': 'この友達申請は拒否されています'}},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif existing.status == FriendshipRegistration.Status.CANCELLED:
                # 取消済みの場合は新規作成可能
                pass
            else:
                return Response(
                    {'success': False, 'error': {'message': '既に友達登録済みです'}},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 新規友達登録を作成
        friendship = FriendshipRegistration.objects.create(
            tenant_id=guardian.tenant_id,
            requester=guardian,
            target=referrer,
            friend_code=referral_code,
            status=FriendshipRegistration.Status.PENDING,
        )

        return Response({
            'success': True,
            'data': {
                'message': f'{referrer.full_name}さんに友達申請を送信しました。相手が承認すると相互に500円割引が適用されます。',
                'status': 'pending',
                'friend_name': referrer.full_name,
                'friendship_id': str(friendship.id),
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def list_friends(self, request):
        """友達一覧を取得

        GET /api/v1/students/friendship/list_friends/
        """
        guardian = self.get_guardian()
        if not guardian:
            return Response(
                {'success': False, 'error': {'message': '保護者情報が見つかりません'}},
                status=status.HTTP_404_NOT_FOUND
            )

        # 承認済みの友達
        friends = FriendshipRegistration.get_friends(guardian)

        # 保留中の申請（自分が送った）
        pending_sent = FriendshipRegistration.objects.filter(
            requester=guardian,
            status=FriendshipRegistration.Status.PENDING
        ).select_related('target')

        # 保留中の申請（自分が受けた）
        pending_received = FriendshipRegistration.objects.filter(
            target=guardian,
            status=FriendshipRegistration.Status.PENDING
        ).select_related('requester')

        return Response({
            'success': True,
            'data': {
                'friends': [
                    {
                        'id': str(f.id),
                        'name': f.full_name,
                        'guardian_no': f.guardian_no,
                    }
                    for f in friends
                ],
                'pending_sent': [
                    {
                        'id': str(p.id),
                        'name': p.target.full_name,
                        'requested_at': p.requested_at.isoformat(),
                    }
                    for p in pending_sent
                ],
                'pending_received': [
                    {
                        'id': str(p.id),
                        'name': p.requester.full_name,
                        'requested_at': p.requested_at.isoformat(),
                    }
                    for p in pending_received
                ],
            }
        })

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """友達申請を承認

        POST /api/v1/students/friendship/{id}/accept/
        """
        guardian = self.get_guardian()
        if not guardian:
            return Response(
                {'success': False, 'error': {'message': '保護者情報が見つかりません'}},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            friendship = FriendshipRegistration.objects.get(
                id=pk,
                target=guardian,
                status=FriendshipRegistration.Status.PENDING
            )
        except FriendshipRegistration.DoesNotExist:
            return Response(
                {'success': False, 'error': {'message': '申請が見つかりません'}},
                status=status.HTTP_404_NOT_FOUND
            )

        friendship.accept()

        return Response({
            'success': True,
            'data': {
                'message': '友達登録を承認しました。相互に500円割引が適用されます。',
                'friend_name': friendship.requester.full_name,
            }
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """友達申請を拒否

        POST /api/v1/students/friendship/{id}/reject/
        """
        guardian = self.get_guardian()
        if not guardian:
            return Response(
                {'success': False, 'error': {'message': '保護者情報が見つかりません'}},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            friendship = FriendshipRegistration.objects.get(
                id=pk,
                target=guardian,
                status=FriendshipRegistration.Status.PENDING
            )
        except FriendshipRegistration.DoesNotExist:
            return Response(
                {'success': False, 'error': {'message': '申請が見つかりません'}},
                status=status.HTTP_404_NOT_FOUND
            )

        friendship.reject()

        return Response({
            'success': True,
            'data': {
                'message': '友達申請を拒否しました。',
            }
        })

    @action(detail=False, methods=['get'])
    def discounts(self, request):
        """自分のFS割引一覧を取得

        GET /api/v1/students/friendship/discounts/
        """
        guardian = self.get_guardian()
        if not guardian:
            return Response(
                {'success': False, 'error': {'message': '保護者情報が見つかりません'}},
                status=status.HTTP_404_NOT_FOUND
            )

        # 有効な割引
        active_discounts = FSDiscount.get_available_discounts(guardian)

        return Response({
            'success': True,
            'data': {
                'discounts': [
                    {
                        'id': str(d.id),
                        'discount_type': d.discount_type,
                        'discount_value': float(d.discount_value),
                        'status': d.status,
                        'valid_from': d.valid_from.isoformat() if d.valid_from else None,
                        'valid_until': d.valid_until.isoformat() if d.valid_until else None,
                        'friend_name': d.friendship.requester.full_name if d.friendship.target == guardian else d.friendship.target.full_name,
                    }
                    for d in active_discounts
                ],
                'total_discount': sum(float(d.discount_value) for d in active_discounts if d.discount_type == 'fixed'),
            }
        })

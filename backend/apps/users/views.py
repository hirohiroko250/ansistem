"""
Users Views
"""
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from .models import User
from .serializers import (
    UserSummarySerializer, UserDetailSerializer,
    UserCreateSerializer, UserUpdateSerializer,
    PasswordChangeSerializer, ProfileSerializer,
    ChildAccountSerializer, ChildAccountCreateSerializer,
    SwitchAccountSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """ユーザービューセット"""
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        queryset = User.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        user_type = self.request.query_params.get('user_type')
        if user_type:
            queryset = queryset.filter(user_type=user_type)

        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(last_name__icontains=search) |
                Q(first_name__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return UserSummarySerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserDetailSerializer

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.is_active = False
        instance.save()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """ユーザー有効化"""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response(UserDetailSerializer(user).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """ユーザー無効化"""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(UserDetailSerializer(user).data)

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """パスワードリセット（管理者用）"""
        user = self.get_object()
        new_password = request.data.get('new_password')

        if not new_password or len(new_password) < 8:
            return Response(
                {'error': 'パスワードは8文字以上で指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.save()
        return Response({'message': 'パスワードをリセットしました'})


class ProfileView(APIView):
    """自分のプロフィール"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProfileSerializer(request.user).data)

    def post(self, request):
        """パスワード変更"""
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data['current_password']):
            return Response(
                {'error': '現在のパスワードが正しくありません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.password_changed_at = timezone.now()
        request.user.save()
        return Response({'message': 'パスワードを変更しました'})


class ChildAccountViewSet(viewsets.ViewSet):
    """子アカウント管理（保護者が生徒アカウントを管理）"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """子アカウント一覧"""
        children = request.user.get_children()
        serializer = ChildAccountSerializer(children, many=True)
        return Response(serializer.data)

    def create(self, request):
        """子アカウント作成"""
        # 保護者のみ作成可能
        if request.user.user_type != User.UserType.GUARDIAN:
            return Response(
                {'error': '保護者アカウントのみ子アカウントを作成できます'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ChildAccountCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        child = serializer.save()

        return Response(
            ChildAccountSerializer(child).data,
            status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, pk=None):
        """子アカウント詳細"""
        try:
            child = request.user.child_accounts.get(
                id=pk,
                deleted_at__isnull=True
            )
            serializer = ChildAccountSerializer(child)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': '子アカウントが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

    def partial_update(self, request, pk=None):
        """子アカウント更新"""
        try:
            child = request.user.child_accounts.get(
                id=pk,
                deleted_at__isnull=True
            )
            serializer = ChildAccountCreateSerializer(
                child,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            # parent_userは更新しない
            serializer.save()
            return Response(ChildAccountSerializer(child).data)
        except User.DoesNotExist:
            return Response(
                {'error': '子アカウントが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, pk=None):
        """子アカウント削除（論理削除）"""
        try:
            child = request.user.child_accounts.get(
                id=pk,
                deleted_at__isnull=True
            )
            child.deleted_at = timezone.now()
            child.is_active = False
            child.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response(
                {'error': '子アカウントが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )


class SwitchAccountView(APIView):
    """アカウント切り替え"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        アカウント切り替え
        保護者 → 生徒への切り替え、または生徒 → 保護者への切り替え
        新しいトークンを発行して返す
        """
        serializer = SwitchAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user_id = serializer.validated_data['target_user_id']

        # 親アカウントに戻る場合
        if request.user.parent_user and str(request.user.parent_user.id) == str(target_user_id):
            target_user = request.user.parent_user
        # 子アカウントに切り替える場合
        else:
            target_user = request.user.switch_to_child(target_user_id)

        if not target_user:
            return Response(
                {'error': '切り替え先のアカウントが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 新しいJWTトークンを発行
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(target_user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': ChildAccountSerializer(target_user).data
        })

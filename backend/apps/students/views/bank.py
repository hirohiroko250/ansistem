"""
Bank Views - 銀行口座管理
BankAccountViewSet, BankAccountChangeRequestViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone

from apps.core.permissions import IsTenantUser
from ..models import BankAccount, BankAccountChangeRequest
from ..serializers import (
    BankAccountSerializer,
    BankAccountChangeRequestSerializer, BankAccountChangeRequestCreateSerializer,
)


class BankAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """銀行口座ビューセット（読み取り専用）"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = BankAccount.objects.filter(
            tenant_id=tenant_id,
            is_active=True
        ).select_related('guardian')

        # 保護者の場合は自分の口座のみ
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(guardian=guardian)

        return queryset.order_by('-is_primary', '-created_at')

    @action(detail=False, methods=['get'])
    def my_accounts(self, request):
        """ログイン中の保護者の銀行口座一覧"""
        if not hasattr(request.user, 'guardian_profile') or not request.user.guardian_profile:
            return Response(
                {'error': '保護者プロファイルが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        guardian = request.user.guardian_profile
        accounts = BankAccount.objects.filter(
            guardian=guardian,
            is_active=True
        ).order_by('-is_primary', '-created_at')
        serializer = BankAccountSerializer(accounts, many=True)
        return Response(serializer.data)


class BankAccountChangeRequestViewSet(viewsets.ModelViewSet):
    """銀行口座変更申請ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = BankAccountChangeRequest.objects.select_related(
            'guardian', 'existing_account', 'requested_by', 'processed_by'
        )

        # テナントフィルタ
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        # 保護者の場合は自分の申請のみ
        if hasattr(self.request, 'user') and hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(guardian=guardian)

        # フィルタリング
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 検索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(guardian__last_name__icontains=search) |
                Q(guardian__first_name__icontains=search) |
                Q(guardian__guardian_no__icontains=search) |
                Q(bank_name__icontains=search) |
                Q(account_holder__icontains=search)
            )

        # リクエストタイプフィルタ
        request_type = self.request.query_params.get('request_type')
        if request_type:
            queryset = queryset.filter(request_type=request_type)

        return queryset.order_by('-requested_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return BankAccountChangeRequestCreateSerializer
        return BankAccountChangeRequestSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        guardian = None

        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            if not tenant_id:
                tenant_id = guardian.tenant_id

        instance = serializer.save(
            tenant_id=tenant_id,
            guardian=guardian,
            requested_by=self.request.user,
            status='pending'
        )

        # 作業一覧にタスクを作成
        from apps.tasks.models import Task
        request_type_display = dict(BankAccountChangeRequest.RequestType.choices).get(
            instance.request_type, instance.request_type
        )
        Task.objects.create(
            tenant_id=tenant_id,
            task_type='bank_account_request',
            title=f'銀行口座{request_type_display}: {guardian.full_name if guardian else "不明"}',
            description=f'{guardian.full_name if guardian else "不明"}さんから銀行口座の{request_type_display}申請が提出されました。',
            status='new',
            priority='normal',
            guardian=guardian,
            source_type='bank_account_request',
            source_id=instance.id,
        )

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """ログイン中の保護者の申請一覧"""
        if not hasattr(request.user, 'guardian_profile') or not request.user.guardian_profile:
            return Response(
                {'error': '保護者プロファイルが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        guardian = request.user.guardian_profile
        requests = BankAccountChangeRequest.objects.filter(
            guardian=guardian
        ).order_by('-requested_at')
        serializer = BankAccountChangeRequestSerializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """申請キャンセル"""
        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみキャンセルできます'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.status = 'cancelled'
        instance.save()
        return Response(BankAccountChangeRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """申請承認 - 古い口座を履歴に保存し、新しい口座をGuardianに反映"""
        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみ承認できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        guardian = instance.guardian
        if not guardian:
            return Response(
                {'error': '保護者情報が見つかりません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 古い口座情報をBankAccountテーブルに保存（履歴として）
        if guardian.bank_name and guardian.account_number:
            BankAccount.objects.create(
                tenant_id=guardian.tenant_id,
                tenant_ref_id=guardian.tenant_ref_id,
                guardian=guardian,
                bank_name=guardian.bank_name,
                bank_code=guardian.bank_code or '',
                branch_name=guardian.branch_name or '',
                branch_code=guardian.branch_code or '',
                account_type=guardian.account_type or 'ordinary',
                account_number=guardian.account_number,
                account_holder=guardian.account_holder or '',
                account_holder_kana=guardian.account_holder_kana or '',
                is_primary=False,  # 履歴なのでプライマリではない
                is_active=False,   # 旧口座なので無効
                notes=f'口座変更申請承認により退避 ({timezone.now().strftime("%Y-%m-%d %H:%M")})'
            )

        # 新しい口座情報をGuardianに反映
        if instance.request_type in ('new', 'update'):
            guardian.bank_name = instance.bank_name
            guardian.bank_code = instance.bank_code or ''
            guardian.branch_name = instance.branch_name or ''
            guardian.branch_code = instance.branch_code or ''
            guardian.account_type = instance.account_type or 'ordinary'
            guardian.account_number = instance.account_number
            guardian.account_holder = instance.account_holder or f"{guardian.last_name} {guardian.first_name}"
            guardian.account_holder_kana = instance.account_holder_kana or ''
            guardian.save()
        elif instance.request_type == 'delete':
            # 削除の場合は口座情報をクリア
            guardian.bank_name = ''
            guardian.bank_code = ''
            guardian.branch_name = ''
            guardian.branch_code = ''
            guardian.account_type = ''
            guardian.account_number = ''
            guardian.account_holder = ''
            guardian.account_holder_kana = ''
            guardian.save()

        # 申請を承認済みに
        instance.status = 'approved'
        instance.processed_by = request.user
        instance.processed_at = timezone.now()
        instance.save()

        # 関連タスクを完了に
        from apps.tasks.models import Task
        Task.objects.filter(
            source_type='bank_account_request',
            source_id=instance.id
        ).update(status='completed', completed_at=timezone.now())

        return Response(BankAccountChangeRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """申請却下"""
        instance = self.get_object()
        if instance.status != 'pending':
            return Response(
                {'error': '申請中のもののみ却下できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.status = 'rejected'
        instance.processed_by = request.user
        instance.processed_at = timezone.now()
        instance.process_notes = request.data.get('reason', '')
        instance.save()

        # 関連タスクを完了に
        from apps.tasks.models import Task
        Task.objects.filter(
            source_type='bank_account_request',
            source_id=instance.id
        ).update(status='completed', completed_at=timezone.now())

        return Response(BankAccountChangeRequestSerializer(instance).data)

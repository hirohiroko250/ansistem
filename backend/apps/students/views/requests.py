"""
Request Views - 休会・退会申請管理
SuspensionRequestViewSet, WithdrawalRequestViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsTenantUser
from ..models import SuspensionRequest, WithdrawalRequest, StudentSchool, StudentEnrollment
from ..serializers import (
    SuspensionRequestSerializer, SuspensionRequestCreateSerializer,
    WithdrawalRequestSerializer, WithdrawalRequestCreateSerializer,
)
from ..services import SuspensionService, WithdrawalService


class SuspensionRequestViewSet(viewsets.ModelViewSet):
    """休会申請ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = SuspensionRequest.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'brand', 'school', 'requested_by', 'processed_by')

        # 保護者の場合は自分の子供の申請のみ
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(student__guardian=guardian)

        # フィルタリング
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-requested_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return SuspensionRequestCreateSerializer
        return SuspensionRequestSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            tenant_id = self.request.user.guardian_profile.tenant_id

        # 生徒情報から自動的にブランド・校舎を設定
        student = serializer.validated_data.get('student')
        brand = serializer.validated_data.get('brand') or student.primary_brand
        school = serializer.validated_data.get('school') or student.primary_school

        # primary_brand/schoolがない場合は契約から取得
        if not brand or not school:
            from apps.contracts.models import Contract
            active_contract = Contract.objects.filter(
                student=student,
                status='active',
                deleted_at__isnull=True
            ).select_related('brand', 'school').first()
            if active_contract:
                if not brand:
                    brand = active_contract.brand
                if not school:
                    school = active_contract.school

        instance = serializer.save(
            tenant_id=tenant_id,
            brand=brand,
            school=school,
            requested_by=self.request.user,
            status='pending'
        )

        # 作業一覧にタスクを作成
        from apps.tasks.models import Task
        Task.objects.create(
            tenant_id=tenant_id,
            task_type='suspension_request',
            title=f'休会申請: {instance.student.full_name}',
            description=f'{instance.student.full_name}さんの休会申請が提出されました。休会開始日: {instance.suspend_from}',
            status='new',
            priority='normal',
            student=instance.student,
            source_type='suspension_request',
            source_id=instance.id,
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """申請キャンセル"""
        instance = self.get_object()
        service = SuspensionService(instance)
        try:
            service.cancel()
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SuspensionRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """休会申請を承認"""
        instance = self.get_object()
        service = SuspensionService(instance)
        try:
            service.approve(processed_by=request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SuspensionRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """休会申請を却下"""
        instance = self.get_object()
        service = SuspensionService(instance)
        try:
            service.reject(
                processed_by=request.user,
                reason=request.data.get('reason', '')
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SuspensionRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """休会から復会"""
        instance = self.get_object()
        service = SuspensionService(instance)
        try:
            service.resume()
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SuspensionRequestSerializer(instance).data)


class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    """退会申請ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = WithdrawalRequest.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'brand', 'school', 'requested_by', 'processed_by')

        # 保護者の場合は自分の子供の申請のみ
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(student__guardian=guardian)

        # フィルタリング
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-requested_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return WithdrawalRequestCreateSerializer
        return WithdrawalRequestSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            tenant_id = self.request.user.guardian_profile.tenant_id

        # 生徒情報から自動的にブランド・校舎を設定
        student = serializer.validated_data.get('student')
        brand = serializer.validated_data.get('brand') or student.primary_brand
        school = serializer.validated_data.get('school') or student.primary_school

        # primary_brand/schoolがない場合は契約から取得
        if not brand or not school:
            from apps.contracts.models import Contract
            active_contract = Contract.objects.filter(
                student=student,
                status='active',
                deleted_at__isnull=True
            ).select_related('brand', 'school').first()
            if active_contract:
                if not brand:
                    brand = active_contract.brand
                if not school:
                    school = active_contract.school

        # 残チケット数を計算
        from apps.contracts.models import StudentItem
        remaining_tickets = StudentItem.objects.filter(
            student=student,
            deleted_at__isnull=True,
            product__item_type='ticket'
        ).aggregate(total=Count('id'))['total'] or 0

        instance = serializer.save(
            tenant_id=tenant_id,
            brand=brand,
            school=school,
            requested_by=self.request.user,
            status='pending',
            remaining_tickets=remaining_tickets
        )

        # 作業一覧にタスクを作成
        from apps.tasks.models import Task
        Task.objects.create(
            tenant_id=tenant_id,
            task_type='withdrawal_request',
            title=f'退会申請: {instance.student.full_name}',
            description=f'{instance.student.full_name}さんの退会申請が提出されました。退会希望日: {instance.withdrawal_date}',
            status='new',
            priority='high',
            student=instance.student,
            source_type='withdrawal_request',
            source_id=instance.id,
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """申請キャンセル"""
        instance = self.get_object()
        service = WithdrawalService(instance)
        try:
            service.cancel()
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(WithdrawalRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """退会申請を承認"""
        instance = self.get_object()
        service = WithdrawalService(instance)
        try:
            service.approve(processed_by=request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(WithdrawalRequestSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """退会申請を却下"""
        instance = self.get_object()
        service = WithdrawalService(instance)
        try:
            service.reject(
                processed_by=request.user,
                reason=request.data.get('reason', '')
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(WithdrawalRequestSerializer(instance).data)

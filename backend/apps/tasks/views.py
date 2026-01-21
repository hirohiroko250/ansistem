"""Task API views."""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from apps.core.permissions import IsTenantUser
from apps.core.exceptions import UnauthorizedError, ValidationException
from .models import Task, TaskCategory, TaskComment
from .serializers import (
    TaskSerializer, TaskCreateUpdateSerializer,
    TaskCategorySerializer, TaskCommentSerializer
)


class TaskCategoryViewSet(viewsets.ModelViewSet):
    """作業カテゴリ ViewSet"""
    queryset = TaskCategory.objects.filter(deleted_at__isnull=True, is_active=True)
    serializer_class = TaskCategorySerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['sort_order', 'category_code']
    ordering = ['sort_order']


class TaskViewSet(viewsets.ModelViewSet):
    """作業 ViewSet"""
    queryset = Task.objects.filter(deleted_at__isnull=True).select_related(
        'category', 'school', 'brand', 'student', 'guardian'
    ).order_by('-created_at')
    permission_classes = [IsAuthenticated, IsTenantUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'task_type', 'school', 'brand', 'student', 'assigned_to_id']
    search_fields = ['title', 'description', 'student__last_name', 'student__first_name']
    ordering_fields = ['created_at', 'due_date', 'priority', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TaskCreateUpdateSerializer
        return TaskSerializer

    def update(self, request, *args, **kwargs):
        """更新後にTaskSerializerで完全なデータを返す"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        # TaskSerializerで完全なデータを返す（assigned_to_name等を含む）
        response_serializer = TaskSerializer(instance)
        return Response(response_serializer.data)

    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """自分に割り当てられたタスク一覧"""
        user = request.user
        if not user.is_authenticated:
            raise UnauthorizedError()

        # ユーザーIDでフィルタリング
        tasks = self.queryset.filter(assigned_to_id=user.id).exclude(status__in=['completed', 'cancelled'])

        # ステータスフィルター
        status_filter = request.query_params.get('status')
        if status_filter:
            tasks = tasks.filter(status=status_filter)

        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = TaskSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_assignee(self, request):
        """担当者別タスク一覧"""
        assignee_id = request.query_params.get('assignee_id')
        if not assignee_id:
            raise ValidationException('assignee_id は必須です')

        tasks = self.queryset.filter(assigned_to_id=assignee_id)

        # ステータスフィルター
        status_filter = request.query_params.get('status')
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        else:
            # デフォルトで未完了のみ
            tasks = tasks.exclude(status__in=['completed', 'cancelled'])

        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = TaskSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """未完了タスク一覧"""
        tasks = self.queryset.exclude(status__in=['completed', 'cancelled'])
        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = TaskSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """今日の期限タスク"""
        today = timezone.now().date()
        tasks = self.queryset.filter(due_date=today).exclude(status__in=['completed', 'cancelled'])
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """期限切れタスク"""
        today = timezone.now().date()
        tasks = self.queryset.filter(due_date__lt=today).exclude(status__in=['completed', 'cancelled'])
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """タスクを完了にする"""
        task = self.get_object()
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        serializer = TaskSerializer(task)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """タスクを再開する"""
        task = self.get_object()
        task.status = 'in_progress'
        task.completed_at = None
        task.save()
        serializer = TaskSerializer(task)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve_employee(self, request, pk=None):
        """社員登録タスクを承認する"""
        from apps.tenants.models import Employee
        from apps.users.models import User

        task = self.get_object()

        # 社員登録タスクかチェック
        if task.task_type != 'staff_registration' or task.source_type != 'employee':
            return Response(
                {'error': 'このタスクは社員登録承認タスクではありません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 社員を取得
        try:
            employee = Employee.objects.get(id=task.source_id)
        except Employee.DoesNotExist:
            return Response(
                {'error': '対象の社員が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 社員を有効化
        employee.is_active = True
        employee.save()

        # 関連するUserも有効化
        user = User.objects.filter(staff_id=employee.id).first()
        if user:
            user.is_active = True
            user.save()

        # タスクを完了にする
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()

        serializer = TaskSerializer(task)
        return Response({
            'success': True,
            'message': f'{employee.last_name} {employee.first_name}さんを承認しました',
            'task': serializer.data,
            'employee_id': str(employee.id),
        })

    @action(detail=True, methods=['post'])
    def reject_employee(self, request, pk=None):
        """社員登録タスクを却下する（データは保持）"""
        from apps.tenants.models import Employee
        from apps.users.models import User

        task = self.get_object()

        # 社員登録タスクかチェック
        if task.task_type != 'staff_registration' or task.source_type != 'employee':
            return Response(
                {'error': 'このタスクは社員登録承認タスクではありません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 却下理由を取得
        reason = request.data.get('reason', '')

        # 社員を取得
        try:
            employee = Employee.objects.get(id=task.source_id)
            employee_name = f'{employee.last_name} {employee.first_name}'

            # 社員を却下状態に更新（データは保持）
            employee.approval_status = 'rejected'
            employee.rejected_at = timezone.now()
            employee.rejected_reason = reason
            employee.is_active = False
            employee.save()

            # 関連するUserを無効化（削除せずに保持）
            User.objects.filter(staff_id=employee.id).update(is_active=False)
        except Employee.DoesNotExist:
            employee_name = '不明'

        # タスクをキャンセルにする
        task.status = 'cancelled'
        task.completed_at = timezone.now()
        task.save()

        serializer = TaskSerializer(task)
        return Response({
            'success': True,
            'message': f'{employee_name}さんの登録を却下しました',
            'task': serializer.data,
        })


class TaskCommentViewSet(viewsets.ModelViewSet):
    """作業コメント ViewSet"""
    queryset = TaskComment.objects.filter(deleted_at__isnull=True).order_by('created_at')
    serializer_class = TaskCommentSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['task', 'is_internal']

    def perform_create(self, serializer):
        """コメント作成時にテナントを設定"""
        tenant_id = self.request.user.tenant_id
        serializer.save(tenant_id=tenant_id, tenant_ref_id=tenant_id)

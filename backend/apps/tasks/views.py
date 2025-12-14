"""Task API views."""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import Task, TaskCategory, TaskComment
from .serializers import (
    TaskSerializer, TaskCreateUpdateSerializer,
    TaskCategorySerializer, TaskCommentSerializer
)


class TaskCategoryViewSet(viewsets.ModelViewSet):
    """作業カテゴリ ViewSet"""
    queryset = TaskCategory.objects.filter(deleted_at__isnull=True, is_active=True)
    serializer_class = TaskCategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['sort_order', 'category_code']
    ordering = ['sort_order']


class TaskViewSet(viewsets.ModelViewSet):
    """作業 ViewSet"""
    queryset = Task.objects.filter(deleted_at__isnull=True).select_related(
        'category', 'school', 'brand', 'student', 'guardian'
    ).order_by('-created_at')
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'task_type', 'school', 'brand', 'student']
    search_fields = ['title', 'description', 'student__last_name', 'student__first_name']
    ordering_fields = ['created_at', 'due_date', 'priority', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TaskCreateUpdateSerializer
        return TaskSerializer

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


class TaskCommentViewSet(viewsets.ModelViewSet):
    """作業コメント ViewSet"""
    queryset = TaskComment.objects.filter(deleted_at__isnull=True).order_by('created_at')
    serializer_class = TaskCommentSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['task', 'is_internal']

"""Task URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, TaskCategoryViewSet, TaskCommentViewSet

app_name = 'tasks'

router = DefaultRouter()
router.register(r'categories', TaskCategoryViewSet, basename='task-category')
router.register(r'comments', TaskCommentViewSet, basename='task-comment')
router.register(r'', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
]

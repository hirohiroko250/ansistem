"""
Knowledge URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ManualCategoryViewSet, ManualViewSet,
    TemplateCategoryViewSet, ChatTemplateViewSet,
)

app_name = 'knowledge'

router = DefaultRouter()
router.register(r'manual-categories', ManualCategoryViewSet, basename='manual-category')
router.register(r'manuals', ManualViewSet, basename='manual')
router.register(r'template-categories', TemplateCategoryViewSet, basename='template-category')
router.register(r'templates', ChatTemplateViewSet, basename='template')

urlpatterns = [
    path('', include(router.urls)),
]

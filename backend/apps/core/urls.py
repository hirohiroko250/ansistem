"""
Core URLs - Health check and File Upload
"""
from django.urls import path
from .views import health_check, upload_file, upload_multiple_files

urlpatterns = [
    path('', health_check, name='health-check'),
    path('upload/', upload_file, name='upload-file'),
    path('upload/multiple/', upload_multiple_files, name='upload-multiple-files'),
]

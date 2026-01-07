"""
Core URLs - Health check and File Upload
"""
from django.urls import path
from .views import health_check, system_info, upload_file, upload_multiple_files

app_name = 'core'

urlpatterns = [
    path('', health_check, name='health-check'),
    path('info/', system_info, name='system-info'),
    path('upload/', upload_file, name='upload-file'),
    path('upload/multiple/', upload_multiple_files, name='upload-multiple-files'),
]

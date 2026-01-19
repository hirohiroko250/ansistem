"""
Core URLs - Health check and File Upload
"""
from django.urls import path, re_path
from .views import health_check, system_info, upload_file, upload_multiple_files, serve_media

app_name = 'core'

urlpatterns = [
    path('', health_check, name='health-check'),
    path('info/', system_info, name='system-info'),
    path('upload/', upload_file, name='upload-file'),
    path('upload/multiple/', upload_multiple_files, name='upload-multiple-files'),
    # メディアファイル配信（/api/v1/core/media/...でアクセス可能）
    re_path(r'^media/(?P<path>.*)$', serve_media, name='api-serve-media'),
]

"""
URL configuration for OZA System project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from apps.core.views import serve_media

urlpatterns = [
    # Django Admin (use /django-admin/ to avoid conflict with frontend /admin)
    path('django-admin/', admin.site.urls),

    # API v1
    path('api/v1/', include('api.v1.urls')),

    # Legacy paths (without /api/v1/ prefix) for backward compatibility
    # フロントエンドの環境変数が /api/v1 を含まない場合のフォールバック
    # namespace を省略してルーティングのみを提供
    path('schools/', include(('apps.schools.urls', 'schools_legacy'))),
    path('auth/', include(('apps.authentication.urls', 'auth_legacy'))),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Health check
    path('health/', include('apps.core.urls')),

    # Media files (for development/staging - use nginx/CDN in production)
    re_path(r'^media/(?P<path>.*)$', serve_media, name='serve-media'),
]

# Debug toolbar URLs (development only)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

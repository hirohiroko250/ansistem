"""
ASGI config for OZA System project.
WebSocket support via Django Channels
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application

from apps.communications.routing import websocket_urlpatterns
from apps.communications.middleware import JWTAuthMiddleware

django_asgi_app = get_asgi_application()

# WebSocket用のOrigin許可リストを構築
# CORS_ALLOWED_ORIGINSまたはCSRF_TRUSTED_ORIGINSから取得
allowed_origins = []
if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
    allowed_origins.extend(settings.CORS_ALLOWED_ORIGINS)
if hasattr(settings, 'CSRF_TRUSTED_ORIGINS'):
    allowed_origins.extend(settings.CSRF_TRUSTED_ORIGINS)

# 開発環境用のデフォルト許可Origin追加
default_origins = [
    'http://localhost:3000',
    'http://localhost:3001',
    'http://localhost:3002',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:3001',
    'http://127.0.0.1:3002',
]
allowed_origins.extend(default_origins)

# 重複を除去
allowed_origins = list(set(allowed_origins))

# DEBUGモードの場合は全てのOriginを許可
if settings.DEBUG:
    allowed_origins = ['*']

websocket_application = JWTAuthMiddleware(
    URLRouter(websocket_urlpatterns)
)

# OriginValidatorでOriginをチェック（'*'の場合は全許可）
if '*' in allowed_origins:
    # 全許可の場合はValidatorをスキップ
    websocket_with_origin = websocket_application
else:
    websocket_with_origin = OriginValidator(
        websocket_application,
        allowed_origins
    )

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": websocket_with_origin,
})

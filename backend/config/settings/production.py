"""
Django settings for OZA System project - Production Configuration
"""
import os
from .base import *

DEBUG = False

# Security: Ensure SECRET_KEY is set in production
if SECRET_KEY.startswith('django-insecure') or 'change-this' in SECRET_KEY.lower():
    raise ValueError(
        "SECRET_KEY is not set or using insecure default. "
        "Set DJANGO_SECRET_KEY environment variable with a secure random key."
    )

# Security: Ensure JWT_SECRET_KEY is set separately in production (optional but recommended)
JWT_SECRET = os.environ.get('JWT_SECRET_KEY')
if JWT_SECRET:
    SIMPLE_JWT['SIGNING_KEY'] = JWT_SECRET

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# SSL settings - only enable if using HTTPS (set via environment variable)
USE_SSL = os.environ.get('USE_SSL', 'False').lower() == 'true'
SECURE_SSL_REDIRECT = USE_SSL
SESSION_COOKIE_SECURE = USE_SSL
CSRF_COOKIE_SECURE = USE_SSL
if USE_SSL:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# CSRF trusted origins (for production server)
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:3000,http://localhost:3001'
).split(',')

# Static files with WhiteNoise
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# WhiteNoise middleware - must be added after SecurityMiddleware
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Ensure logs directory exists
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Logging - 本番環境ではJSON形式
USE_JSON_LOGS = os.environ.get('USE_JSON_LOGS', 'True').lower() == 'true'

LOGGING['handlers']['file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': LOGS_DIR / 'django.log',
    'maxBytes': 1024 * 1024 * 10,  # 10 MB
    'backupCount': 10,
    'formatter': 'json' if USE_JSON_LOGS else 'verbose',
}

LOGGING['handlers']['error_file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': LOGS_DIR / 'error.log',
    'maxBytes': 1024 * 1024 * 10,  # 10 MB
    'backupCount': 10,
    'formatter': 'json' if USE_JSON_LOGS else 'verbose',
    'level': 'ERROR',
}

# コンソールもJSON形式に
if USE_JSON_LOGS:
    LOGGING['handlers']['console']['formatter'] = 'json'

# ルートハンドラーにファイル追加
LOGGING['root']['handlers'].extend(['file', 'error_file'])

# 本番用ログレベル調整
LOGGING['loggers']['apps']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'WARNING'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.lolipop.jp')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '465'))
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True').lower() == 'true'
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'info@oz-a.jp')

# Frontend URL for email links
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

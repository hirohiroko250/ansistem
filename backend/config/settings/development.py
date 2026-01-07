"""
Django settings for OZA System project - Development Configuration
"""
import os
from .base import *

DEBUG = True

# Debug toolbar (optional - only if installed)
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
except ImportError:
    pass

INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Database configuration
# Use PostgreSQL if DB_HOST is set (Docker environment), otherwise use SQLite
if os.environ.get('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'oza_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    # SQLite for quick local development without Docker
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Email settings - Use SMTP if credentials are provided, otherwise console
if os.environ.get('EMAIL_HOST_USER') and os.environ.get('EMAIL_HOST_PASSWORD'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.lolipop.jp')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '465'))
    EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True').lower() == 'true'
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False').lower() == 'true'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Frontend URL for email links
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Debug toolbar configuration
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
}

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# CORS - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True
# Override CORS_ALLOWED_ORIGINS from base.py (must be empty when CORS_ALLOW_ALL_ORIGINS is True)
CORS_ALLOWED_ORIGINS = []

# Add simple CORS middleware as fallback (put it first in MIDDLEWARE)
MIDDLEWARE.insert(0, 'config.cors_middleware.SimpleCORSMiddleware')

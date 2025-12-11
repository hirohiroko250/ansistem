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

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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

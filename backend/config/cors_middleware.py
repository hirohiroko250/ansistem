"""
Simple CORS Middleware as a fallback for development only
"""
from django.conf import settings


class SimpleCORSMiddleware:
    """
    Simple CORS middleware that allows all origins.
    Used as a fallback when django-cors-headers doesn't work properly.

    WARNING: This middleware should only be used in development.
    In production, use django-cors-headers with explicit allowed origins.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Safety check: warn if used in non-debug mode
        if not getattr(settings, 'DEBUG', False):
            import warnings
            warnings.warn(
                "SimpleCORSMiddleware is being used with DEBUG=False. "
                "This allows all origins and should only be used in development.",
                RuntimeWarning
            )

    def __call__(self, request):
        response = self.get_response(request)

        # Only allow all origins in DEBUG mode
        # In production, fall through to django-cors-headers
        if not getattr(settings, 'DEBUG', False):
            return response

        # Add CORS headers (development only)
        origin = request.META.get('HTTP_ORIGIN')
        if origin:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Accept, Accept-Language, Content-Type, Authorization, X-CSRFToken, X-Requested-With, X-Tenant-Id'
            response['Access-Control-Max-Age'] = '86400'

        return response

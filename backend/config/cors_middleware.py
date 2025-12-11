"""
Simple CORS Middleware as a fallback
"""


class SimpleCORSMiddleware:
    """
    Simple CORS middleware that allows all origins.
    Used as a fallback when django-cors-headers doesn't work properly.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response = self.get_response(request)
        else:
            response = self.get_response(request)

        # Add CORS headers
        origin = request.META.get('HTTP_ORIGIN')
        if origin:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Accept, Accept-Language, Content-Type, Authorization, X-CSRFToken, X-Requested-With, X-Tenant-Id'
            response['Access-Control-Max-Age'] = '86400'

        return response

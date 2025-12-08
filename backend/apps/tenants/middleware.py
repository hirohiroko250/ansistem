"""Tenant middleware."""


class TenantMiddleware:
    """Middleware to handle tenant context."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Placeholder tenant middleware
        response = self.get_response(request)
        return response

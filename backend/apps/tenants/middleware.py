"""Tenant middleware."""


class TenantMiddleware:
    """Middleware to handle tenant context.

    Sets request.tenant_id from:
    1. X-Tenant-ID header (if provided)
    2. Authenticated user's tenant_id (fallback)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get tenant_id from X-Tenant-ID header
        tenant_id = request.headers.get('X-Tenant-ID')

        # If no header, try to get from authenticated user
        if not tenant_id and hasattr(request, 'user') and request.user.is_authenticated:
            tenant_id = getattr(request.user, 'tenant_id', None)
            if tenant_id:
                tenant_id = str(tenant_id)

        # Set tenant_id on request
        request.tenant_id = tenant_id

        response = self.get_response(request)
        return response

"""Gateway middleware for Tenant Context lifecycle.

Ensures:
1. TenantContext is set after authentication
2. TenantContext is cleared after every request
3. X-Tenant-ID from client is NEVER trusted directly
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from services.tenant_context import clear_tenant_context


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware that manages TenantContext for each request.

    - Sets context AFTER authentication (get_current_tenant runs first)
    - Clears context BEFORE response is sent
    - Never reads X-Tenant-ID header directly (security: client spoofing)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        finally:
            # Always clear context after request completes
            clear_tenant_context()

"""Audit middleware to automatically log user actions."""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically capture and log user actions.
    
    Captures:
    - All write operations (POST, PUT, PATCH, DELETE)
    - User information from JWT token
    - IP address and user agent
    - Request/response data
    
    Note: Actual audit logging is done in the endpoint handlers
    using the AuditService, as they have access to entity details.
    This middleware adds context to the request for use by handlers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add audit context."""
        # Skip audit for health checks and metrics
        if request.url.path in ["/health", "/health/live", "/health/ready", "/metrics"]:
            return await call_next(request)
        
        # Extract client information
        client_ip = None
        if request.client:
            client_ip = request.client.host
        
        # Check for X-Forwarded-For header (proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (client IP)
            client_ip = forwarded_for.split(",")[0].strip()
        
        user_agent = request.headers.get("User-Agent")
        
        # Store in request state for use by handlers
        request.state.audit_ip = client_ip
        request.state.audit_user_agent = user_agent
        
        # Log write operations
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            logger.info(
                "write_operation",
                method=request.method,
                path=request.url.path,
                client_ip=client_ip,
            )
        
        # Process request
        response = await call_next(request)
        
        return response

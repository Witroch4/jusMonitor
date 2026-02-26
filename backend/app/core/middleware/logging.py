"""Logging middleware to add request context."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import bind_context, clear_context, get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add logging context and log requests.
    
    Adds to context:
    - request_id: Unique identifier for the request
    - tenant_id: From JWT token (if authenticated)
    - user_id: From JWT token (if authenticated)
    - path: Request path
    - method: HTTP method
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add logging context."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Clear any existing context
        clear_context()
        
        # Bind request context
        bind_context(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        
        # Extract tenant_id and user_id from request state (set by auth middleware)
        if hasattr(request.state, "tenant_id"):
            bind_context(tenant_id=str(request.state.tenant_id))
        
        if hasattr(request.state, "user_id"):
            bind_context(user_id=str(request.state.user_id))
        
        # Log request start
        start_time = time.time()
        logger.info(
            "request_started",
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log request completion
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_seconds=round(duration, 3),
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
        
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(duration, 3),
                exc_info=True,
            )
            raise
        
        finally:
            # Clear context after request
            clear_context()

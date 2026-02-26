"""Middleware for tracking in-flight requests during shutdown."""

from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.shutdown import get_shutdown_handler

logger = structlog.get_logger(__name__)


class ShutdownMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track in-flight requests and reject new requests during shutdown.
    
    This middleware:
    - Tracks the number of in-flight requests
    - Rejects new requests with 503 when shutdown is initiated
    - Allows graceful completion of existing requests
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request and track in-flight status.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
        
        Returns:
            HTTP response
        """
        shutdown_handler = get_shutdown_handler()

        # Reject new requests if shutdown is in progress
        if shutdown_handler.is_shutting_down:
            logger.warning(
                "request_rejected_shutdown",
                path=request.url.path,
                method=request.method,
            )
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Server is shutting down. Please try again later.",
                    "error": "service_unavailable",
                },
                headers={
                    "Retry-After": "30",  # Suggest retry after 30 seconds
                },
            )

        # Track in-flight request
        shutdown_handler.increment_requests()
        
        try:
            response = await call_next(request)
            return response
        finally:
            shutdown_handler.decrement_requests()

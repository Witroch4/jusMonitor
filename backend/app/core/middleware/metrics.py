"""Metrics middleware to track HTTP requests."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.metrics import (
    http_error_rate,
    http_request_count,
    http_request_duration_seconds,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track HTTP request metrics.
    
    Tracks:
    - Request duration
    - Request count by method, path, and status
    - Error rate by type
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and record metrics."""
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Normalize path (remove IDs for better aggregation)
        path = self._normalize_path(request.url.path)
        method = request.method
        
        # Start timer
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            status_code = str(response.status_code)
            http_request_duration_seconds.labels(
                method=method,
                path=path,
                status_code=status_code,
            ).observe(duration)
            
            http_request_count.labels(
                method=method,
                path=path,
                status_code=status_code,
            ).inc()
            
            return response
        
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Record error metrics
            error_type = type(e).__name__
            http_error_rate.labels(
                method=method,
                path=path,
                error_type=error_type,
            ).inc()
            
            # Record duration with 500 status
            http_request_duration_seconds.labels(
                method=method,
                path=path,
                status_code="500",
            ).observe(duration)
            
            http_request_count.labels(
                method=method,
                path=path,
                status_code="500",
            ).inc()
            
            raise
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by removing UUIDs and IDs.
        
        Examples:
            /api/v1/clients/123e4567-e89b-12d3-a456-426614174000 -> /api/v1/clients/{id}
            /api/v1/cases/12345 -> /api/v1/cases/{id}
        """
        import re
        
        # Replace UUIDs
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{id}",
            path,
            flags=re.IGNORECASE,
        )
        
        # Replace numeric IDs
        path = re.sub(r"/\d+", "/{id}", path)
        
        return path

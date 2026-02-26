"""Cache middleware for HTTP responses with Cache-Control and ETag support."""

import hashlib
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add Cache-Control headers and ETag support.
    
    Features:
    - Adds Cache-Control headers based on route patterns
    - Generates ETags for cacheable responses
    - Handles If-None-Match conditional requests
    - Returns 304 Not Modified when appropriate
    """

    def __init__(
        self,
        app,
        default_max_age: int = 0,
        static_max_age: int = 86400,  # 1 day
        api_max_age: int = 60,  # 1 minute
    ):
        """
        Initialize cache middleware.
        
        Args:
            app: FastAPI application
            default_max_age: Default max-age in seconds (0 = no cache)
            static_max_age: Max-age for static resources in seconds
            api_max_age: Max-age for API responses in seconds
        """
        super().__init__(app)
        self.default_max_age = default_max_age
        self.static_max_age = static_max_age
        self.api_max_age = api_max_age

    def _get_cache_control(self, path: str, method: str) -> str:
        """
        Determine Cache-Control header based on path and method.
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            Cache-Control header value
        """
        # No cache for non-GET requests
        if method != "GET":
            return "no-store, no-cache, must-revalidate"
        
        # Static resources (docs, openapi, etc.)
        if any(
            path.startswith(prefix)
            for prefix in ["/docs", "/redoc", "/openapi.json"]
        ):
            return f"public, max-age={self.static_max_age}"
        
        # Health and metrics endpoints - short cache
        if path in ["/health", "/health/live", "/health/ready", "/metrics"]:
            return "public, max-age=10"
        
        # API endpoints - short cache with revalidation
        if path.startswith("/api/"):
            # Dashboard and metrics can be cached briefly
            if any(
                segment in path
                for segment in ["/dashboard", "/metrics", "/stats"]
            ):
                return f"private, max-age={self.api_max_age}, must-revalidate"
            
            # Most API endpoints should not be cached or very short cache
            return "private, max-age=0, must-revalidate"
        
        # Default: no cache
        return "no-store, no-cache, must-revalidate"

    def _generate_etag(self, content: bytes) -> str:
        """
        Generate ETag from response content.
        
        Args:
            content: Response body bytes
            
        Returns:
            ETag value (MD5 hash of content)
        """
        return f'"{hashlib.md5(content).hexdigest()}"'

    def _should_generate_etag(self, path: str, status_code: int) -> bool:
        """
        Determine if ETag should be generated for this response.
        
        Args:
            path: Request path
            status_code: Response status code
            
        Returns:
            True if ETag should be generated
        """
        # Only for successful GET requests
        if status_code != 200:
            return False
        
        # Generate ETags for static resources and cacheable API endpoints
        if any(
            path.startswith(prefix)
            for prefix in ["/docs", "/redoc", "/openapi.json"]
        ):
            return True
        
        # Generate ETags for dashboard and metrics
        if any(segment in path for segment in ["/dashboard", "/metrics", "/stats"]):
            return True
        
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add caching headers."""
        # Check for If-None-Match header (ETag conditional request)
        if_none_match = request.headers.get("if-none-match")
        
        # Process request
        response = await call_next(request)
        
        # Add Cache-Control header
        cache_control = self._get_cache_control(request.url.path, request.method)
        response.headers["Cache-Control"] = cache_control
        
        # Add Vary header to indicate response varies by encoding
        response.headers["Vary"] = "Accept-Encoding"
        
        # Generate and add ETag if applicable
        if self._should_generate_etag(request.url.path, response.status_code):
            # Get response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Generate ETag
            etag = self._generate_etag(body)
            response.headers["ETag"] = etag
            
            # Check if client's cached version is still valid
            if if_none_match and if_none_match == etag:
                logger.debug(
                    "etag_match",
                    path=request.url.path,
                    etag=etag,
                )
                # Return 304 Not Modified
                return Response(
                    status_code=304,
                    headers={
                        "Cache-Control": cache_control,
                        "ETag": etag,
                        "Vary": "Accept-Encoding",
                    },
                )
            
            # Recreate response with body
            from starlette.responses import Response as StarletteResponse
            
            response = StarletteResponse(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        
        return response


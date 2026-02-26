"""Rate limiting middleware using Redis for distributed counters."""

import time
from typing import Callable

import redis.asyncio as redis
import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware using Redis for distributed counters.
    
    Implements sliding window rate limiting with different limits per endpoint type:
    - General endpoints: 100 req/min
    - AI endpoints: 10 req/min
    
    Returns 429 Too Many Requests with Retry-After header when limit exceeded.
    
    Uses Redis for distributed rate limiting across multiple instances.
    """
    
    # AI endpoints that have stricter rate limits
    AI_ENDPOINTS = {
        "/api/v1/ai",
        "/api/v1/briefing",
        "/api/v1/translate",
        "/api/v1/leads/qualify",
        "/api/v1/clients/analyze",
    }
    
    # Endpoints excluded from rate limiting
    EXCLUDED_PATHS = {
        "/health",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    def __init__(self, app):
        """Initialize rate limiter with Redis connection."""
        super().__init__(app)
        self.redis: redis.Redis | None = None
        self._connected = False
    
    async def _connect_redis(self) -> None:
        """Connect to Redis if not already connected."""
        if self._connected and self.redis:
            return
        
        try:
            self.redis = redis.from_url(
                str(settings.redis_url),
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self.redis.ping()
            self._connected = True
            logger.info("rate_limit_redis_connected")
        except Exception as e:
            logger.error("rate_limit_redis_connection_failed", error=str(e))
            self.redis = None
            self._connected = False
    
    def _get_rate_limit(self, path: str) -> int:
        """
        Get rate limit for the given path.
        
        Args:
            path: Request path
            
        Returns:
            Rate limit (requests per minute)
        """
        # Check if it's an AI endpoint
        for ai_path in self.AI_ENDPOINTS:
            if path.startswith(ai_path):
                return settings.rate_limit_ai_per_minute
        
        # Default to general rate limit
        return settings.rate_limit_per_minute
    
    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for the client.
        
        Uses (in order of preference):
        1. User ID from JWT token (if authenticated)
        2. Tenant ID from JWT token (if authenticated)
        3. Client IP address
        
        Args:
            request: FastAPI request
            
        Returns:
            Client identifier string
        """
        # Try to get user_id from request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Try to get tenant_id from request state (set by tenant middleware)
        if hasattr(request.state, "tenant_id"):
            return f"tenant:{request.state.tenant_id}"
        
        # Fall back to IP address
        if request.client:
            return f"ip:{request.client.host}"
        
        # Last resort: use a generic identifier
        return "unknown"
    
    def _make_redis_key(self, client_id: str, window: int) -> str:
        """
        Create Redis key for rate limiting.
        
        Args:
            client_id: Client identifier
            window: Time window (minute timestamp)
            
        Returns:
            Redis key
        """
        return f"jusmonitor:ratelimit:{client_id}:{window}"
    
    async def _check_rate_limit(
        self,
        client_id: str,
        limit: int,
    ) -> tuple[bool, int, int]:
        """
        Check if client has exceeded rate limit using sliding window.
        
        Args:
            client_id: Client identifier
            limit: Rate limit (requests per minute)
            
        Returns:
            Tuple of (allowed, current_count, retry_after_seconds)
        """
        if not self._connected or not self.redis:
            # If Redis is down, allow the request (fail open)
            logger.warning("rate_limit_redis_unavailable", client_id=client_id)
            return True, 0, 0
        
        try:
            # Get current minute window
            current_time = int(time.time())
            current_window = current_time // 60
            
            # Redis key for current window
            key = self._make_redis_key(client_id, current_window)
            
            # Increment counter
            count = await self.redis.incr(key)
            
            # Set expiration on first request (2 minutes to handle sliding window)
            if count == 1:
                await self.redis.expire(key, 120)
            
            # Check if limit exceeded
            if count > limit:
                # Calculate retry after (seconds until next window)
                retry_after = 60 - (current_time % 60)
                logger.warning(
                    "rate_limit_exceeded",
                    client_id=client_id,
                    count=count,
                    limit=limit,
                    retry_after=retry_after,
                )
                return False, count, retry_after
            
            logger.debug(
                "rate_limit_check",
                client_id=client_id,
                count=count,
                limit=limit,
            )
            
            return True, count, 0
        
        except Exception as e:
            # If Redis operation fails, allow the request (fail open)
            logger.error("rate_limit_check_error", error=str(e), client_id=client_id)
            return True, 0, 0
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and apply rate limiting."""
        
        # Skip rate limiting if disabled
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Ensure Redis connection
        await self._connect_redis()
        
        # Get rate limit for this endpoint
        limit = self._get_rate_limit(request.url.path)
        
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        # Check rate limit
        allowed, current_count, retry_after = await self._check_rate_limit(
            client_id, limit
        )
        
        if not allowed:
            # Rate limit exceeded - return 429
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "limit": limit,
                    "current": current_count,
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                },
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        # Add rate limit info headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current_count))
        response.headers["X-RateLimit-Reset"] = str(
            (int(time.time()) // 60 + 1) * 60
        )
        
        return response

"""Tenant isolation middleware for multi-tenant architecture."""

import logging
from typing import Callable
from uuid import UUID

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate tenant_id from requests.
    
    Extracts tenant_id from:
    1. X-Tenant-ID header (for service-to-service calls)
    2. JWT token payload (for authenticated user requests)
    
    Injects tenant_id into request.state for use in repositories and services.
    Returns 403 if tenant_id is invalid or missing for protected routes.
    """
    
    # Routes that don't require tenant isolation
    EXCLUDED_PATHS = {
        "/health",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
    }
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and inject tenant_id."""
        
        # Skip tenant validation for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Extract tenant_id from header or JWT
        tenant_id = await self._extract_tenant_id(request)
        
        if tenant_id is None:
            logger.warning(
                "Missing tenant_id for protected route",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client": request.client.host if request.client else None,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Tenant identification required. "
                    "Provide X-Tenant-ID header or valid JWT token."
                },
            )
        
        # Inject tenant_id into request state
        request.state.tenant_id = tenant_id
        
        logger.debug(
            "Tenant context established",
            extra={
                "tenant_id": str(tenant_id),
                "path": request.url.path,
            },
        )
        
        # Continue processing request
        response = await call_next(request)
        return response
    
    async def _extract_tenant_id(self, request: Request) -> UUID | None:
        """
        Extract tenant_id from X-Tenant-ID header or JWT token.
        
        Priority:
        1. X-Tenant-ID header (for service-to-service calls)
        2. JWT token payload (for user requests)
        
        Returns:
            UUID: Tenant ID if found and valid
            None: If tenant_id not found or invalid
        """
        # Try X-Tenant-ID header first
        tenant_id_header = request.headers.get("X-Tenant-ID")
        if tenant_id_header:
            try:
                return UUID(tenant_id_header)
            except (ValueError, AttributeError) as e:
                logger.warning(
                    "Invalid X-Tenant-ID header format",
                    extra={"header_value": tenant_id_header, "error": str(e)},
                )
                return None
        
        # Try extracting from JWT token
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        # Extract token from "Bearer <token>" format
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                logger.warning(
                    "Invalid authorization scheme",
                    extra={"scheme": scheme},
                )
                return None
        except ValueError:
            logger.warning("Malformed Authorization header")
            return None
        
        # Decode JWT and extract tenant_id
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            tenant_id_str = payload.get("tenant_id")
            
            if not tenant_id_str:
                logger.warning("JWT token missing tenant_id claim")
                return None
            
            return UUID(tenant_id_str)
            
        except JWTError as e:
            logger.warning(
                "JWT token validation failed",
                extra={"error": str(e)},
            )
            return None
        except (ValueError, AttributeError) as e:
            logger.warning(
                "Invalid tenant_id format in JWT",
                extra={"error": str(e)},
            )
            return None

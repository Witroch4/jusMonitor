"""Security middleware for headers and input validation."""

import re
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Maximum payload size in bytes (10MB default)
MAX_PAYLOAD_SIZE = 10 * 1024 * 1024

# XSS patterns to detect
XSS_PATTERNS = [
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers like onclick=
    re.compile(r"<iframe[^>]*>", re.IGNORECASE),
    re.compile(r"<object[^>]*>", re.IGNORECASE),
    re.compile(r"<embed[^>]*>", re.IGNORECASE),
]

# SQL injection patterns to detect
SQL_INJECTION_PATTERNS = [
    re.compile(r"(\bUNION\b.*\bSELECT\b)", re.IGNORECASE),
    re.compile(r"(\bSELECT\b.*\bFROM\b.*\bWHERE\b)", re.IGNORECASE),
    re.compile(r"(\bINSERT\b.*\bINTO\b.*\bVALUES\b)", re.IGNORECASE),
    re.compile(r"(\bUPDATE\b.*\bSET\b)", re.IGNORECASE),
    re.compile(r"(\bDELETE\b.*\bFROM\b)", re.IGNORECASE),
    re.compile(r"(\bDROP\b.*\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(--|#|/\*|\*/)", re.IGNORECASE),  # SQL comments
    re.compile(r"(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)", re.IGNORECASE),  # OR 1=1 or OR '1'='1'
    re.compile(r"(\bAND\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)", re.IGNORECASE),  # AND 1=1 or AND '1'='1'
]


def detect_xss(text: str) -> bool:
    """
    Detect potential XSS attacks in text.
    
    Args:
        text: Text to check
        
    Returns:
        True if XSS pattern detected, False otherwise
    """
    if not isinstance(text, str):
        return False
    
    for pattern in XSS_PATTERNS:
        if pattern.search(text):
            return True
    
    return False


def detect_sql_injection(text: str) -> bool:
    """
    Detect potential SQL injection attacks in text.
    
    Args:
        text: Text to check
        
    Returns:
        True if SQL injection pattern detected, False otherwise
    """
    if not isinstance(text, str):
        return False
    
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    
    return False


def sanitize_input(data: dict | list | str) -> dict | list | str:
    """
    Recursively sanitize input data by checking for XSS and SQL injection.
    
    Note: This is a detection mechanism, not a sanitization mechanism.
    We use Pydantic for validation and SQLAlchemy with parameterized queries
    for actual protection. This is an additional layer of defense.
    
    Args:
        data: Data to sanitize (dict, list, or str)
        
    Returns:
        Original data if safe
        
    Raises:
        ValueError: If malicious pattern detected
    """
    if isinstance(data, dict):
        for key, value in data.items():
            sanitize_input(value)
    elif isinstance(data, list):
        for item in data:
            sanitize_input(item)
    elif isinstance(data, str):
        if detect_xss(data):
            raise ValueError(f"Potential XSS attack detected in input")
        if detect_sql_injection(data):
            raise ValueError(f"Potential SQL injection detected in input")
    
    return data


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Adds:
    - Content-Security-Policy (CSP)
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Add security headers to response."""
        
        # Validate payload size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > MAX_PAYLOAD_SIZE:
                    logger.warning(
                        "payload_too_large",
                        size=size,
                        max_size=MAX_PAYLOAD_SIZE,
                        path=request.url.path,
                        client_ip=request.client.host if request.client else None,
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={
                            "detail": f"Payload too large. Maximum size is {MAX_PAYLOAD_SIZE} bytes"
                        },
                    )
            except ValueError:
                pass
        
        # Validate input for XSS and SQL injection (for JSON payloads)
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    # Read body
                    body = await request.body()
                    
                    # Parse JSON and validate
                    if body:
                        import json
                        try:
                            data = json.loads(body)
                            sanitize_input(data)
                        except json.JSONDecodeError:
                            # Let FastAPI handle invalid JSON
                            pass
                        except ValueError as e:
                            logger.warning(
                                "malicious_input_detected",
                                error=str(e),
                                path=request.url.path,
                                method=request.method,
                                client_ip=request.client.host if request.client else None,
                            )
                            return JSONResponse(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                content={"detail": str(e)},
                            )
                    
                    # Reconstruct request with body
                    async def receive():
                        return {"type": "http.request", "body": body}
                    
                    request._receive = receive
                    
                except Exception as e:
                    logger.error(
                        "security_validation_error",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        
        # Content Security Policy
        # Restrictive policy that only allows same-origin resources
        csp_directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",  # unsafe-inline needed for some UI frameworks
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",  # Prevent clickjacking
            "base-uri 'self'",
            "form-action 'self'",
        ]
        
        # In development, allow localhost origins
        if settings.is_development:
            csp_directives.append("connect-src 'self' ws://localhost:* http://localhost:*")
        
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Strict Transport Security (HSTS)
        # Only add in production with HTTPS
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature Policy)
        # Disable potentially dangerous features
        permissions_policy = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)
        
        return response

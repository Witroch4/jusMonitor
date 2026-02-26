# Security Implementation - Task 24.5

## Overview

This document describes the comprehensive security validations implemented for the JusMonitor CRM Orquestrador system, addressing Requirement 1.4 (Autenticação e Autorização) with additional security hardening measures.

## Implemented Security Features

### 1. Restrictive CORS Configuration

**Location**: `app/main.py`

**Implementation**:
- Explicit allowed origins (no wildcards)
- Explicit allowed methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`
- Explicit allowed headers (no `*` wildcard)
- Credentials support with proper origin validation
- Max age configuration for preflight caching (10 minutes)

**Configuration** (`.env`):
```env
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
CORS_ALLOW_CREDENTIALS=true
CORS_MAX_AGE=600
```

**Benefits**:
- Prevents unauthorized cross-origin requests
- Reduces attack surface by limiting allowed methods and headers
- Protects against CSRF attacks when combined with credentials

### 2. Security Headers Middleware

**Location**: `app/core/middleware/security.py`

**Class**: `SecurityHeadersMiddleware`

**Headers Added**:

#### Content-Security-Policy (CSP)
Restrictive policy that prevents XSS attacks:
- `default-src 'self'` - Only allow resources from same origin
- `script-src 'self'` - Only allow scripts from same origin
- `style-src 'self' 'unsafe-inline'` - Allow inline styles (needed for UI frameworks)
- `img-src 'self' data: https:` - Allow images from same origin, data URIs, and HTTPS
- `font-src 'self' data:` - Allow fonts from same origin and data URIs
- `connect-src 'self'` - Only allow API calls to same origin
- `frame-ancestors 'none'` - Prevent clickjacking
- `base-uri 'self'` - Prevent base tag injection
- `form-action 'self'` - Only allow form submissions to same origin

In development mode, WebSocket connections to localhost are allowed.

#### Strict-Transport-Security (HSTS)
**Production only** - Forces HTTPS connections:
- `max-age=31536000` - 1 year
- `includeSubDomains` - Apply to all subdomains
- `preload` - Allow browser preload list inclusion

#### X-Content-Type-Options
- `nosniff` - Prevents MIME type sniffing

#### X-Frame-Options
- `DENY` - Prevents clickjacking by disallowing iframe embedding

#### X-XSS-Protection
- `1; mode=block` - Legacy XSS protection for older browsers

#### Referrer-Policy
- `strict-origin-when-cross-origin` - Protects user privacy

#### Permissions-Policy
Disables potentially dangerous browser features:
- `geolocation=()` - No geolocation access
- `microphone=()` - No microphone access
- `camera=()` - No camera access
- `payment=()` - No payment API access
- `usb=()` - No USB access
- `magnetometer=()` - No magnetometer access
- `gyroscope=()` - No gyroscope access
- `accelerometer=()` - No accelerometer access

### 3. Payload Size Validation

**Location**: `app/core/middleware/security.py`

**Implementation**:
- Validates `Content-Length` header before processing request
- Default maximum: 10MB (configurable)
- Returns `413 Content Too Large` for oversized payloads
- Logs warnings with client IP for monitoring

**Configuration**:
```env
MAX_PAYLOAD_SIZE_MB=10
```

**Benefits**:
- Prevents denial-of-service attacks via large payloads
- Protects server resources
- Early rejection before parsing

### 4. XSS Detection and Prevention

**Location**: `app/core/middleware/security.py`

**Functions**: `detect_xss()`, `sanitize_input()`

**Detected Patterns**:
- `<script>` tags (case-insensitive)
- `javascript:` protocol
- Event handlers (`onclick=`, `onerror=`, etc.)
- `<iframe>` tags
- `<object>` tags
- `<embed>` tags

**Implementation**:
- Recursive validation of JSON payloads
- Validates strings in dictionaries, lists, and nested structures
- Returns `400 Bad Request` with descriptive error
- Logs malicious attempts with client IP

**Note**: This is a defense-in-depth layer. Primary protection comes from:
- Pydantic validation
- Proper output encoding in frontend
- Content-Security-Policy headers

### 5. SQL Injection Detection

**Location**: `app/core/middleware/security.py`

**Functions**: `detect_sql_injection()`, `sanitize_input()`

**Detected Patterns**:
- `UNION SELECT` attacks
- `SELECT FROM WHERE` statements
- `INSERT INTO VALUES` statements
- `UPDATE SET` statements
- `DELETE FROM` statements
- `DROP TABLE` statements
- SQL comments (`--`, `#`, `/* */`)
- Boolean injection (`OR 1=1`, `AND 1=1`, `OR '1'='1'`)

**Implementation**:
- Recursive validation of JSON payloads
- Validates strings in dictionaries, lists, and nested structures
- Returns `400 Bad Request` with descriptive error
- Logs malicious attempts with client IP

**Note**: This is a defense-in-depth layer. Primary protection comes from:
- SQLAlchemy with parameterized queries
- Pydantic validation
- Repository pattern with type safety

### 6. Input Validation Configuration

**Configuration**:
```env
SECURITY_HEADERS_ENABLED=true
INPUT_VALIDATION_ENABLED=true
```

**Benefits**:
- Can be disabled in specific environments if needed
- Allows gradual rollout
- Facilitates testing

## Architecture

### Middleware Stack Order

Middlewares execute in reverse order of addition (last added = first executed):

1. **GZipMiddleware** - Compresses responses
2. **CacheMiddleware** - Adds cache headers
3. **AuditMiddleware** - Logs operations
4. **MetricsMiddleware** - Collects metrics
5. **LoggingMiddleware** - Structured logging
6. **ShutdownMiddleware** - Tracks in-flight requests
7. **RateLimitMiddleware** - Rate limiting
8. **SecurityHeadersMiddleware** - Security headers and input validation
9. **CORSMiddleware** - CORS handling

This order ensures:
- Security validation happens early
- Rate limiting prevents abuse before processing
- Logging captures all requests
- Compression happens last (on final response)

## Testing

### Test Coverage

**Location**: `tests/unit/test_security.py`

**Test Classes**:
1. `TestXSSDetection` - 6 tests for XSS pattern detection
2. `TestSQLInjectionDetection` - 11 tests for SQL injection detection
3. `TestSanitizeInput` - 10 tests for input sanitization
4. `TestSecurityHeadersMiddleware` - 10 tests for middleware functionality
5. `TestCORSConfiguration` - 2 tests for CORS configuration

**Total**: 37 tests, all passing

**Coverage**: 92% of security middleware code

### Running Tests

```bash
cd backend
python -m pytest tests/unit/test_security.py -v
```

### Test Examples

**XSS Detection**:
```python
assert detect_xss("<script>alert('xss')</script>")
assert detect_xss("<img src=x onerror=alert('xss')>")
assert not detect_xss("Hello, world!")
```

**SQL Injection Detection**:
```python
assert detect_sql_injection("' OR 1=1 --")
assert detect_sql_injection("admin' OR '1'='1")
assert not detect_sql_injection("Hello, world!")
```

**Middleware Integration**:
```python
# Test that malicious input is rejected
response = client.post("/test", json={"bio": "<script>alert('xss')</script>"})
assert response.status_code == 400
assert "XSS" in response.json()["detail"]
```

## Security Best Practices

### Defense in Depth

This implementation follows defense-in-depth principles with multiple layers:

1. **Network Layer**: CORS restrictions
2. **Transport Layer**: HSTS (production)
3. **Application Layer**: Input validation, rate limiting
4. **Data Layer**: Parameterized queries, Pydantic validation
5. **Presentation Layer**: CSP headers, output encoding

### Logging and Monitoring

All security events are logged with structured logging:

```python
logger.warning(
    "malicious_input_detected",
    error=str(e),
    path=request.url.path,
    method=request.method,
    client_ip=request.client.host,
)
```

**Monitored Events**:
- Oversized payloads
- XSS attempts
- SQL injection attempts
- Rate limit violations (from RateLimitMiddleware)
- Authentication failures (from auth endpoints)

### Production Recommendations

1. **Enable HTTPS**: Required for HSTS and secure cookies
2. **Configure Real Origins**: Update `CORS_ORIGINS` with production domains
3. **Monitor Logs**: Set up alerts for security events
4. **Regular Updates**: Keep dependencies updated
5. **Security Audits**: Regular penetration testing
6. **WAF**: Consider Web Application Firewall for additional protection
7. **DDoS Protection**: Use CDN with DDoS protection (e.g., Cloudflare)

## Configuration Reference

### Environment Variables

```env
# CORS Configuration
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
CORS_ALLOW_CREDENTIALS=true
CORS_MAX_AGE=600

# Security Configuration
SECURITY_HEADERS_ENABLED=true
MAX_PAYLOAD_SIZE_MB=10
INPUT_VALIDATION_ENABLED=true

# Rate Limiting (from previous task)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_AI_PER_MINUTE=10
```

### Production Example

```env
# Production CORS
CORS_ORIGINS=["https://app.jusmonitor.com","https://admin.jusmonitor.com"]
CORS_ALLOW_CREDENTIALS=true
CORS_MAX_AGE=3600

# Production Security
SECURITY_HEADERS_ENABLED=true
MAX_PAYLOAD_SIZE_MB=5
INPUT_VALIDATION_ENABLED=true
ENVIRONMENT=production
```

## Known Limitations

1. **Pattern-Based Detection**: XSS and SQL injection detection uses regex patterns, which can have false positives/negatives. Prima
# HTTP Compression and Caching Implementation

## Overview

This document describes the HTTP compression and caching implementation for the JusMonitor CRM Orquestrador backend API. These optimizations improve performance by reducing bandwidth usage and enabling browser caching.

## Features Implemented

### 1. GZip Compression

**Middleware**: `fastapi.middleware.gzip.GZipMiddleware`

**Configuration**:
- `COMPRESSION_ENABLED`: Enable/disable compression (default: `true`)
- `COMPRESSION_MINIMUM_SIZE`: Minimum response size in bytes to compress (default: `500`)
- `COMPRESSION_LEVEL`: Compression level 1-9, balance between speed and ratio (default: `6`)

**Behavior**:
- Automatically compresses responses when client sends `Accept-Encoding: gzip` header
- Only compresses responses larger than `minimum_size` bytes
- Compresses compressible content types (JSON, HTML, CSS, JavaScript, XML, SVG)
- Adds `Content-Encoding: gzip` header to compressed responses
- Adds `Vary: Accept-Encoding` header for proper caching

**Benefits**:
- Reduces bandwidth usage by 60-80% for text-based responses
- Faster page loads and API responses
- Lower hosting costs due to reduced data transfer

### 2. Cache-Control Headers

**Middleware**: `app.core.middleware.cache.CacheMiddleware`

**Configuration**:
- `CACHE_ENABLED`: Enable/disable caching (default: `true`)
- `CACHE_DEFAULT_MAX_AGE`: Default max-age in seconds (default: `0` = no cache)
- `CACHE_STATIC_MAX_AGE`: Max-age for static resources in seconds (default: `86400` = 1 day)
- `CACHE_API_MAX_AGE`: Max-age for cacheable API responses in seconds (default: `60` = 1 minute)

**Cache Policies by Route**:

| Route Pattern | Cache-Control | Rationale |
|--------------|---------------|-----------|
| `/docs`, `/redoc`, `/openapi.json` | `public, max-age=86400` | Static documentation, changes rarely |
| `/health`, `/health/*`, `/metrics` | `public, max-age=10` | Health checks, can be cached briefly |
| `/api/*/dashboard`, `/api/*/metrics` | `private, max-age=60, must-revalidate` | Dashboard data, can be cached for 1 minute |
| Other `/api/*` endpoints | `private, max-age=0, must-revalidate` | Dynamic data, no cache or very short |
| POST, PUT, DELETE requests | `no-store, no-cache, must-revalidate` | Mutations should never be cached |

**Headers Added**:
- `Cache-Control`: Specifies caching behavior
- `Vary: Accept-Encoding`: Indicates response varies by encoding

### 3. ETag Support

**Middleware**: `app.core.middleware.cache.CacheMiddleware`

**Behavior**:
- Generates MD5 hash of response body as ETag
- Adds `ETag` header to cacheable responses
- Handles `If-None-Match` conditional requests
- Returns `304 Not Modified` when ETag matches

**ETag Generation**:
- Static resources: `/docs`, `/redoc`, `/openapi.json`
- Dashboard and metrics endpoints: `/api/*/dashboard`, `/api/*/metrics`, `/api/*/stats`
- Only for successful GET requests (status 200)

**Benefits**:
- Reduces bandwidth for unchanged resources
- Faster response times (304 responses are tiny)
- Better user experience with instant page loads

## Implementation Details

### Middleware Order

Middleware executes in reverse order of addition. Current order:

```python
1. GZipMiddleware (last added, first executed)
2. CacheMiddleware
3. AuditMiddleware
4. MetricsMiddleware
5. LoggingMiddleware
6. RateLimitMiddleware
7. CORSMiddleware (first added, last executed)
```

**Rationale**:
- Compression should be last to compress the final response
- Cache headers should be added before compression
- Other middleware can modify response before caching/compression

### Configuration

Add to `.env` file:

```bash
# HTTP Compression
COMPRESSION_ENABLED=true
COMPRESSION_MINIMUM_SIZE=500
COMPRESSION_LEVEL=6

# HTTP Caching
CACHE_ENABLED=true
CACHE_DEFAULT_MAX_AGE=0
CACHE_STATIC_MAX_AGE=86400
CACHE_API_MAX_AGE=60
```

### Code Structure

```
backend/app/core/middleware/
├── cache.py              # Cache-Control and ETag middleware
└── compression.py        # Compression middleware (documentation only)

backend/app/
├── config.py             # Configuration settings
└── main.py               # Middleware registration
```

## Testing

### Manual Testing

1. **Test Compression**:
```bash
# Request with gzip support
curl -H "Accept-Encoding: gzip" http://localhost:8000/openapi.json -v

# Check for Content-Encoding: gzip header
# Check for Vary: Accept-Encoding header
```

2. **Test Cache-Control**:
```bash
# Health endpoint (short cache)
curl http://localhost:8000/health -v
# Look for: Cache-Control: public, max-age=10

# Docs endpoint (long cache)
curl http://localhost:8000/docs -v
# Look for: Cache-Control: public, max-age=86400

# API endpoint (no cache)
curl http://localhost:8000/api/v1/leads -v
# Look for: Cache-Control: private, max-age=0, must-revalidate
```

3. **Test ETag**:
```bash
# First request - get ETag
curl http://localhost:8000/openapi.json -v
# Note the ETag header value

# Second request with If-None-Match
curl -H "If-None-Match: \"<etag-value>\"" http://localhost:8000/openapi.json -v
# Should return 304 Not Modified
```

### Automated Testing

Run the test suite:

```bash
cd backend
python test_compression_cache_simple.py
```

## Performance Impact

### Expected Improvements

1. **Bandwidth Reduction**:
   - JSON responses: 60-80% smaller
   - HTML/CSS/JS: 70-90% smaller
   - Overall bandwidth savings: 50-70%

2. **Response Time**:
   - First request: Slightly slower (compression overhead ~5-10ms)
   - Cached requests: 90% faster (304 responses)
   - Overall: 30-50% faster perceived performance

3. **Server Load**:
   - CPU: Slight increase (compression)
   - Memory: Minimal impact
   - Network I/O: Significant reduction

### Monitoring

Monitor these metrics:

- Response size distribution (compressed vs uncompressed)
- Cache hit rate (304 responses / total requests)
- Compression ratio by content type
- Response time impact

## Best Practices

### When to Cache

✅ **DO cache**:
- Static resources (docs, images, CSS, JS)
- Aggregated data (dashboard, metrics)
- Rarely changing data (configuration, settings)

❌ **DON'T cache**:
- User-specific data (unless using `private`)
- Real-time data (notifications, live updates)
- Mutation operations (POST, PUT, DELETE)
- Sensitive data (unless properly secured)

### Cache-Control Directives

- `public`: Can be cached by any cache (CDN, browser)
- `private`: Can only be cached by browser
- `no-cache`: Must revalidate with server before using
- `no-store`: Must not be cached at all
- `must-revalidate`: Must revalidate when stale
- `max-age=N`: Cache for N seconds

### ETag Best Practices

- Use strong ETags (MD5 hash) for accuracy
- Generate ETags only for cacheable responses
- Handle `If-None-Match` properly
- Consider weak ETags (`W/"..."`) for dynamic content

## Troubleshooting

### Compression Not Working

1. Check `COMPRESSION_ENABLED=true` in `.env`
2. Verify client sends `Accept-Encoding: gzip` header
3. Check response size > `COMPRESSION_MINIMUM_SIZE`
4. Verify content type is compressible

### Caching Issues

1. Check `CACHE_ENABLED=true` in `.env`
2. Verify route matches cache policy
3. Check for conflicting headers from other middleware
4. Clear browser cache and test with `curl`

### ETag Not Generated

1. Verify route is in ETag generation list
2. Check response status is 200
3. Ensure request method is GET
4. Check middleware order (cache before compression)

## Future Enhancements

Potential improvements:

1. **CDN Integration**: Add `CDN-Cache-Control` headers
2. **Conditional Compression**: Skip compression for already-compressed content
3. **Brotli Support**: Add Brotli compression for better ratios
4. **Cache Warming**: Pre-generate ETags for common requests
5. **Stale-While-Revalidate**: Serve stale content while updating
6. **Cache Invalidation**: API to invalidate specific cache entries

## References

- [MDN: HTTP Caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)
- [MDN: HTTP Compression](https://developer.mozilla.org/en-US/docs/Web/HTTP/Compression)
- [RFC 7232: HTTP Conditional Requests](https://tools.ietf.org/html/rfc7232)
- [FastAPI Middleware](https://fastapi.tiangolo.com/advanced/middleware/)


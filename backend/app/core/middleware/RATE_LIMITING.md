# Rate Limiting Middleware

## Overview

The rate limiting middleware implements distributed rate limiting using Redis as a backend for counters. It protects the API from abuse by limiting the number of requests per client per time window.

## Features

- **Distributed Rate Limiting**: Uses Redis for shared counters across multiple instances
- **Sliding Window**: Implements per-minute sliding window rate limiting
- **Different Limits per Endpoint Type**:
  - General endpoints: 100 requests/minute
  - AI endpoints: 10 requests/minute
- **Client Identification**: Identifies clients by user ID, tenant ID, or IP address
- **Standard Headers**: Returns standard rate limit headers (X-RateLimit-*)
- **429 Response**: Returns HTTP 429 with Retry-After header when limit exceeded
- **Fail Open**: If Redis is unavailable, allows requests through (graceful degradation)

## Configuration

Rate limiting is configured via environment variables in `.env`:

```bash
# Enable/disable rate limiting
RATE_LIMIT_ENABLED=true

# General endpoints limit (requests per minute)
RATE_LIMIT_PER_MINUTE=100

# AI endpoints limit (requests per minute)
RATE_LIMIT_AI_PER_MINUTE=10

# Redis connection
REDIS_URL=redis://localhost:6379/0
```

## How It Works

### 1. Client Identification

The middleware identifies clients using the following priority:

1. **User ID** from JWT token (if authenticated)
2. **Tenant ID** from JWT token (if authenticated)
3. **IP Address** from request client

This ensures that:
- Authenticated users have per-user limits
- Multi-tenant isolation is maintained
- Anonymous requests are limited by IP

### 2. Rate Limit Calculation

The middleware uses a sliding window approach:

```python
current_time = int(time.time())
current_window = current_time // 60  # Minute-based window
key = f"jusmonitoria:ratelimit:{client_id}:{window}"

count = await redis.incr(key)
if count == 1:
    await redis.expire(key, 120)  # 2 minutes TTL

if count > limit:
    # Rate limit exceeded
    retry_after = 60 - (current_time % 60)
    return 429
```

### 3. Response Headers

All responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067260
```

When rate limited (429 response):

```
Retry-After: 45
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704067260
```

## Endpoint Classification

### AI Endpoints (10 req/min)

The following endpoints have stricter rate limits:

- `/api/v1/ai/*`
- `/api/v1/briefing/*`
- `/api/v1/translate/*`
- `/api/v1/leads/qualify`
- `/api/v1/clients/analyze`

### Excluded Endpoints (No Rate Limiting)

The following endpoints are excluded from rate limiting:

- `/health`
- `/health/live`
- `/health/ready`
- `/metrics`
- `/docs`
- `/redoc`
- `/openapi.json`

## Usage Examples

### Normal Request

```bash
curl -i http://localhost:8000/api/v1/leads

HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1704067260
...
```

### Rate Limited Request

```bash
curl -i http://localhost:8000/api/v1/leads

HTTP/1.1 429 Too Many Requests
Retry-After: 45
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704067260

{
  "detail": "Rate limit exceeded. Please try again later.",
  "limit": 100,
  "current": 101,
  "retry_after": 45
}
```

## Testing

### Manual Test

Run the manual test script to verify Redis connection and rate limiting logic:

```bash
python test_rate_limit_manual.py
```

### Integration Test

Start the FastAPI server and run the integration test:

```bash
# Terminal 1: Start server
uvicorn app.main:app --reload

# Terminal 2: Run test
python test_rate_limit_integration.py
```

### Unit Tests

Run the pytest suite:

```bash
pytest tests/integration/test_rate_limiting.py -v
```

## Monitoring

### Redis Keys

Rate limit counters are stored in Redis with the following key pattern:

```
jusmonitoria:ratelimit:{client_id}:{window}
```

Example:
```
jusmonitoria:ratelimit:user:123e4567-e89b-12d3-a456-426614174000:28401120
```

Keys automatically expire after 2 minutes.

### Metrics

The middleware logs rate limit events:

```python
logger.warning(
    "rate_limit_exceeded",
    client_id=client_id,
    count=count,
    limit=limit,
    retry_after=retry_after,
)
```

Monitor these logs to identify:
- Clients hitting rate limits frequently
- Potential abuse patterns
- Need to adjust limits

## Troubleshooting

### Redis Connection Issues

If Redis is unavailable, the middleware will:
1. Log a warning: `rate_limit_redis_unavailable`
2. Allow the request through (fail open)
3. Continue attempting to reconnect

### Rate Limits Too Strict

If legitimate users are hitting rate limits:

1. Check the logs for the client identifier
2. Consider increasing limits in `.env`:
   ```bash
   RATE_LIMIT_PER_MINUTE=200
   ```
3. Or add specific endpoints to the excluded list

### Rate Limits Too Lenient

If you're experiencing abuse:

1. Decrease limits in `.env`
2. Add more endpoints to the AI endpoints list (stricter limits)
3. Implement IP-based blocking for repeat offenders

## Architecture Decisions

### Why Redis?

- **Distributed**: Works across multiple API instances
- **Fast**: In-memory operations with minimal latency
- **Atomic**: INCR operation is atomic, preventing race conditions
- **TTL**: Automatic key expiration simplifies cleanup

### Why Sliding Window?

- **Fair**: Prevents burst traffic at window boundaries
- **Simple**: Easy to implement and understand
- **Efficient**: Minimal Redis operations per request

### Why Fail Open?

- **Availability**: System remains operational if Redis fails
- **User Experience**: Better to allow some abuse than block all users
- **Monitoring**: Redis failures are logged for investigation

## Future Enhancements

Potential improvements:

1. **Token Bucket Algorithm**: More sophisticated rate limiting
2. **Per-Tenant Limits**: Different limits per tenant plan
3. **Burst Allowance**: Allow short bursts above the limit
4. **Rate Limit Bypass**: Special header for internal services
5. **Dynamic Limits**: Adjust limits based on system load
6. **Whitelist/Blacklist**: IP-based allow/deny lists

## References

- [RFC 6585 - Additional HTTP Status Codes](https://tools.ietf.org/html/rfc6585)
- [IETF Draft - RateLimit Header Fields](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-ratelimit-headers)
- [Redis INCR Command](https://redis.io/commands/incr)

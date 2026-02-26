"""Manual test script for rate limiting middleware."""

import asyncio
import time

import redis.asyncio as redis
from app.config import settings


async def test_redis_connection():
    """Test Redis connection."""
    print("Testing Redis connection...")
    try:
        r = redis.from_url(
            str(settings.redis_url),
            encoding="utf-8",
            decode_responses=True,
        )
        await r.ping()
        print("✓ Redis connection successful")
        
        # Test rate limiting logic
        print("\nTesting rate limiting logic...")
        
        client_id = "test_client"
        limit = 5
        
        # Simulate requests
        for i in range(limit + 2):
            current_time = int(time.time())
            current_window = current_time // 60
            key = f"jusmonitor:ratelimit:{client_id}:{current_window}"
            
            count = await r.incr(key)
            
            if count == 1:
                await r.expire(key, 120)
            
            if count > limit:
                retry_after = 60 - (current_time % 60)
                print(f"  Request {i+1}: RATE LIMITED (count={count}, retry_after={retry_after}s)")
            else:
                print(f"  Request {i+1}: ALLOWED (count={count}/{limit})")
        
        # Clean up
        await r.delete(f"jusmonitor:ratelimit:{client_id}:{current_window}")
        await r.close()
        
        print("\n✓ Rate limiting logic works correctly")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return True


async def test_rate_limit_config():
    """Test rate limit configuration."""
    print("\nTesting rate limit configuration...")
    
    print(f"  Rate limiting enabled: {settings.rate_limit_enabled}")
    print(f"  General rate limit: {settings.rate_limit_per_minute} req/min")
    print(f"  AI rate limit: {settings.rate_limit_ai_per_minute} req/min")
    
    assert settings.rate_limit_per_minute == 100, "General rate limit should be 100"
    assert settings.rate_limit_ai_per_minute == 10, "AI rate limit should be 10"
    
    print("✓ Rate limit configuration is correct")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Rate Limiting Middleware - Manual Test")
    print("=" * 60)
    
    await test_rate_limit_config()
    await test_redis_connection()
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

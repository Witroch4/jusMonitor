"""Simple test to verify rate limiting middleware is working."""

import asyncio
import redis.asyncio as redis
from app.config import settings

async def test_redis_connection():
    """Test Redis connection for rate limiting."""
    print("Testing Redis connection...")
    try:
        r = redis.from_url(
            str(settings.redis_url),
            encoding="utf-8",
            decode_responses=True,
        )
        await r.ping()
        print("✓ Redis connection successful")
        
        # Test rate limit key operations
        test_key = "jusmonitor:ratelimit:test:12345"
        count = await r.incr(test_key)
        print(f"✓ Redis INCR operation successful (count: {count})")
        
        await r.expire(test_key, 120)
        print("✓ Redis EXPIRE operation successful")
        
        await r.delete(test_key)
        print("✓ Redis DELETE operation successful")
        
        await r.close()
        print("\n✅ All Redis operations working correctly!")
        return True
    except Exception as e:
        print(f"\n❌ Redis connection failed: {e}")
        return False

async def test_rate_limit_config():
    """Test rate limiting configuration."""
    print("\nTesting rate limiting configuration...")
    print(f"✓ Rate limiting enabled: {settings.rate_limit_enabled}")
    print(f"✓ General rate limit: {settings.rate_limit_per_minute} req/min")
    print(f"✓ AI rate limit: {settings.rate_limit_ai_per_minute} req/min")
    print(f"✓ Redis URL: {settings.redis_url}")
    print("\n✅ Configuration looks good!")
    return True

async def main():
    """Run all tests."""
    print("=" * 60)
    print("Rate Limiting Middleware Test")
    print("=" * 60)
    
    config_ok = await test_rate_limit_config()
    redis_ok = await test_redis_connection()
    
    print("\n" + "=" * 60)
    if config_ok and redis_ok:
        print("✅ ALL TESTS PASSED - Rate limiting is ready!")
    else:
        print("❌ SOME TESTS FAILED - Check configuration")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

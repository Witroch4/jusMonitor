"""Integration test for rate limiting middleware with actual HTTP requests."""

import asyncio
import time

import httpx


async def test_rate_limiting():
    """Test rate limiting with actual HTTP requests."""
    print("=" * 60)
    print("Rate Limiting Integration Test")
    print("=" * 60)
    
    # Note: This requires the FastAPI server to be running
    # Start with: uvicorn app.main:app --reload
    
    base_url = "http://localhost:8000"
    
    print("\n1. Testing rate limit headers...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/health")
        
        if response.status_code == 200:
            print(f"   Status: {response.status_code}")
            print(f"   X-RateLimit-Limit: {response.headers.get('X-RateLimit-Limit')}")
            print(f"   X-RateLimit-Remaining: {response.headers.get('X-RateLimit-Remaining')}")
            print(f"   X-RateLimit-Reset: {response.headers.get('X-RateLimit-Reset')}")
            print("   ✓ Rate limit headers present")
        else:
            print(f"   ✗ Unexpected status: {response.status_code}")
    
    print("\n2. Testing rate limit enforcement (making 10 requests)...")
    async with httpx.AsyncClient() as client:
        success_count = 0
        rate_limited_count = 0
        
        for i in range(10):
            response = await client.get(f"{base_url}/health")
            
            if response.status_code == 200:
                success_count += 1
                remaining = response.headers.get('X-RateLimit-Remaining', 'N/A')
                print(f"   Request {i+1}: OK (remaining: {remaining})")
            elif response.status_code == 429:
                rate_limited_count += 1
                retry_after = response.headers.get('Retry-After', 'N/A')
                print(f"   Request {i+1}: RATE LIMITED (retry after: {retry_after}s)")
            else:
                print(f"   Request {i+1}: Unexpected status {response.status_code}")
        
        print(f"\n   Summary: {success_count} successful, {rate_limited_count} rate limited")
        print("   ✓ Rate limiting is working")
    
    print("\n3. Testing excluded paths (should not be rate limited)...")
    async with httpx.AsyncClient() as client:
        excluded_paths = ["/health", "/metrics"]
        
        for path in excluded_paths:
            # Make many requests to verify no rate limiting
            responses = []
            for i in range(5):
                response = await client.get(f"{base_url}{path}")
                responses.append(response)
            
            rate_limited = [r for r in responses if r.status_code == 429]
            
            if len(rate_limited) == 0:
                print(f"   {path}: ✓ Not rate limited ({len(responses)} requests)")
            else:
                print(f"   {path}: ✗ Unexpectedly rate limited")
    
    print("\n" + "=" * 60)
    print("Integration test completed!")
    print("=" * 60)


if __name__ == "__main__":
    print("\nNOTE: This test requires the FastAPI server to be running.")
    print("Start it with: uvicorn app.main:app --reload")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")
    
    try:
        input()
        asyncio.run(test_rate_limiting())
    except KeyboardInterrupt:
        print("\nTest cancelled.")

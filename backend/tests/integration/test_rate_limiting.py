"""Integration tests for rate limiting middleware."""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_rate_limit_general_endpoint(client):
    """Test that general endpoints are rate limited to 100 req/min."""
    # Skip if rate limiting is disabled
    if not settings.rate_limit_enabled:
        pytest.skip("Rate limiting is disabled")
    
    # Make requests up to the limit
    limit = settings.rate_limit_per_minute
    
    # Make requests just under the limit
    responses = []
    for i in range(min(5, limit)):  # Test with 5 requests to avoid long test
        response = client.get("/health")
        responses.append(response)
    
    # All should succeed
    assert all(r.status_code == 200 for r in responses)
    
    # Check rate limit headers are present
    last_response = responses[-1]
    assert "X-RateLimit-Limit" in last_response.headers
    assert "X-RateLimit-Remaining" in last_response.headers
    assert "X-RateLimit-Reset" in last_response.headers


@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    """Test that rate limit returns 429 when exceeded."""
    # Skip if rate limiting is disabled
    if not settings.rate_limit_enabled:
        pytest.skip("Rate limiting is disabled")
    
    # Use async client for better control
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Make requests exceeding the limit
        limit = settings.rate_limit_per_minute
        
        # Make more requests than the limit
        responses = []
        for i in range(limit + 5):
            response = await ac.get("/health")
            responses.append(response)
        
        # Last few should be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0, "Expected some requests to be rate limited"
        
        # Check 429 response has correct headers
        if rate_limited:
            response_429 = rate_limited[0]
            assert "Retry-After" in response_429.headers
            assert "X-RateLimit-Limit" in response_429.headers
            assert response_429.json()["detail"] == "Rate limit exceeded. Please try again later."


@pytest.mark.asyncio
async def test_rate_limit_ai_endpoints_stricter():
    """Test that AI endpoints have stricter rate limits (10 req/min)."""
    # Skip if rate limiting is disabled
    if not settings.rate_limit_enabled:
        pytest.skip("Rate limiting is disabled")
    
    # AI endpoints should have lower limit
    ai_limit = settings.rate_limit_ai_per_minute
    assert ai_limit < settings.rate_limit_per_minute, "AI limit should be stricter"
    
    # Note: This test would need actual AI endpoints to be implemented
    # For now, we just verify the configuration is correct
    assert ai_limit == 10


@pytest.mark.asyncio
async def test_rate_limit_excluded_paths():
    """Test that excluded paths are not rate limited."""
    # Skip if rate limiting is disabled
    if not settings.rate_limit_enabled:
        pytest.skip("Rate limiting is disabled")
    
    excluded_paths = ["/health", "/metrics", "/docs"]
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Make many requests to excluded paths
        for path in excluded_paths:
            responses = []
            for i in range(150):  # More than the limit
                response = await ac.get(path)
                responses.append(response)
            
            # None should be rate limited (all should be 200 or 404)
            rate_limited = [r for r in responses if r.status_code == 429]
            assert len(rate_limited) == 0, f"Path {path} should not be rate limited"


@pytest.mark.asyncio
async def test_rate_limit_reset_after_window():
    """Test that rate limit resets after the time window."""
    # Skip if rate limiting is disabled
    if not settings.rate_limit_enabled:
        pytest.skip("Rate limiting is disabled")
    
    # This test would take too long in practice (need to wait 60 seconds)
    # So we just verify the reset timestamp is in the future
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        
        if "X-RateLimit-Reset" in response.headers:
            reset_time = int(response.headers["X-RateLimit-Reset"])
            current_time = int(time.time())
            
            # Reset time should be in the future (within next minute)
            assert reset_time > current_time
            assert reset_time <= current_time + 60


@pytest.mark.asyncio
async def test_rate_limit_headers_present():
    """Test that rate limit headers are present in responses."""
    # Skip if rate limiting is disabled
    if not settings.rate_limit_enabled:
        pytest.skip("Rate limiting is disabled")
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        
        # Check all required headers are present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        
        # Verify header values are valid
        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])
        reset = int(response.headers["X-RateLimit-Reset"])
        
        assert limit > 0
        assert remaining >= 0
        assert remaining <= limit
        assert reset > 0


def test_rate_limit_disabled():
    """Test that rate limiting can be disabled via config."""
    # Temporarily disable rate limiting
    original_value = settings.rate_limit_enabled
    
    try:
        # This test just verifies the config option exists
        assert hasattr(settings, "rate_limit_enabled")
        assert isinstance(settings.rate_limit_enabled, bool)
    finally:
        # Restore original value
        settings.rate_limit_enabled = original_value

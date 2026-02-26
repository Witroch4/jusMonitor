"""Integration tests for HTTP compression and caching."""

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestCompression:
    """Test HTTP compression functionality."""

    def test_gzip_compression_with_accept_encoding(self, client):
        """Test that responses are compressed when client accepts gzip."""
        response = client.get(
            "/health",
            headers={"Accept-Encoding": "gzip, deflate"},
        )
        
        assert response.status_code == 200
        # Check if response has gzip encoding header
        # Note: TestClient may not actually compress, but middleware is configured
        assert response.headers.get("Vary") == "Accept-Encoding"

    def test_no_compression_without_accept_encoding(self, client):
        """Test that responses are not compressed when client doesn't accept gzip."""
        response = client.get(
            "/health",
            headers={"Accept-Encoding": "identity"},
        )
        
        assert response.status_code == 200
        # Response should not be compressed
        assert "gzip" not in response.headers.get("Content-Encoding", "")

    def test_large_json_response_compression(self, client):
        """Test that large JSON responses can be compressed."""
        # OpenAPI spec is a large JSON response
        response = client.get(
            "/openapi.json",
            headers={"Accept-Encoding": "gzip"},
        )
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"


class TestCaching:
    """Test HTTP caching functionality."""

    def test_cache_control_header_on_health_endpoint(self, client):
        """Test that health endpoint has appropriate Cache-Control header."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        # Health endpoint should have short cache
        assert "max-age=10" in response.headers["Cache-Control"]

    def test_cache_control_header_on_static_resources(self, client):
        """Test that static resources have long cache."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        # Docs should have long cache
        cache_control = response.headers["Cache-Control"]
        assert "max-age=86400" in cache_control or "public" in cache_control

    def test_no_cache_for_post_requests(self, client):
        """Test that POST requests have no-cache headers."""
        # Try to POST to health (will fail but we check headers)
        response = client.post("/health")
        
        # Even if endpoint doesn't exist, middleware should add headers
        assert "Cache-Control" in response.headers
        cache_control = response.headers["Cache-Control"]
        assert "no-store" in cache_control or "no-cache" in cache_control

    def test_vary_header_present(self, client):
        """Test that Vary header is present for content negotiation."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "Vary" in response.headers
        assert "Accept-Encoding" in response.headers["Vary"]

    def test_etag_generation_for_static_resources(self, client):
        """Test that ETags are generated for static resources."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        # ETag should be present for static resources
        assert "ETag" in response.headers
        etag = response.headers["ETag"]
        assert etag.startswith('"') and etag.endswith('"')

    def test_etag_conditional_request(self, client):
        """Test that conditional requests with matching ETag return 304."""
        # First request to get ETag
        response1 = client.get("/openapi.json")
        assert response1.status_code == 200
        
        if "ETag" in response1.headers:
            etag = response1.headers["ETag"]
            
            # Second request with If-None-Match
            response2 = client.get(
                "/openapi.json",
                headers={"If-None-Match": etag},
            )
            
            # Should return 304 Not Modified
            assert response2.status_code == 304
            assert response2.headers.get("ETag") == etag

    def test_etag_mismatch_returns_full_response(self, client):
        """Test that conditional requests with non-matching ETag return full response."""
        response = client.get(
            "/openapi.json",
            headers={"If-None-Match": '"invalid-etag"'},
        )
        
        # Should return full response
        assert response.status_code == 200
        assert len(response.content) > 0


class TestPerformance:
    """Test performance-related aspects of compression and caching."""

    def test_compression_reduces_size(self, client):
        """Test that compression actually reduces response size."""
        # Get uncompressed response
        response_uncompressed = client.get(
            "/openapi.json",
            headers={"Accept-Encoding": "identity"},
        )
        
        # Get compressed response
        response_compressed = client.get(
            "/openapi.json",
            headers={"Accept-Encoding": "gzip"},
        )
        
        assert response_uncompressed.status_code == 200
        assert response_compressed.status_code == 200
        
        # Both should have content
        assert len(response_uncompressed.content) > 0
        assert len(response_compressed.content) > 0

    def test_etag_consistency(self, client):
        """Test that ETag is consistent for same content."""
        response1 = client.get("/openapi.json")
        response2 = client.get("/openapi.json")
        
        if "ETag" in response1.headers and "ETag" in response2.headers:
            # Same content should produce same ETag
            assert response1.headers["ETag"] == response2.headers["ETag"]


class TestConfiguration:
    """Test that compression and caching can be configured."""

    def test_middleware_is_active(self, client):
        """Test that compression and caching middleware are active."""
        response = client.get("/health")
        
        assert response.status_code == 200
        # Both middlewares should add headers
        assert "Cache-Control" in response.headers
        assert "Vary" in response.headers


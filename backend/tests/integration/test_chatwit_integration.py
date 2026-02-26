"""
Integration tests for Chatwit client.

Tests:
- Rate limiting (100 req/min)
- send_message functionality
- add_tag functionality
- Error handling
- Retry logic
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from app.core.services.chatwit_client import (
    ChatwitAPIError,
    ChatwitClient,
    ChatwitRateLimiter,
    ChatwitRateLimitError,
)


class TestChatwitRateLimiter:
    """Test rate limiter functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_within_limit(self):
        """Test that rate limiter allows requests within the limit."""
        limiter = ChatwitRateLimiter(max_requests=5, window_seconds=1)

        # Should allow 5 requests immediately
        for _ in range(5):
            await limiter.acquire()

        # Check remaining quota
        assert limiter.get_remaining_quota() == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_when_limit_exceeded(self):
        """Test that rate limiter blocks when limit is exceeded."""
        limiter = ChatwitRateLimiter(max_requests=2, window_seconds=1)

        # First 2 requests should be immediate
        start = datetime.utcnow()
        await limiter.acquire()
        await limiter.acquire()
        first_two_duration = (datetime.utcnow() - start).total_seconds()

        # Should be very fast (< 0.1s)
        assert first_two_duration < 0.1

        # Third request should block until window resets
        start = datetime.utcnow()
        await limiter.acquire()
        third_duration = (datetime.utcnow() - start).total_seconds()

        # Should wait approximately 1 second
        assert 0.9 <= third_duration <= 1.5

    @pytest.mark.asyncio
    async def test_rate_limiter_window_sliding(self):
        """Test that rate limiter uses sliding window."""
        limiter = ChatwitRateLimiter(max_requests=3, window_seconds=2)

        # Make 3 requests
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

        # Wait 1 second (half the window)
        await asyncio.sleep(1)

        # Should still be at limit
        assert limiter.get_remaining_quota() == 0

        # Wait another 1.1 seconds (total 2.1s, past first request)
        await asyncio.sleep(1.1)

        # Should have 1 slot available now
        assert limiter.get_remaining_quota() >= 1


class TestChatwitClient:
    """Test Chatwit client functionality."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Create a mock httpx client."""
        with patch("app.core.services.chatwit_client.httpx.AsyncClient") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield client_instance

    @pytest.fixture
    def chatwit_client(self, mock_httpx_client):
        """Create a Chatwit client with mocked HTTP."""
        return ChatwitClient(
            api_url="https://api.chatwit.test",
            api_key="test_key",
            rate_limit_per_minute=100,
            timeout_seconds=30.0,
        )

    @pytest.mark.asyncio
    async def test_send_message_success(self, chatwit_client, mock_httpx_client):
        """Test successful message sending."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message_id": "msg_123",
            "status": "sent",
        }
        mock_httpx_client.request.return_value = mock_response

        # Send message
        result = await chatwit_client.send_message(
            contact_id="contact_123",
            message="Hello, world!",
            channel="whatsapp",
        )

        # Verify result
        assert result["message_id"] == "msg_123"
        assert result["status"] == "sent"

        # Verify request was made correctly
        mock_httpx_client.request.assert_called_once()
        call_args = mock_httpx_client.request.call_args
        assert call_args[0][0] == "POST"
        assert "/messages" in call_args[0][1]
        assert call_args[1]["json"]["contact_id"] == "contact_123"
        assert call_args[1]["json"]["content"] == "Hello, world!"

    @pytest.mark.asyncio
    async def test_add_tag_success(self, chatwit_client, mock_httpx_client):
        """Test successful tag addition."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_httpx_client.request.return_value = mock_response

        # Add tag
        result = await chatwit_client.add_tag(
            contact_id="contact_123",
            tag="novo_lead",
        )

        # Verify result
        assert result["status"] == "success"

        # Verify request
        mock_httpx_client.request.assert_called_once()
        call_args = mock_httpx_client.request.call_args
        assert call_args[0][0] == "POST"
        assert "contact_123/tags" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, chatwit_client, mock_httpx_client):
        """Test handling of 429 rate limit errors."""
        # Mock 429 response
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limit exceeded",
            request=AsyncMock(),
            response=mock_response,
        )
        mock_httpx_client.request.return_value = mock_response

        # Should raise ChatwitRateLimitError
        with pytest.raises(ChatwitRateLimitError):
            await chatwit_client.send_message(
                contact_id="contact_123",
                message="Test",
            )

    @pytest.mark.asyncio
    async def test_api_error_handling(self, chatwit_client, mock_httpx_client):
        """Test handling of API errors."""
        # Mock 500 response
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal server error",
            request=AsyncMock(),
            response=mock_response,
        )
        mock_httpx_client.request.return_value = mock_response

        # Should raise ChatwitAPIError after retries
        with pytest.raises(ChatwitAPIError):
            await chatwit_client.send_message(
                contact_id="contact_123",
                message="Test",
            )

    @pytest.mark.asyncio
    async def test_timeout_handling(self, chatwit_client, mock_httpx_client):
        """Test handling of timeouts."""
        # Mock timeout
        mock_httpx_client.request.side_effect = httpx.TimeoutException("Timeout")

        # Should raise TimeoutException after retries
        with pytest.raises(httpx.TimeoutException):
            await chatwit_client.send_message(
                contact_id="contact_123",
                message="Test",
            )

    @pytest.mark.asyncio
    async def test_rate_limiting_between_requests(self, chatwit_client, mock_httpx_client):
        """Test that rate limiting is applied between requests."""
        # Mock successful responses
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_httpx_client.request.return_value = mock_response

        # Set a very low rate limit for testing
        chatwit_client.rate_limiter = ChatwitRateLimiter(max_requests=2, window_seconds=1)

        # Make 2 requests (should be fast)
        start = datetime.utcnow()
        await chatwit_client.send_message("contact_1", "Message 1")
        await chatwit_client.send_message("contact_2", "Message 2")
        duration = (datetime.utcnow() - start).total_seconds()

        # Should be very fast
        assert duration < 0.2

        # Third request should be rate limited
        start = datetime.utcnow()
        await chatwit_client.send_message("contact_3", "Message 3")
        duration = (datetime.utcnow() - start).total_seconds()

        # Should wait approximately 1 second
        assert 0.8 <= duration <= 1.5

    @pytest.mark.asyncio
    async def test_get_active_tags(self, chatwit_client, mock_httpx_client):
        """Test getting active tags."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tags": ["novo_lead", "qualificado", "urgente"]
        }
        mock_httpx_client.request.return_value = mock_response

        # Get tags
        tags = await chatwit_client.get_active_tags()

        # Verify result
        assert len(tags) == 3
        assert "novo_lead" in tags
        assert "qualificado" in tags
        assert "urgente" in tags

    @pytest.mark.asyncio
    async def test_remove_tag(self, chatwit_client, mock_httpx_client):
        """Test tag removal."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_httpx_client.request.return_value = mock_response

        # Remove tag
        result = await chatwit_client.remove_tag(
            contact_id="contact_123",
            tag="old_tag",
        )

        # Verify result
        assert result["status"] == "success"

        # Verify DELETE request was made
        call_args = mock_httpx_client.request.call_args
        assert call_args[0][0] == "DELETE"
        assert "contact_123/tags/old_tag" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_httpx_client):
        """Test client as async context manager."""
        async with ChatwitClient(
            api_url="https://api.chatwit.test",
            api_key="test_key",
        ) as client:
            assert client is not None

        # Verify client was closed
        mock_httpx_client.aclose.assert_called_once()

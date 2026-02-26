"""Chatwit API client with rate limiting and retry logic."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = structlog.get_logger(__name__)


class ChatwitRateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    
    pass


class ChatwitAPIError(Exception):
    """Raised when Chatwit API returns an error."""
    
    pass


class ChatwitRateLimiter:
    """
    Rate limiter for Chatwit API.
    
    Implements token bucket algorithm to limit requests to 100/minute.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: list[datetime] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """
        Acquire permission to make a request.
        
        Blocks if rate limit would be exceeded.
        
        Raises:
            ChatwitRateLimitError: If rate limit is exceeded
        """
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(seconds=self.window_seconds)
            
            # Remove old requests outside the window
            self.requests = [req for req in self.requests if req > cutoff]
            
            # Check if we can make a request
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest_request = self.requests[0]
                wait_seconds = (oldest_request - cutoff).total_seconds()
                
                logger.warning(
                    "chatwit_rate_limit_reached",
                    requests_in_window=len(self.requests),
                    wait_seconds=wait_seconds,
                )
                
                # Wait until we can make a request
                await asyncio.sleep(wait_seconds + 0.1)
                
                # Retry acquire
                return await self.acquire()
            
            # Record this request
            self.requests.append(now)
    
    def get_remaining_quota(self) -> int:
        """
        Get remaining requests in current window.
        
        Returns:
            Number of remaining requests
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Count requests in current window
        recent_requests = [req for req in self.requests if req > cutoff]
        
        return max(0, self.max_requests - len(recent_requests))


class ChatwitClient:
    """
    Chatwit API client with rate limiting and retry logic.
    
    Features:
    - Rate limiting: 100 requests/minute
    - Exponential backoff retry
    - 30s timeout
    - Structured logging
    """
    
    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        rate_limit_per_minute: int | None = None,
        timeout_seconds: float = 30.0,
    ):
        """
        Initialize Chatwit client.
        
        Args:
            api_url: Chatwit API base URL (defaults to settings)
            api_key: Chatwit API key (defaults to settings)
            rate_limit_per_minute: Rate limit (defaults to settings)
            timeout_seconds: Request timeout in seconds
        """
        self.api_url = api_url or settings.chatwit_api_url
        self.api_key = api_key or settings.chatwit_api_key
        self.timeout = timeout_seconds
        
        # Initialize rate limiter
        rate_limit = rate_limit_per_minute or settings.chatwit_rate_limit_per_minute
        self.rate_limiter = ChatwitRateLimiter(max_requests=rate_limit, window_seconds=60)
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        
        logger.info(
            "chatwit_client_initialized",
            api_url=self.api_url,
            rate_limit=rate_limit,
            timeout=timeout_seconds,
        )
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make HTTP request with rate limiting and retry.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response JSON
            
        Raises:
            ChatwitRateLimitError: If rate limit is exceeded
            ChatwitAPIError: If API returns an error
            httpx.HTTPError: If request fails
        """
        # Acquire rate limit permission
        await self.rate_limiter.acquire()
        
        # Make request
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            
            logger.info(
                "chatwit_request_success",
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                remaining_quota=self.rate_limiter.get_remaining_quota(),
            )
            
            return response.json()
        
        except httpx.HTTPStatusError as e:
            logger.error(
                "chatwit_request_failed",
                method=method,
                endpoint=endpoint,
                status_code=e.response.status_code,
                error=str(e),
            )
            
            if e.response.status_code == 429:
                raise ChatwitRateLimitError("Chatwit API rate limit exceeded") from e
            
            raise ChatwitAPIError(f"Chatwit API error: {e}") from e
        
        except httpx.TimeoutException as e:
            logger.error(
                "chatwit_request_timeout",
                method=method,
                endpoint=endpoint,
                timeout=self.timeout,
            )
            raise
    
    async def send_message(
        self,
        contact_id: str,
        message: str,
        channel: str = "whatsapp",
    ) -> dict[str, Any]:
        """
        Send message to contact via Chatwit.
        
        Args:
            contact_id: Chatwit contact ID
            message: Message content
            channel: Channel to send message (default: whatsapp)
            
        Returns:
            Response with message_id and status
            
        Raises:
            ChatwitAPIError: If API returns an error
        """
        payload = {
            "contact_id": contact_id,
            "channel": channel,
            "content": message,
        }
        
        logger.info(
            "chatwit_sending_message",
            contact_id=contact_id,
            channel=channel,
            message_length=len(message),
        )
        
        response = await self._request("POST", "/messages", json=payload)
        
        logger.info(
            "chatwit_message_sent",
            contact_id=contact_id,
            message_id=response.get("message_id"),
        )
        
        return response
    
    async def add_tag(
        self,
        contact_id: str,
        tag: str,
    ) -> dict[str, Any]:
        """
        Add tag to contact.
        
        Args:
            contact_id: Chatwit contact ID
            tag: Tag name to add
            
        Returns:
            Response with status
            
        Raises:
            ChatwitAPIError: If API returns an error
        """
        payload = {"tag": tag}
        
        logger.info(
            "chatwit_adding_tag",
            contact_id=contact_id,
            tag=tag,
        )
        
        response = await self._request(
            "POST",
            f"/contacts/{contact_id}/tags",
            json=payload,
        )
        
        logger.info(
            "chatwit_tag_added",
            contact_id=contact_id,
            tag=tag,
        )
        
        return response
    
    async def remove_tag(
        self,
        contact_id: str,
        tag: str,
    ) -> dict[str, Any]:
        """
        Remove tag from contact.
        
        Args:
            contact_id: Chatwit contact ID
            tag: Tag name to remove
            
        Returns:
            Response with status
            
        Raises:
            ChatwitAPIError: If API returns an error
        """
        logger.info(
            "chatwit_removing_tag",
            contact_id=contact_id,
            tag=tag,
        )
        
        response = await self._request(
            "DELETE",
            f"/contacts/{contact_id}/tags/{tag}",
        )
        
        logger.info(
            "chatwit_tag_removed",
            contact_id=contact_id,
            tag=tag,
        )
        
        return response
    
    async def get_contact(
        self,
        contact_id: str,
    ) -> dict[str, Any]:
        """
        Get contact information.
        
        Args:
            contact_id: Chatwit contact ID
            
        Returns:
            Contact information
            
        Raises:
            ChatwitAPIError: If API returns an error
        """
        logger.info(
            "chatwit_getting_contact",
            contact_id=contact_id,
        )
        
        response = await self._request("GET", f"/contacts/{contact_id}")
        
        return response
    
    async def get_active_tags(self) -> list[str]:
        """
        Get list of active tags from Chatwit.
        
        Returns:
            List of tag names
            
        Raises:
            ChatwitAPIError: If API returns an error
        """
        logger.info("chatwit_getting_active_tags")
        
        response = await self._request("GET", "/tags")
        
        tags = response.get("tags", [])
        
        logger.info(
            "chatwit_active_tags_retrieved",
            tag_count=len(tags),
        )
        
        return tags


# Global client instance (lazy initialized)
_client: ChatwitClient | None = None


def get_chatwit_client() -> ChatwitClient:
    """
    Get global Chatwit client instance.
    
    Returns:
        ChatwitClient instance
    """
    global _client
    
    if _client is None:
        _client = ChatwitClient()
    
    return _client

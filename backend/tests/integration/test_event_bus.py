"""
Integration tests for Event Bus.

Tests:
- Event publishing and subscription
- At-least-once delivery
- Retry with backoff
- Dead letter queue after max retries
- Event handler execution
- Multiple handlers for same event

Requirements: 3.3, 3.4, 5.2
"""

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.workers.events.bus import (
    DLQ_MAX_RETRIES,
    EventBusError,
    _event_handlers,
    _move_to_dlq,
    _process_event,
    get_dlq_events,
    publish,
    retry_dlq_event,
    subscribe,
)
from app.workers.events.types import (
    BaseEvent,
    EventType,
    LeadCreatedEvent,
    MovementDetectedEvent,
)


class TestEventPublishing:
    """Test event publishing functionality."""

    @pytest.fixture(autouse=True)
    def clear_handlers(self):
        """Clear event handlers before each test."""
        _event_handlers.clear()
        yield
        _event_handlers.clear()

    @pytest.mark.asyncio
    async def test_publish_event_success(self):
        """Test successful event publishing."""
        tenant_id = uuid4()
        event = BaseEvent(
            event_id=uuid4(),
            event_type=EventType.LEAD_CREATED,
            tenant_id=tenant_id,
            timestamp=datetime.utcnow(),
        )

        # Mock the task enqueue
        with patch("app.workers.events.bus._process_event.kiq") as mock_kiq:
            mock_kiq.return_value = AsyncMock()

            await publish(event)

            # Verify task was enqueued
            mock_kiq.assert_called_once()
            call_args = mock_kiq.call_args[1]

            assert call_args["event_type"] == EventType.LEAD_CREATED.value
            assert call_args["retry_count"] == 0

    @pytest.mark.asyncio
    async def test_publish_event_serialization(self):
        """Test that events are properly serialized."""
        tenant_id = uuid4()
        event_id = uuid4()

        event = LeadCreatedEvent(
            event_id=event_id,
            tenant_id=tenant_id,
            timestamp=datetime.utcnow(),
            lead_id=uuid4(),
            source="chatwit",
            stage="new",
        )

        with patch("app.workers.events.bus._process_event.kiq") as mock_kiq:
            mock_kiq.return_value = AsyncMock()

            await publish(event)

            # Verify serialization
            call_args = mock_kiq.call_args[1]
            event_data = call_args["event_data"]

            # UUIDs should be serialized as strings
            assert isinstance(event_data["event_id"], str)
            assert isinstance(event_data["tenant_id"], str)
            assert isinstance(event_data["lead_id"], str)

            # Datetime should be serialized as ISO string
            assert isinstance(event_data["timestamp"], str)


class TestEventSubscription:
    """Test event subscription and handler registration."""

    @pytest.fixture(autouse=True)
    def clear_handlers(self):
        """Clear event handlers before each test."""
        _event_handlers.clear()
        yield
        _event_handlers.clear()

    def test_subscribe_decorator_registers_handler(self):
        """Test that subscribe decorator registers handlers."""

        @subscribe(EventType.LEAD_CREATED)
        async def handle_lead_created(event_data: dict):
            pass

        assert EventType.LEAD_CREATED in _event_handlers
        assert handle_lead_created in _event_handlers[EventType.LEAD_CREATED]

    def test_multiple_handlers_for_same_event(self):
        """Test registering multiple handlers for same event."""

        @subscribe(EventType.LEAD_CREATED)
        async def handler1(event_data: dict):
            pass

        @subscribe(EventType.LEAD_CREATED)
        async def handler2(event_data: dict):
            pass

        handlers = _event_handlers[EventType.LEAD_CREATED]
        assert len(handlers) == 2
        assert handler1 in handlers
        assert handler2 in handlers

    def test_handlers_for_different_events(self):
        """Test registering handlers for different events."""

        @subscribe(EventType.LEAD_CREATED)
        async def handle_lead(event_data: dict):
            pass

        @subscribe(EventType.MOVEMENT_DETECTED)
        async def handle_movement(event_data: dict):
            pass

        assert EventType.LEAD_CREATED in _event_handlers
        assert EventType.MOVEMENT_DETECTED in _event_handlers
        assert len(_event_handlers) == 2


class TestEventProcessing:
    """Test event processing and handler execution."""

    @pytest.fixture(autouse=True)
    def clear_handlers(self):
        """Clear event handlers before each test."""
        _event_handlers.clear()
        yield
        _event_handlers.clear()

    @pytest.mark.asyncio
    async def test_process_event_calls_handlers(self):
        """Test that event processing calls registered handlers."""
        handler_called = []

        @subscribe(EventType.LEAD_CREATED)
        async def handler(event_data: dict):
            handler_called.append(event_data)

        event_data = {
            "event_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "lead_id": str(uuid4()),
            "source": "chatwit",
        }

        await _process_event(
            event_type=EventType.LEAD_CREATED.value,
            event_data=event_data,
            retry_count=0,
        )

        # Verify handler was called
        assert len(handler_called) == 1
        assert handler_called[0] == event_data

    @pytest.mark.asyncio
    async def test_process_event_calls_multiple_handlers(self):
        """Test that all handlers are called for an event."""
        handler1_called = []
        handler2_called = []

        @subscribe(EventType.LEAD_CREATED)
        async def handler1(event_data: dict):
            handler1_called.append(True)

        @subscribe(EventType.LEAD_CREATED)
        async def handler2(event_data: dict):
            handler2_called.append(True)

        event_data = {
            "event_id": str(uuid4()),
            "tenant_id": str(uuid4()),
        }

        await _process_event(
            event_type=EventType.LEAD_CREATED.value,
            event_data=event_data,
            retry_count=0,
        )

        # Both handlers should be called
        assert len(handler1_called) == 1
        assert len(handler2_called) == 1

    @pytest.mark.asyncio
    async def test_process_event_no_handlers_warning(self):
        """Test that processing event with no handlers logs warning."""
        event_data = {
            "event_id": str(uuid4()),
            "tenant_id": str(uuid4()),
        }

        # Should not raise error, just log warning
        await _process_event(
            event_type=EventType.LEAD_CREATED.value,
            event_data=event_data,
            retry_count=0,
        )

    @pytest.mark.asyncio
    async def test_handler_error_triggers_retry(self):
        """Test that handler errors trigger retry."""

        @subscribe(EventType.LEAD_CREATED)
        async def failing_handler(event_data: dict):
            raise ValueError("Handler failed")

        event_data = {
            "event_id": str(uuid4()),
            "tenant_id": str(uuid4()),
        }

        # Should raise error to trigger retry
        with pytest.raises(ValueError, match="Handler failed"):
            await _process_event(
                event_type=EventType.LEAD_CREATED.value,
                event_data=event_data,
                retry_count=0,
            )


class TestDeadLetterQueue:
    """Test dead letter queue functionality."""

    @pytest.fixture(autouse=True)
    def clear_handlers(self):
        """Clear event handlers before each test."""
        _event_handlers.clear()
        yield
        _event_handlers.clear()

    @pytest.mark.asyncio
    async def test_move_to_dlq(self):
        """Test moving failed event to DLQ."""
        event_data = {
            "event_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "lead_id": str(uuid4()),
        }

        with patch("app.workers.events.bus.Redis") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.from_url.return_value = mock_redis

            await _move_to_dlq(
                event_type=EventType.LEAD_CREATED.value,
                event_data=event_data,
                error="Handler failed after 3 retries",
            )

            # Verify Redis zadd was called
            mock_redis.zadd.assert_called_once()
            call_args = mock_redis.zadd.call_args

            # Verify DLQ key format
            dlq_key = call_args[0][0]
            assert dlq_key.startswith("jusmonitor:dlq:")
            assert EventType.LEAD_CREATED.value in dlq_key

    @pytest.mark.asyncio
    async def test_get_dlq_events(self):
        """Test retrieving events from DLQ."""
        import json

        event_data = {
            "event_id": str(uuid4()),
            "tenant_id": str(uuid4()),
        }

        dlq_entry = {
            "event_type": EventType.LEAD_CREATED.value,
            "event_data": event_data,
            "error": "Handler failed",
            "failed_at": datetime.utcnow().isoformat(),
            "retries_exhausted": DLQ_MAX_RETRIES,
        }

        with patch("app.workers.events.bus.Redis") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.from_url.return_value = mock_redis

            # Mock Redis keys and zrevrange
            mock_redis.keys.return_value = [
                f"jusmonitor:dlq:{EventType.LEAD_CREATED.value}"
            ]
            mock_redis.zrevrange.return_value = [json.dumps(dlq_entry).encode()]

            events = await get_dlq_events(event_type=EventType.LEAD_CREATED)

            # Verify
            assert len(events) == 1
            assert events[0]["event_type"] == EventType.LEAD_CREATED.value
            assert events[0]["error"] == "Handler failed"

    @pytest.mark.asyncio
    async def test_retry_dlq_event(self):
        """Test retrying a failed event from DLQ."""
        import json

        event_id = str(uuid4())
        event_data = {
            "event_id": event_id,
            "tenant_id": str(uuid4()),
        }

        dlq_entry = {
            "event_type": EventType.LEAD_CREATED.value,
            "event_data": event_data,
            "error": "Handler failed",
            "failed_at": datetime.utcnow().isoformat(),
        }

        with patch("app.workers.events.bus.Redis") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.from_url.return_value = mock_redis

            # Mock Redis operations
            mock_redis.keys.return_value = [
                f"jusmonitor:dlq:{EventType.LEAD_CREATED.value}"
            ]
            mock_redis.zrange.return_value = [json.dumps(dlq_entry).encode()]

            with patch("app.workers.events.bus._process_event.kiq") as mock_kiq:
                mock_kiq.return_value = AsyncMock()

                result = await retry_dlq_event(event_id)

                # Verify event was retried
                assert result is True
                mock_redis.zrem.assert_called_once()
                mock_kiq.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_dlq_event_not_found(self):
        """Test retrying non-existent event returns False."""
        with patch("app.workers.events.bus.Redis") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.from_url.return_value = mock_redis

            # Mock empty DLQ
            mock_redis.keys.return_value = []

            result = await retry_dlq_event(str(uuid4()))

            assert result is False


class TestAtLeastOnceDelivery:
    """Test at-least-once delivery guarantees."""

    @pytest.fixture(autouse=True)
    def clear_handlers(self):
        """Clear event handlers before each test."""
        _event_handlers.clear()
        yield
        _event_handlers.clear()

    @pytest.mark.asyncio
    async def test_handler_failure_triggers_retry(self):
        """Test that handler failures trigger retry mechanism."""
        call_count = []

        @subscribe(EventType.LEAD_CREATED)
        async def flaky_handler(event_data: dict):
            call_count.append(1)
            if len(call_count) < 2:
                raise ValueError("Temporary failure")
            # Success on second try

        event_data = {
            "event_id": str(uuid4()),
            "tenant_id": str(uuid4()),
        }

        # First call should fail
        with pytest.raises(ValueError):
            await _process_event(
                event_type=EventType.LEAD_CREATED.value,
                event_data=event_data,
                retry_count=0,
            )

        # Second call should succeed
        await _process_event(
            event_type=EventType.LEAD_CREATED.value,
            event_data=event_data,
            retry_count=1,
        )

        # Handler should be called twice
        assert len(call_count) == 2

    @pytest.mark.asyncio
    async def test_max_retries_moves_to_dlq(self):
        """Test that exhausting retries moves event to DLQ."""

        @subscribe(EventType.LEAD_CREATED)
        async def always_failing_handler(event_data: dict):
            raise ValueError("Always fails")

        event_data = {
            "event_id": str(uuid4()),
            "tenant_id": str(uuid4()),
        }

        with patch("app.workers.events.bus._move_to_dlq") as mock_move_to_dlq:
            mock_move_to_dlq.return_value = AsyncMock()

            # Process with max retries exhausted
            with pytest.raises(ValueError):
                await _process_event(
                    event_type=EventType.LEAD_CREATED.value,
                    event_data=event_data,
                    retry_count=DLQ_MAX_RETRIES,
                )

            # Should move to DLQ
            mock_move_to_dlq.assert_called_once()


class TestEventTypes:
    """Test different event types."""

    @pytest.mark.asyncio
    async def test_lead_created_event(self):
        """Test LeadCreatedEvent structure."""
        event = LeadCreatedEvent(
            event_id=uuid4(),
            tenant_id=uuid4(),
            timestamp=datetime.utcnow(),
            lead_id=uuid4(),
            source="chatwit",
            stage="new",
        )

        assert event.event_type == EventType.LEAD_CREATED
        assert event.source == "chatwit"
        assert event.stage == "new"

    @pytest.mark.asyncio
    async def test_movement_detected_event(self):
        """Test MovementDetectedEvent structure."""
        event = MovementDetectedEvent(
            event_id=uuid4(),
            tenant_id=uuid4(),
            timestamp=datetime.utcnow(),
            process_id=uuid4(),
            movement_id=uuid4(),
            is_important=True,
            requires_action=False,
        )

        assert event.event_type == EventType.MOVEMENT_DETECTED
        assert event.is_important is True
        assert event.requires_action is False


class TestEventBusIntegration:
    """Integration tests for complete event flow."""

    @pytest.fixture(autouse=True)
    def clear_handlers(self):
        """Clear event handlers before each test."""
        _event_handlers.clear()
        yield
        _event_handlers.clear()

    @pytest.mark.asyncio
    async def test_complete_event_flow(self):
        """Test complete flow: publish -> process -> handle."""
        handler_results = []

        @subscribe(EventType.LEAD_CREATED)
        async def capture_handler(event_data: dict):
            handler_results.append(event_data)

        tenant_id = uuid4()
        lead_id = uuid4()

        event = LeadCreatedEvent(
            event_id=uuid4(),
            tenant_id=tenant_id,
            timestamp=datetime.utcnow(),
            lead_id=lead_id,
            source="chatwit",
            stage="new",
        )

        # Publish event
        with patch("app.workers.events.bus._process_event.kiq") as mock_kiq:
            # Simulate immediate processing
            async def process_immediately(**kwargs):
                await _process_event(**kwargs)

            mock_kiq.side_effect = process_immediately

            await publish(event)

            # Verify handler was called
            assert len(handler_results) == 1
            assert handler_results[0]["lead_id"] == str(lead_id)
            assert handler_results[0]["source"] == "chatwit"

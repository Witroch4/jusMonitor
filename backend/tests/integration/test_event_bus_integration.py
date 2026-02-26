"""
Integration tests for event bus.

Tests:
- Event publishing
- Event subscription and handling
- At-least-once delivery
- Dead letter queue (DLQ)
- Event serialization
"""

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from app.workers.events.bus import (
    DLQ_MAX_RETRIES,
    get_dlq_events,
    publish,
    retry_dlq_event,
    subscribe,
)
from app.workers.events.types import (
    EventType,
    LeadCreatedEvent,
    MessageReceivedEvent,
    MovementDetectedEvent,
)


class TestEventBus:
    """Test event bus functionality."""

    @pytest.mark.asyncio
    async def test_publish_event(self):
        """Test publishing an event."""
        tenant_id = uuid4()
        lead_id = uuid4()

        event = LeadCreatedEvent(
            tenant_id=tenant_id,
            lead_id=lead_id,
            source="chatwit",
            score=50,
        )

        # Should not raise
        await publish(event)

    @pytest.mark.asyncio
    async def test_event_handler_registration(self):
        """Test registering event handlers."""
        handler_called = []

        @subscribe(EventType.LEAD_CREATED)
        async def test_handler(event_data: dict):
            handler_called.append(event_data)

        # Handler should be registered
        from app.workers.events.bus import _event_handlers

        assert EventType.LEAD_CREATED in _event_handlers
        assert test_handler in _event_handlers[EventType.LEAD_CREATED]

    @pytest.mark.asyncio
    async def test_event_serialization(self):
        """Test that events are properly serialized."""
        tenant_id = uuid4()
        lead_id = uuid4()
        timestamp = datetime.utcnow()

        event = LeadCreatedEvent(
            tenant_id=tenant_id,
            lead_id=lead_id,
            source="chatwit",
            score=75,
            timestamp=timestamp,
        )

        # Serialize to dict
        event_data = event.model_dump(mode="json")

        # Verify serialization
        assert "tenant_id" in event_data
        assert "lead_id" in event_data
        assert event_data["event_type"] == "lead.created"
        assert event_data["source"] == "chatwit"
        assert event_data["score"] == 75

    @pytest.mark.asyncio
    async def test_multiple_handlers_for_same_event(self):
        """Test that multiple handlers can subscribe to the same event."""
        handler1_called = []
        handler2_called = []

        @subscribe(EventType.MESSAGE_RECEIVED)
        async def handler1(event_data: dict):
            handler1_called.append(event_data)

        @subscribe(EventType.MESSAGE_RECEIVED)
        async def handler2(event_data: dict):
            handler2_called.append(event_data)

        # Both handlers should be registered
        from app.workers.events.bus import _event_handlers

        assert len(_event_handlers[EventType.MESSAGE_RECEIVED]) >= 2

    @pytest.mark.asyncio
    async def test_event_with_metadata(self):
        """Test events with custom metadata."""
        tenant_id = uuid4()
        process_id = uuid4()
        movement_id = uuid4()

        event = MovementDetectedEvent(
            tenant_id=tenant_id,
            process_id=process_id,
            movement_id=movement_id,
            is_important=True,
            requires_action=True,
            metadata={
                "court": "TJSP",
                "case_number": "0000001-00.2023.8.00.0000",
                "movement_type": "Sentença",
            },
        )

        # Verify metadata
        assert event.metadata["court"] == "TJSP"
        assert event.metadata["case_number"] == "0000001-00.2023.8.00.0000"

        # Should publish successfully
        await publish(event)

    @pytest.mark.asyncio
    async def test_event_types_enum(self):
        """Test that all event types are properly defined."""
        # Verify key event types exist
        assert EventType.WEBHOOK_RECEIVED == "webhook.received"
        assert EventType.MESSAGE_RECEIVED == "message.received"
        assert EventType.LEAD_CREATED == "lead.created"
        assert EventType.LEAD_QUALIFIED == "lead.qualified"
        assert EventType.LEAD_CONVERTED == "lead.converted"
        assert EventType.CLIENT_CREATED == "client.created"
        assert EventType.PROCESS_CREATED == "process.created"
        assert EventType.MOVEMENT_DETECTED == "movement.detected"
        assert EventType.DEADLINE_APPROACHING == "deadline.approaching"
        assert EventType.BRIEFING_GENERATED == "briefing.generated"

    @pytest.mark.asyncio
    async def test_message_received_event(self):
        """Test MessageReceivedEvent structure."""
        tenant_id = uuid4()

        event = MessageReceivedEvent(
            tenant_id=tenant_id,
            contact_id="contact_123",
            message_id="msg_456",
            content="Olá, preciso de ajuda com um processo",
            channel="whatsapp",
            metadata={
                "contact_name": "João Silva",
                "contact_phone": "+5511999999999",
            },
        )

        # Verify event structure
        assert event.event_type == EventType.MESSAGE_RECEIVED
        assert event.contact_id == "contact_123"
        assert event.message_id == "msg_456"
        assert event.channel == "whatsapp"
        assert "João Silva" in event.metadata["contact_name"]

    @pytest.mark.asyncio
    async def test_dlq_constants(self):
        """Test DLQ configuration constants."""
        # Verify DLQ settings
        assert DLQ_MAX_RETRIES == 3
        from app.workers.events.bus import DLQ_RETRY_DELAY_SECONDS

        assert DLQ_RETRY_DELAY_SECONDS == 60

    @pytest.mark.asyncio
    async def test_get_dlq_events_empty(self):
        """Test getting DLQ events when queue is empty."""
        # Should return empty list
        events = await get_dlq_events()
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_event_id_generation(self):
        """Test that events get unique IDs."""
        tenant_id = uuid4()

        event1 = LeadCreatedEvent(
            tenant_id=tenant_id,
            lead_id=uuid4(),
            source="chatwit",
        )

        event2 = LeadCreatedEvent(
            tenant_id=tenant_id,
            lead_id=uuid4(),
            source="chatwit",
        )

        # Events should have different IDs
        assert event1.event_id != event2.event_id

    @pytest.mark.asyncio
    async def test_event_timestamp_generation(self):
        """Test that events get timestamps."""
        tenant_id = uuid4()

        before = datetime.utcnow()
        event = LeadCreatedEvent(
            tenant_id=tenant_id,
            lead_id=uuid4(),
            source="chatwit",
        )
        after = datetime.utcnow()

        # Timestamp should be between before and after
        assert before <= event.timestamp <= after


class TestEventBusIntegration:
    """Integration tests for event bus with Redis."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_publish_and_process_event(self):
        """Test full event publishing and processing flow."""
        tenant_id = uuid4()
        lead_id = uuid4()

        # Track if handler was called
        handler_results = []

        @subscribe(EventType.LEAD_CREATED)
        async def integration_handler(event_data: dict):
            handler_results.append(event_data)

        # Publish event
        event = LeadCreatedEvent(
            tenant_id=tenant_id,
            lead_id=lead_id,
            source="test_integration",
            score=80,
        )

        await publish(event)

        # Wait a bit for async processing
        await asyncio.sleep(0.5)

        # Note: In a real integration test with Taskiq running,
        # we would verify the handler was called
        # For now, we just verify the event was published successfully

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_event_retry_mechanism(self):
        """Test that failed events are retried."""
        tenant_id = uuid4()

        # Track retry attempts
        attempt_count = []

        @subscribe(EventType.MOVEMENT_DETECTED)
        async def failing_handler(event_data: dict):
            attempt_count.append(1)
            if len(attempt_count) < 3:
                raise Exception("Simulated failure")
            # Succeed on 3rd attempt

        # Publish event
        event = MovementDetectedEvent(
            tenant_id=tenant_id,
            process_id=uuid4(),
            movement_id=uuid4(),
            is_important=True,
        )

        await publish(event)

        # Note: In a real integration test, we would verify retries happened
        # This requires Taskiq to be running

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_dlq_after_max_retries(self):
        """Test that events move to DLQ after max retries."""
        tenant_id = uuid4()

        @subscribe(EventType.CLIENT_CREATED)
        async def always_failing_handler(event_data: dict):
            raise Exception("Always fails")

        # Publish event
        event = LeadCreatedEvent(
            tenant_id=tenant_id,
            lead_id=uuid4(),
            source="test_dlq",
        )

        await publish(event)

        # Note: In a real integration test, we would:
        # 1. Wait for max retries to be exhausted
        # 2. Check DLQ for the failed event
        # 3. Verify error details are stored

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_retry_dlq_event(self):
        """Test retrying an event from DLQ."""
        # This would require:
        # 1. An event in the DLQ
        # 2. Calling retry_dlq_event with the event_id
        # 3. Verifying the event is reprocessed

        # For now, just test the function exists and handles missing events
        result = await retry_dlq_event(str(uuid4()))
        assert result is False  # Event not found

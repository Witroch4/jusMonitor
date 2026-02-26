"""Event system for async task processing."""

from app.workers.events.bus import publish, subscribe
from app.workers.events.types import (
    BaseEvent,
    ClientCreatedEvent,
    ClientUpdatedEvent,
    DeadlineApproachingEvent,
    DeadlineMissedEvent,
    EventType,
    LeadConvertedEvent,
    LeadCreatedEvent,
    LeadQualifiedEvent,
    LeadStageChangedEvent,
    MessageReceivedEvent,
    MovementDetectedEvent,
    ProcessCreatedEvent,
    ProcessUpdatedEvent,
    WebhookReceivedEvent,
)

__all__ = [
    # Event bus functions
    "publish",
    "subscribe",
    # Event types
    "EventType",
    "BaseEvent",
    "WebhookReceivedEvent",
    "MessageReceivedEvent",
    "LeadCreatedEvent",
    "LeadQualifiedEvent",
    "LeadConvertedEvent",
    "LeadStageChangedEvent",
    "ClientCreatedEvent",
    "ClientUpdatedEvent",
    "ProcessCreatedEvent",
    "ProcessUpdatedEvent",
    "MovementDetectedEvent",
    "DeadlineApproachingEvent",
    "DeadlineMissedEvent",
]

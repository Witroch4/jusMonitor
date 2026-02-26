"""Pydantic schemas for Chatwit integration."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatwitContact(BaseModel):
    """Chatwit contact information."""
    
    id: str = Field(..., description="Chatwit contact ID")
    name: str = Field(..., description="Contact name")
    phone: str = Field(..., description="Phone number")
    email: str | None = Field(None, description="Email address")
    tags: list[str] = Field(default_factory=list, description="Contact tags")
    custom_fields: dict[str, Any] = Field(default_factory=dict, description="Custom fields")


class ChatwitMessage(BaseModel):
    """Chatwit message information."""
    
    id: str = Field(..., description="Message ID")
    direction: str = Field(..., description="Message direction: inbound or outbound")
    content: str = Field(..., description="Message content")
    media_url: str | None = Field(None, description="Media URL if present")
    channel: str = Field(..., description="Channel: whatsapp, instagram, etc")


class ChatwitWebhookPayload(BaseModel):
    """Chatwit webhook payload."""
    
    event_type: str = Field(..., description="Event type: message.received, tag.added, tag.removed")
    timestamp: datetime = Field(..., description="Event timestamp")
    contact: ChatwitContact = Field(..., description="Contact information")
    message: ChatwitMessage | None = Field(None, description="Message if applicable")
    tag: str | None = Field(None, description="Tag name for tag events")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ChatwitWebhookResponse(BaseModel):
    """Response for webhook endpoint."""
    
    status: str = Field(default="received", description="Status of webhook processing")
    event_id: str | None = Field(None, description="Generated event ID")


class ChatwitSendMessageRequest(BaseModel):
    """Request to send message via Chatwit."""
    
    contact_id: str = Field(..., description="Chatwit contact ID")
    message: str = Field(..., description="Message content")
    channel: str = Field(default="whatsapp", description="Channel to send message")


class ChatwitSendMessageResponse(BaseModel):
    """Response from sending message."""
    
    message_id: str = Field(..., description="Sent message ID")
    status: str = Field(..., description="Send status")


class ChatwitAddTagRequest(BaseModel):
    """Request to add tag to contact."""
    
    contact_id: str = Field(..., description="Chatwit contact ID")
    tag: str = Field(..., description="Tag name to add")


class ChatwitAddTagResponse(BaseModel):
    """Response from adding tag."""
    
    status: str = Field(..., description="Operation status")

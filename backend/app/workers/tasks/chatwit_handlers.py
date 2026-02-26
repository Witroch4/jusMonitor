"""Chatwit event handlers for webhook processing."""

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import AsyncSessionLocal
from app.db.models.client import Client
from app.db.models.lead import Lead, LeadSource, LeadStage, LeadStatus
from app.db.repositories.client import ClientRepository
from app.db.repositories.lead import LeadRepository
from app.workers.events.bus import subscribe
from app.workers.events.types import (
    EventType,
    MessageReceivedEvent,
    WebhookReceivedEvent,
)

logger = structlog.get_logger(__name__)


async def _get_or_create_tenant_id(chatwit_contact_id: str) -> UUID:
    """
    Resolve tenant_id from Chatwit contact.
    
    For now, this is a placeholder that returns a default tenant.
    In production, you would:
    1. Query a mapping table (chatwit_contact_id -> tenant_id)
    2. Or extract tenant info from contact custom fields
    3. Or use a default tenant for new contacts
    
    Args:
        chatwit_contact_id: Chatwit contact ID
        
    Returns:
        Tenant UUID
    """
    # TODO: Implement proper tenant resolution
    # For now, return a placeholder that should be configured per deployment
    return UUID("00000000-0000-0000-0000-000000000001")


@subscribe(EventType.MESSAGE_RECEIVED)
async def handle_message_received(event_data: dict[str, Any]) -> None:
    """
    Handle message received from Chatwit.
    
    Creates or updates lead based on the contact information.
    
    Args:
        event_data: Message received event data
    """
    try:
        # Extract event data
        contact_id = event_data.get("contact_id")
        message_content = event_data.get("content")
        channel = event_data.get("channel")
        metadata = event_data.get("metadata", {})
        
        contact_name = metadata.get("contact_name")
        contact_phone = metadata.get("contact_phone")
        contact_email = metadata.get("contact_email")
        contact_tags = metadata.get("contact_tags", [])
        
        logger.info(
            "processing_message_received",
            contact_id=contact_id,
            channel=channel,
            has_tags=len(contact_tags) > 0,
        )
        
        # Resolve tenant_id from contact
        tenant_id = await _get_or_create_tenant_id(contact_id)
        
        # Create database session
        async with AsyncSessionLocal() as session:
            lead_repo = LeadRepository(session, tenant_id)
            
            # Check if lead already exists
            existing_lead = await lead_repo.get_by_chatwit_contact(contact_id)
            
            if existing_lead:
                # Update existing lead
                logger.info(
                    "updating_existing_lead",
                    lead_id=str(existing_lead.id),
                    contact_id=contact_id,
                )
                
                # Update last interaction metadata
                if existing_lead.metadata is None:
                    existing_lead.metadata = {}
                
                existing_lead.metadata["last_message"] = message_content
                existing_lead.metadata["last_message_at"] = datetime.utcnow().isoformat()
                existing_lead.metadata["last_channel"] = channel
                
                await session.commit()
                
                logger.info(
                    "lead_updated",
                    lead_id=str(existing_lead.id),
                    contact_id=contact_id,
                )
            else:
                # Create new lead
                logger.info(
                    "creating_new_lead",
                    contact_id=contact_id,
                    contact_name=contact_name,
                )
                
                lead = await lead_repo.create(
                    full_name=contact_name or "Unknown",
                    phone=contact_phone,
                    email=contact_email,
                    source=LeadSource.CHATWIT,
                    chatwit_contact_id=contact_id,
                    stage=LeadStage.NEW,
                    status=LeadStatus.ACTIVE,
                    score=0,
                    metadata={
                        "first_message": message_content,
                        "first_message_at": datetime.utcnow().isoformat(),
                        "channel": channel,
                        "tags": contact_tags,
                    },
                )
                
                await session.commit()
                
                logger.info(
                    "lead_created",
                    lead_id=str(lead.id),
                    contact_id=contact_id,
                    tenant_id=str(tenant_id),
                )
    
    except Exception as e:
        logger.error(
            "message_received_handler_failed",
            error=str(e),
            contact_id=event_data.get("contact_id"),
        )
        raise


@subscribe(EventType.WEBHOOK_RECEIVED)
async def handle_webhook_received(event_data: dict[str, Any]) -> None:
    """
    Handle generic webhook received from Chatwit.
    
    Routes to specific handlers based on event type.
    
    Args:
        event_data: Webhook event data
    """
    try:
        payload = event_data.get("payload", {})
        event_type = payload.get("event_type")
        
        logger.info(
            "processing_webhook",
            event_type=event_type,
            source=event_data.get("source"),
        )
        
        # Route to specific handlers
        if event_type == "tag.added":
            await handle_tag_added(payload)
        elif event_type == "tag.removed":
            await handle_tag_removed(payload)
        else:
            logger.debug(
                "webhook_event_not_handled",
                event_type=event_type,
            )
    
    except Exception as e:
        logger.error(
            "webhook_handler_failed",
            error=str(e),
            event_type=event_data.get("payload", {}).get("event_type"),
        )
        raise


async def handle_tag_added(payload: dict[str, Any]) -> None:
    """
    Handle tag added to contact.
    
    Updates lead status based on tag mapping.
    
    Args:
        payload: Webhook payload with tag information
    """
    try:
        contact = payload.get("contact", {})
        contact_id = contact.get("id")
        tag = payload.get("tag")
        
        logger.info(
            "processing_tag_added",
            contact_id=contact_id,
            tag=tag,
        )
        
        # Resolve tenant_id
        tenant_id = await _get_or_create_tenant_id(contact_id)
        
        # Create database session
        async with AsyncSessionLocal() as session:
            lead_repo = LeadRepository(session, tenant_id)
            
            # Get lead by contact ID
            lead = await lead_repo.get_by_chatwit_contact(contact_id)
            
            if not lead:
                logger.warning(
                    "lead_not_found_for_tag",
                    contact_id=contact_id,
                    tag=tag,
                )
                return
            
            # Map tags to lead stages
            tag_to_stage = {
                "qualificado": LeadStage.QUALIFIED,
                "proposta": LeadStage.PROPOSAL,
                "negociacao": LeadStage.NEGOTIATION,
                "convertido": LeadStage.CONVERTED,
                "contatado": LeadStage.CONTACTED,
            }
            
            # Update stage if tag matches
            new_stage = tag_to_stage.get(tag.lower())
            if new_stage:
                old_stage = lead.stage
                await lead_repo.update_stage(lead.id, new_stage)
                
                logger.info(
                    "lead_stage_updated_by_tag",
                    lead_id=str(lead.id),
                    contact_id=contact_id,
                    tag=tag,
                    old_stage=old_stage,
                    new_stage=new_stage,
                )
            
            # Update metadata with tag
            if lead.metadata is None:
                lead.metadata = {}
            
            if "tags" not in lead.metadata:
                lead.metadata["tags"] = []
            
            if tag not in lead.metadata["tags"]:
                lead.metadata["tags"].append(tag)
            
            await session.commit()
            
            logger.info(
                "tag_added_processed",
                lead_id=str(lead.id),
                contact_id=contact_id,
                tag=tag,
            )
    
    except Exception as e:
        logger.error(
            "tag_added_handler_failed",
            error=str(e),
            contact_id=payload.get("contact", {}).get("id"),
            tag=payload.get("tag"),
        )
        raise


async def handle_tag_removed(payload: dict[str, Any]) -> None:
    """
    Handle tag removed from contact.
    
    Removes automations or updates lead status.
    
    Args:
        payload: Webhook payload with tag information
    """
    try:
        contact = payload.get("contact", {})
        contact_id = contact.get("id")
        tag = payload.get("tag")
        
        logger.info(
            "processing_tag_removed",
            contact_id=contact_id,
            tag=tag,
        )
        
        # Resolve tenant_id
        tenant_id = await _get_or_create_tenant_id(contact_id)
        
        # Create database session
        async with AsyncSessionLocal() as session:
            lead_repo = LeadRepository(session, tenant_id)
            
            # Get lead by contact ID
            lead = await lead_repo.get_by_chatwit_contact(contact_id)
            
            if not lead:
                logger.warning(
                    "lead_not_found_for_tag_removal",
                    contact_id=contact_id,
                    tag=tag,
                )
                return
            
            # Remove tag from metadata
            if lead.metadata and "tags" in lead.metadata:
                if tag in lead.metadata["tags"]:
                    lead.metadata["tags"].remove(tag)
            
            # Handle special tags that trigger automation removal
            automation_tags = ["urgente", "follow_up", "automatico"]
            if tag.lower() in automation_tags:
                logger.info(
                    "removing_automation_for_tag",
                    lead_id=str(lead.id),
                    contact_id=contact_id,
                    tag=tag,
                )
                
                # TODO: Implement automation removal logic
                # This would interact with the automation system
                # For now, just log the event
            
            await session.commit()
            
            logger.info(
                "tag_removed_processed",
                lead_id=str(lead.id),
                contact_id=contact_id,
                tag=tag,
            )
    
    except Exception as e:
        logger.error(
            "tag_removed_handler_failed",
            error=str(e),
            contact_id=payload.get("contact", {}).get("id"),
            tag=payload.get("tag"),
        )
        raise

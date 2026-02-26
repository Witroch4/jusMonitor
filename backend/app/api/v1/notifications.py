"""API endpoints for notifications."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification
from app.services.notification_service import NotificationService
from app.db.base import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# TODO: Add authentication dependency to get current user
# For now, using placeholder tenant_id and user_id
async def get_current_user():
    """Placeholder for authentication dependency."""
    return {
        "tenant_id": UUID("00000000-0000-0000-0000-000000000000"),
        "user_id": UUID("00000000-0000-0000-0000-000000000000"),
    }


@router.get("")
async def get_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Get notifications for the current user.
    
    Args:
        skip: Number of notifications to skip
        limit: Maximum number of notifications to return
        unread_only: If True, only return unread notifications
        current_user: Current authenticated user
        session: Database session
    
    Returns:
        List of notifications and unread count
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Build query
    query = select(Notification).where(
        Notification.tenant_id == tenant_id,
        Notification.user_id == user_id,
    )
    
    if unread_only:
        query = query.where(Notification.read == False)
    
    query = query.order_by(Notification.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await session.execute(query)
    notifications = result.scalars().all()
    
    # Get unread count
    unread_query = select(func.count()).where(
        Notification.tenant_id == tenant_id,
        Notification.user_id == user_id,
        Notification.read == False,
    )
    unread_result = await session.execute(unread_query)
    unread_count = unread_result.scalar()
    
    return {
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type.value,
                "title": n.title,
                "message": n.message,
                "read": n.read,
                "created_at": n.created_at.isoformat(),
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "metadata": n.metadata,
            }
            for n in notifications
        ],
        "unread_count": unread_count,
        "total": len(notifications),
    }


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Mark a notification as read.
    
    Args:
        notification_id: Notification ID
        current_user: Current authenticated user
        session: Database session
    
    Returns:
        Updated notification
    """
    service = NotificationService(session)
    
    try:
        notification = await service.mark_as_read(notification_id)
        
        # Verify ownership
        if notification.tenant_id != current_user["tenant_id"] or \
           notification.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this notification",
            )
        
        return {
            "id": str(notification.id),
            "read": notification.read,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/read-all")
async def mark_all_notifications_as_read(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Mark all notifications as read for the current user.
    
    Args:
        current_user: Current authenticated user
        session: Database session
    
    Returns:
        Number of notifications marked as read
    """
    service = NotificationService(session)
    
    count = await service.mark_all_as_read(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
    )
    
    return {
        "marked_as_read": count,
        "message": f"{count} notifications marked as read",
    }


@router.get("/unread-count")
async def get_unread_count(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Get count of unread notifications.
    
    Args:
        current_user: Current authenticated user
        session: Database session
    
    Returns:
        Unread notification count
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    query = select(func.count()).where(
        Notification.tenant_id == tenant_id,
        Notification.user_id == user_id,
        Notification.read == False,
    )
    
    result = await session.execute(query)
    count = result.scalar()
    
    return {
        "unread_count": count,
    }

# Notification System Implementation Summary

## Overview

Implemented a complete real-time notification system for the JusMonitor CRM with WebSocket support, notification center UI component, and four types of notifications.

## Components Implemented

### Frontend Components

#### 1. NotificationCenter Component (`frontend/components/notifications/NotificationCenter.tsx`)
- **Features:**
  - Bell icon with unread count badge
  - Dropdown with notification list
  - Visual indicators for different notification types
  - Mark individual notifications as read
  - Mark all notifications as read
  - Real-time updates via WebSocket
  - Browser notifications support
  - Responsive design with Shadcn/UI components

#### 2. useNotifications Hook (`frontend/hooks/useNotifications.ts`)
- **Features:**
  - Manages notification state
  - Loads initial notifications from API
  - Handles incoming WebSocket messages
  - Provides functions to mark notifications as read
  - Requests browser notification permission
  - Shows browser notifications for new alerts

#### 3. useWebSocket Hook (`frontend/hooks/useWebSocket.ts`)
- **Features:**
  - Persistent WebSocket connection
  - JWT authentication via query parameter
  - Automatic reconnection with exponential backoff
  - Maximum reconnection attempts (10)
  - Reconnects when tab becomes visible
  - Ping/pong keepalive support
  - Clean disconnect on unmount

### Backend Components

#### 1. WebSocket Endpoint (`backend/app/api/v1/websocket.py`)
- **Features:**
  - WebSocket endpoint at `/ws`
  - JWT authentication via query parameter
  - Connection manager for multi-tenant support
  - Broadcast to all connections for a tenant
  - Send personal messages to specific connections
  - Automatic cleanup of disconnected clients
  - Structured logging for debugging

#### 2. Notification Model (`backend/app/db/models/notification.py`)
- **Fields:**
  - `id`: UUID primary key
  - `tenant_id`: Foreign key to tenants
  - `user_id`: Foreign key to users
  - `type`: Enum (urgent_movement, qualified_lead, briefing_available, mention)
  - `title`: Notification title
  - `message`: Notification message
  - `read`: Boolean flag
  - `metadata`: JSONB for additional data
  - `created_at`: Timestamp
  - `read_at`: Timestamp when marked as read

#### 3. Notification Service (`backend/app/services/notification_service.py`)
- **Methods:**
  - `create_urgent_movement_notification()`: For urgent process movements
  - `create_qualified_lead_notification()`: For automatically qualified leads
  - `create_briefing_available_notification()`: For morning briefings
  - `create_mention_notification()`: For user mentions in notes
  - `mark_as_read()`: Mark single notification as read
  - `mark_all_as_read()`: Mark all user notifications as read
  - Automatically sends notifications via WebSocket

#### 4. Notification API (`backend/app/api/v1/notifications.py`)
- **Endpoints:**
  - `GET /api/v1/notifications`: List notifications with pagination
  - `POST /api/v1/notifications/{id}/read`: Mark notification as read
  - `POST /api/v1/notifications/read-all`: Mark all as read
  - `GET /api/v1/notifications/unread-count`: Get unread count

#### 5. Database Migration (`backend/alembic/versions/004_add_notifications_table.py`)
- Creates `notifications` table
- Creates `notification_type` enum
- Creates indexes for performance:
  - `tenant_id`, `user_id`, `type`, `read`, `created_at`
  - Composite index for common queries

## Notification Types

### 1. Urgent Movement (`urgent_movement`)
- **Trigger:** Critical process movement detected
- **Icon:** ⚠️ (Warning)
- **Color:** Red
- **Metadata:** `process_id`, `process_number`

### 2. Qualified Lead (`qualified_lead`)
- **Trigger:** Lead automatically qualified by AI
- **Icon:** 🎯 (Target)
- **Color:** Green
- **Metadata:** `lead_id`, `lead_name`, `score`

### 3. Briefing Available (`briefing_available`)
- **Trigger:** Morning briefing generated
- **Icon:** 📋 (Clipboard)
- **Color:** Blue
- **Metadata:** `briefing_date`, `urgent_count`, `attention_count`

### 4. Mention (`mention`)
- **Trigger:** User mentioned in a note
- **Icon:** 💬 (Speech Bubble)
- **Color:** Purple
- **Metadata:** `mentioned_by_user_id`, `mentioned_by_name`, `client_id`, `client_name`

## WebSocket Authentication

The WebSocket connection uses JWT authentication via query parameter:

```
ws://localhost:8000/ws?token=<jwt_token>
```

The token must contain:
- `tenant_id`: UUID of the tenant
- Standard JWT claims (exp, iat, etc.)

This approach was chosen because:
1. WebSocket doesn't support custom headers in browsers
2. Cookies can be problematic with CORS
3. Query parameter is simple and works across all browsers

## Security Considerations

1. **JWT Validation:** Token is validated on connection
2. **Tenant Isolation:** Notifications are filtered by tenant_id
3. **User Authorization:** Users only see their own notifications
4. **Short-lived Tokens:** Tokens should have short expiration
5. **HTTPS/WSS:** Use secure connections in production

## Integration Points

### To Send Notifications from Workers:

```python
from app.services.notification_service import NotificationService
from app.db.base import get_db

async with get_db() as session:
    service = NotificationService(session)
    await service.create_urgent_movement_notification(
        tenant_id=tenant_id,
        user_id=user_id,
        process_id=process_id,
        process_number="1234567-89.2024.8.01.0001",
        movement_description="Sentença publicada",
    )
```

### To Use in Frontend:

```tsx
import { NotificationCenter } from '@/components/notifications/NotificationCenter'

export function Layout() {
  return (
    <header>
      <NotificationCenter />
    </header>
  )
}
```

## Environment Variables

Add to `.env`:

```bash
# Frontend
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Backend (already configured)
SECRET_KEY=<your-secret-key>
JWT_ALGORITHM=HS256
```

## Database Migration

Run the migration:

```bash
cd backend
alembic upgrade head
```

## Testing

### Manual Testing:

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Login to get JWT token
4. Open browser console to see WebSocket connection
5. Create a notification via API or worker
6. See notification appear in real-time

### WebSocket Testing:

Use a WebSocket client to test:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=<your-jwt-token>')
ws.onmessage = (event) => console.log(JSON.parse(event.data))
```

## Future Enhancements

1. **Notification Preferences:** Allow users to configure which notifications they want
2. **Email Notifications:** Send email for critical notifications
3. **Push Notifications:** Mobile push notifications
4. **Notification History:** Archive old notifications
5. **Notification Groups:** Group similar notifications
6. **Sound Alerts:** Optional sound for new notifications
7. **Desktop Notifications:** Better desktop notification support
8. **Notification Templates:** Customizable notification templates

## Requirements Validated

- ✅ **Requirement 3.4:** Real-time notifications via WebSocket
- ✅ Badge with unread count
- ✅ Dropdown with notification list
- ✅ Mark as read functionality
- ✅ Persistent WebSocket connection
- ✅ Automatic reconnection
- ✅ JWT authentication
- ✅ Four notification types implemented

## Files Created

### Frontend:
- `frontend/components/notifications/NotificationCenter.tsx`
- `frontend/hooks/useNotifications.ts`
- `frontend/hooks/useWebSocket.ts`

### Backend:
- `backend/app/api/v1/websocket.py`
- `backend/app/api/v1/notifications.py`
- `backend/app/db/models/notification.py`
- `backend/app/services/notification_service.py`
- `backend/alembic/versions/004_add_notifications_table.py`

### Documentation:
- `NOTIFICATION_SYSTEM_IMPLEMENTATION.md`

## Files Modified

- `backend/app/main.py` - Added WebSocket endpoint
- `backend/app/db/models/user.py` - Added notifications relationship
- `backend/app/db/models/tenant.py` - Added notifications relationship

# Dashboard Implementation - Central Operacional

## Overview

This document describes the implementation of Task 13: CRM - Central Operacional, which provides a comprehensive dashboard for monitoring legal cases and office metrics.

## Implemented Components

### 1. API Endpoints (`app/api/v1/endpoints/dashboard.py`)

#### Core Dashboard Endpoints

- **GET `/v1/dashboard/urgent`** - Returns urgent cases (deadline < 3 days)
  - Filters: `limit`, `assigned_to`
  - Returns: List of cases with approaching deadlines
  - Ordered by: Deadline (most urgent first)

- **GET `/v1/dashboard/attention`** - Returns cases needing attention (no movement > 30 days)
  - Filters: `limit`, `assigned_to`
  - Returns: List of stagnant cases
  - Ordered by: Last movement date (oldest first)

- **GET `/v1/dashboard/good-news`** - Returns positive movements and favorable decisions
  - Filters: `limit`, `days`, `assigned_to`
  - Returns: Important movements with positive keywords
  - Keywords: deferido, procedente, favorável, ganho, vitória, êxito, homologado, aprovado
  - Ordered by: Movement date (most recent first)

- **GET `/v1/dashboard/noise`** - Returns low-priority, irrelevant movements
  - Filters: `limit`, `days`, `assigned_to`
  - Returns: Non-important movements not requiring action
  - Ordered by: Movement date (most recent first)

- **GET `/v1/dashboard/metrics`** - Returns office KPIs with trends
  - Parameters: `days` (period length, default 30)
  - Returns: Conversion rate, response time, satisfaction score, case/client counts
  - Includes: Comparison with previous period (% change)

#### User Preferences Endpoints

- **GET `/v1/dashboard/preferences`** - Get user's dashboard preferences
  - Returns: User's saved preferences or defaults

- **PUT `/v1/dashboard/preferences`** - Update user's dashboard preferences
  - Body: `DashboardPreferencesUpdate`
  - Saves: Display settings, filters, auto-refresh configuration

- **GET `/v1/dashboard/summary`** - Get complete dashboard summary
  - Returns: Counts for all dashboard sections
  - Useful for: Overview widgets and notifications

### 2. Schemas (`app/schemas/`)

#### Dashboard Schemas (`dashboard.py`)

- `UrgentCaseItem` - Urgent case with deadline information
- `AttentionCaseItem` - Case needing attention with stagnation info
- `GoodNewsItem` - Positive movement with AI summary
- `NoiseItem` - Low-priority movement
- `OfficeMetrics` - Office KPIs with trend comparisons
- Response models for each endpoint

#### User Preference Schemas (`user_preference.py`)

- `UserPreferenceBase` - Base preference schema
- `UserPreferenceCreate` - Create preference
- `UserPreferenceUpdate` - Update preference
- `UserPreferenceResponse` - Preference response
- `DashboardPreferences` - Dashboard-specific preferences
  - Display toggles (show_urgent, show_attention, etc.)
  - Default filters (assigned_to, case_type)
  - Auto-refresh settings
  - Default period and limits

### 3. Services (`app/core/services/dashboard/`)

#### Dashboard Aggregator (`aggregator.py`)

Service for aggregating dashboard data with the following methods:

- `get_today_briefing()` - Fetch today's briefing
- `get_urgent_count(days_threshold=3)` - Count urgent cases
- `get_attention_count(days_threshold=30)` - Count cases needing attention
- `get_good_news_count(days_back=7)` - Count good news items
- `get_noise_count(days_back=7)` - Count noise items
- `get_dashboard_summary()` - Get complete summary with all counts
- `classify_movement(movement)` - Classify movement into categories

#### Metrics Calculator (`metrics.py`)

Service for calculating office metrics:

- `calculate_conversion_rate(period_start, period_end)` - Lead to client conversion %
- `calculate_avg_response_time(period_start, period_end)` - Average response time in hours
- `calculate_satisfaction_score(period_start, period_end)` - Client satisfaction (0-100)
- `calculate_metrics_with_trends(days=30)` - All metrics with period comparison
- `generate_trend_data(days=30, data_points=7)` - Trend arrays for charts

### 4. Database Models

#### User Preference Model (`app/db/models/user_preference.py`)

New table for storing user-specific settings:

```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID NOT NULL REFERENCES users(id),
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tenant_id, user_id, preference_key)
);
```

### 5. Database Migration

**Migration 003**: `003_add_user_preferences.py`
- Creates `user_preferences` table
- Adds indexes on `tenant_id` and `user_id`
- Adds unique constraint on `(tenant_id, user_id, preference_key)`

## Data Classification Logic

### Urgent Cases
- Criteria: `next_deadline <= today + 3 days AND next_deadline >= today`
- Purpose: Identify cases requiring immediate attention
- Sorting: By deadline (ascending)

### Attention Cases
- Criteria: `last_movement_date <= today - 30 days`
- Purpose: Identify stagnant cases that may need action
- Sorting: By last movement date (ascending - oldest first)

### Good News
- Criteria: `is_important = true AND description contains positive keywords`
- Keywords: deferido, procedente, favorável, ganho, vitória, êxito, homologado, aprovado
- Purpose: Highlight favorable decisions and positive outcomes
- Sorting: By movement date (descending - most recent first)

### Noise
- Criteria: `is_important = false AND requires_action = false`
- Purpose: Low-priority movements that don't require attention
- Sorting: By movement date (descending - most recent first)

## Metrics Calculation

### Conversion Rate
- Formula: `(converted_leads / total_leads) * 100`
- Period: Configurable (default 30 days)
- Comparison: With previous period of same length

### Average Response Time
- Current: Placeholder implementation based on activity level
- Production: Should calculate from timeline events (message_received → first_response)
- Unit: Hours

### Satisfaction Score
- Current: Uses average client health_score as proxy
- Production: Should integrate with actual satisfaction surveys/NPS
- Range: 0-100

### Trend Calculation
- Change for rates: Percentage point difference (current - previous)
- Change for times: Percentage change ((current - previous) / previous * 100)
- Negative change in response time is good (faster response)

## Multi-Tenancy

All endpoints and services enforce tenant isolation:
- Tenant ID extracted from JWT token via `get_current_user` dependency
- All database queries filtered by `tenant_id`
- User preferences scoped to tenant and user

## Caching Strategy

Recommended caching (not yet implemented):
- Dashboard summary: 5 minutes
- Metrics: 15 minutes
- Good news/noise: 10 minutes
- Urgent/attention: No cache (real-time)

## API Usage Examples

### Get Urgent Cases
```bash
GET /v1/dashboard/urgent?limit=10&assigned_to=<uuid>
Authorization: Bearer <token>
```

### Get Metrics
```bash
GET /v1/dashboard/metrics?days=30
Authorization: Bearer <token>
```

### Update Dashboard Preferences
```bash
PUT /v1/dashboard/preferences
Authorization: Bearer <token>
Content-Type: application/json

{
  "show_noise": false,
  "default_period_days": 60,
  "auto_refresh_enabled": true,
  "auto_refresh_interval_seconds": 300
}
```

## Testing

To test the implementation:

1. Start the backend services:
   ```bash
   docker-compose up -d
   ```

2. Run migrations:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

3. Test endpoints with curl or Postman:
   ```bash
   # Login first to get token
   curl -X POST http://localhost:8000/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "password"}'
   
   # Use token to access dashboard
   curl http://localhost:8000/v1/dashboard/urgent \
     -H "Authorization: Bearer <token>"
   ```

## Future Enhancements

1. **Real-time Updates**: Implement WebSocket for live dashboard updates
2. **Advanced Caching**: Add Redis caching for frequently accessed data
3. **Custom Metrics**: Allow tenants to define custom KPIs
4. **Export Functionality**: Export dashboard data to PDF/Excel
5. **Alerts**: Configurable alerts for urgent cases and metrics thresholds
6. **AI Insights**: Use AI to generate insights and recommendations
7. **Trend Visualization**: Generate chart data for frontend visualization
8. **Performance Optimization**: Add database indexes for common queries
9. **Batch Processing**: Optimize queries with batch loading
10. **Audit Trail**: Track dashboard access and preference changes

## Files Created/Modified

### Created Files
- `backend/app/api/v1/endpoints/dashboard.py` - Dashboard API endpoints
- `backend/app/schemas/dashboard.py` - Dashboard schemas
- `backend/app/schemas/user_preference.py` - User preference schemas
- `backend/app/core/services/dashboard/__init__.py` - Service exports
- `backend/app/core/services/dashboard/aggregator.py` - Data aggregation service
- `backend/app/core/services/dashboard/metrics.py` - Metrics calculation service
- `backend/app/db/models/user_preference.py` - User preference model
- `backend/alembic/versions/003_add_user_preferences.py` - Database migration

### Modified Files
- `backend/app/api/v1/router.py` - Added dashboard router
- `backend/app/db/models/__init__.py` - Added UserPreference import

## Compliance with Requirements

This implementation satisfies the following requirements from the spec:

- **Requirement 4.1**: Dashboard with 4 blocks (Urgent, Attention, Good News, Noise) ✓
- **Requirement 4.2**: Office metrics (conversion rate, response time, satisfaction) ✓
- **Requirement 4.3**: Filters and personalization ✓

All subtasks completed:
- ✓ 13.1 Criar API do dashboard
- ✓ 13.2 Implementar agregação de dados do briefing
- ✓ 13.3 Implementar métricas do escritório
- ✓ 13.4 Implementar filtros e personalização
- ⊘ 13.5 Escrever testes do dashboard (OPTIONAL - not implemented)


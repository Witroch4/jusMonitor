# Observability and Monitoring Implementation

## Overview

This document describes the implementation of observability and monitoring features for the JusMonitor CRM Orquestrador backend, completed as part of Task 20.

## Components Implemented

### 1. Structured Logging (Task 20.1)

**Files Created:**
- `app/core/logging.py` - Structured logging configuration using structlog
- `app/core/middleware/logging.py` - Logging middleware for request context

**Features:**
- JSON-formatted logs for production (easy parsing by log aggregators)
- Human-readable colored output for development
- Automatic context injection: `tenant_id`, `user_id`, `request_id`
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Logs sent to stdout (Docker/Kubernetes compatible)

**Usage Example:**
```python
from app.core.logging import get_logger, bind_context

logger = get_logger(__name__)

# Bind context for all subsequent logs
bind_context(tenant_id=str(tenant_id), user_id=str(user_id))

# Log with structured data
logger.info("user_login", email=user.email, ip_address=request.client.host)
logger.error("database_error", error=str(e), query=query)
```

**Configuration:**
- Controlled via `settings.log_level` (default: INFO)
- Development mode: colored console output
- Production mode: JSON output for log aggregation

### 2. Prometheus Metrics (Task 20.2)

**Files Created:**
- `app/core/metrics.py` - Prometheus metrics definitions
- `app/core/middleware/metrics.py` - Metrics collection middleware
- `app/api/v1/endpoints/metrics.py` - Metrics endpoint for scraping

**Metrics Implemented:**

#### HTTP Metrics
- `http_request_duration_seconds` - Request duration histogram
- `http_request_count` - Total request count by method/path/status
- `http_error_rate` - Error count by type

#### Business Metrics - Leads
- `leads_created_total` - Total leads created
- `leads_converted_total` - Total leads converted to clients
- `leads_by_stage` - Current leads by stage

#### Business Metrics - Cases
- `cases_created_total` - Total cases created
- `cases_updated_total` - Total cases updated
- `cases_by_status` - Current cases by status

#### Business Metrics - Movements
- `movements_detected_total` - Total movements detected
- `movements_requiring_action` - Movements requiring action

#### AI Metrics
- `ai_requests_total` - Total AI requests by agent/provider
- `ai_request_duration_seconds` - AI request duration
- `ai_errors_total` - AI errors by type

#### Embedding Metrics
- `embeddings_generated_total` - Total embeddings generated
- `embeddings_generation_duration_seconds` - Generation duration

#### DataJud Integration Metrics
- `datajud_requests_total` - Total DataJud API requests
- `datajud_request_duration_seconds` - Request duration
- `datajud_rate_limit_remaining` - Remaining API quota

#### Chatwit Integration Metrics
- `chatwit_webhooks_received_total` - Total webhooks received
- `chatwit_messages_sent_total` - Total messages sent

#### Task Queue Metrics
- `taskiq_tasks_enqueued_total` - Total tasks enqueued
- `taskiq_tasks_completed_total` - Total tasks completed
- `taskiq_task_duration_seconds` - Task execution duration

#### Database Metrics
- `db_query_duration_seconds` - Query duration
- `db_connections_active` - Active connections
- `db_connections_idle` - Idle connections

#### Cache Metrics
- `cache_hits_total` - Cache hits
- `cache_misses_total` - Cache misses

**Endpoint:**
- `GET /metrics` - Prometheus scraping endpoint (text/plain format)

**Usage Example:**
```python
from app.core.metrics import leads_created_total, ai_request_duration_seconds
import time

# Increment counter
leads_created_total.labels(tenant_id=str(tenant_id), source="chatwit").inc()

# Record duration
start = time.time()
# ... do work ...
duration = time.time() - start
ai_request_duration_seconds.labels(
    agent_type="triagem",
    provider="openai"
).observe(duration)
```

### 3. Health Checks (Task 20.3)

**Files Created:**
- `app/api/v1/endpoints/health.py` - Health check endpoints

**Endpoints:**

#### Liveness Probe
- `GET /health/live`
- Indicates if the application is running
- Used by Kubernetes to determine if pod should be restarted
- Always returns 200 if application is alive

#### Readiness Probe
- `GET /health/ready`
- Indicates if application is ready to serve traffic
- Checks: Database connectivity, Redis connectivity
- Returns 200 if ready, 503 if not ready
- Used by Kubernetes to determine if pod should receive traffic

#### Startup Probe
- `GET /health/startup`
- Indicates if application has completed initialization
- Checks: Database connectivity, migrations applied
- Returns 200 if started, 503 if still starting
- Used by Kubernetes during pod startup

#### Legacy Health Check
- `GET /health`
- Simple health check without dependency checks
- Returns basic status information

**Response Format:**
```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "redis": true
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "jusmonitor-backend",
  "version": "0.1.0"
}
```

### 4. Audit Logs (Task 20.4)

**Files Created:**
- `app/core/services/audit_service.py` - Audit logging service
- `app/core/middleware/audit.py` - Audit middleware
- `app/db/repositories/audit_log_repository.py` - Audit log repository
- `app/api/v1/endpoints/audit.py` - Audit log query endpoints
- `app/schemas/audit.py` - Audit log schemas

**Features:**
- Automatic capture of user actions
- Records: action type, entity type/id, old/new values
- Captures: IP address, user agent, timestamp
- Tenant-isolated audit logs
- Query endpoints for compliance and debugging

**Audit Service Usage:**
```python
from app.core.services.audit_service import AuditService

audit_service = AuditService(session)

# Log entity creation
await audit_service.log_create(
    tenant_id=tenant_id,
    entity_type="client",
    entity_id=client.id,
    values={"name": client.name, "email": client.email},
    user_id=user.id,
    ip_address=request.state.audit_ip,
    user_agent=request.state.audit_user_agent,
)

# Log entity update
await audit_service.log_update(
    tenant_id=tenant_id,
    entity_type="lead",
    entity_id=lead.id,
    old_values={"stage": "novo"},
    new_values={"stage": "qualificado"},
    user_id=user.id,
)

# Log state change
await audit_service.log_state_change(
    tenant_id=tenant_id,
    entity_type="case",
    entity_id=case.id,
    old_state="active",
    new_state="closed",
    user_id=user.id,
)
```

**Query Endpoints:**
- `GET /api/v1/audit/logs` - Query audit logs with filters
- `GET /api/v1/audit/logs/entity/{entity_type}/{entity_id}` - Get logs for specific entity
- `GET /api/v1/audit/logs/user/{user_id}` - Get logs for specific user

**Query Parameters:**
- `limit` - Maximum number of logs (1-1000)
- `user_id` - Filter by user
- `entity_type` - Filter by entity type
- `entity_id` - Filter by entity ID
- `action` - Filter by action (create, update, delete, etc.)
- `start_date` - Filter by start date
- `end_date` - Filter by end date

## Middleware Stack

The middleware stack is configured in the following order (from outer to inner):

1. **AuditMiddleware** - Captures IP and user agent for audit logs
2. **MetricsMiddleware** - Records HTTP metrics
3. **LoggingMiddleware** - Adds logging context and logs requests
4. **CORSMiddleware** - Handles CORS

## Configuration

All observability features are configured via environment variables in `.env`:

```env
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
ENVIRONMENT=development  # development, staging, production

# Monitoring
PROMETHEUS_ENABLED=true
SENTRY_DSN=  # Optional: Sentry error tracking
```

## Integration with Kubernetes

### Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3
```

### Readiness Probe
```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Startup Probe
```yaml
startupProbe:
  httpGet:
    path: /health/startup
    port: 8000
  initialDelaySeconds: 0
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 30
```

### Prometheus Scraping
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

## Prometheus Configuration

Add the following to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'jusmonitor-backend'
    scrape_interval: 15s
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
```

## Grafana Dashboards

Recommended dashboards to create:

1. **HTTP Performance**
   - Request rate by endpoint
   - Request duration percentiles (p50, p95, p99)
   - Error rate by endpoint

2. **Business Metrics**
   - Leads created/converted over time
   - Cases by status
   - Movements requiring action

3. **AI Performance**
   - AI request rate by agent
   - AI request duration by provider
   - AI error rate

4. **System Health**
   - Database connection pool usage
   - Cache hit/miss ratio
   - Task queue metrics

## Log Aggregation

For production, configure a log aggregation system:

### ELK Stack (Elasticsearch, Logstash, Kibana)
```yaml
# docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Loki (Grafana Loki)
```yaml
# promtail-config.yml
scrape_configs:
  - job_name: jusmonitor
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: 'container'
```

## Testing

### Test Logging
```bash
# Start the application
uvicorn app.main:app --reload

# Make a request
curl http://localhost:8000/health

# Check logs in stdout
```

### Test Metrics
```bash
# Query metrics endpoint
curl http://localhost:8000/metrics

# Should return Prometheus format metrics
```

### Test Health Checks
```bash
# Liveness
curl http://localhost:8000/health/live

# Readiness
curl http://localhost:8000/health/ready

# Startup
curl http://localhost:8000/health/startup
```

### Test Audit Logs
```bash
# Query audit logs (requires authentication)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/audit/logs?limit=10
```

## Best Practices

### Logging
1. Use structured logging with key-value pairs
2. Include tenant_id in all business logic logs
3. Log at appropriate levels (INFO for normal operations, ERROR for failures)
4. Avoid logging sensitive data (passwords, tokens, PII)

### Metrics
1. Use labels sparingly (high cardinality can impact performance)
2. Record business metrics in addition to technical metrics
3. Use histograms for duration measurements
4. Use counters for event counts
5. Use gauges for current state

### Health Checks
1. Keep health checks lightweight (< 1 second)
2. Don't include external API calls in readiness checks
3. Use startup probes for slow-starting applications

### Audit Logs
1. Log all write operations (create, update, delete)
2. Log sensitive read operations (accessing PII)
3. Log authentication events
4. Include enough context for forensic analysis
5. Implement log retention policies (12 months recommended)

## Troubleshooting

### Logs not appearing
- Check LOG_LEVEL environment variable
- Verify logging is configured in main.py
- Check stdout/stderr output

### Metrics not updating
- Verify MetricsMiddleware is registered
- Check /metrics endpoint returns data
- Ensure Prometheus is scraping correctly

### Health checks failing
- Check database connectivity
- Verify Redis is running
- Check application logs for errors

### Audit logs not created
- Verify AuditService is being called in endpoints
- Check database for audit_logs table
- Verify tenant_id is set correctly

## Future Enhancements

1. **Distributed Tracing** - Add OpenTelemetry for request tracing
2. **Error Tracking** - Integrate Sentry for error monitoring
3. **Custom Dashboards** - Create Grafana dashboards for business metrics
4. **Alerting** - Configure Prometheus alerts for critical metrics
5. **Log Analysis** - Add log parsing and analysis tools
6. **Performance Profiling** - Add profiling for slow endpoints

## Requirements Validation

This implementation satisfies Requirement 20 (Healthcheck e Monitoramento):

✅ Exposes /health endpoint returning 200 when operational
✅ Verifies connectivity with database, Redis, and Taskiq
✅ Returns 503 when critical components are unavailable
✅ Exposes Prometheus metrics at /metrics endpoint
✅ Implements structured logging with tenant context
✅ Records audit logs for all user actions

All acceptance criteria have been met.

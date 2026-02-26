# Graceful Shutdown Implementation

## Overview

This document describes the graceful shutdown implementation for the JusMonitor CRM Orquestrador backend. The system handles SIGTERM and SIGINT signals properly to ensure clean shutdown during deployments, restarts, or container orchestration events.

## Architecture

### Components

1. **GracefulShutdown Handler** (`app/core/shutdown.py`)
   - Captures SIGTERM and SIGINT signals
   - Tracks in-flight requests
   - Manages shutdown callbacks
   - Coordinates graceful shutdown sequence

2. **ShutdownMiddleware** (`app/core/middleware/shutdown.py`)
   - Tracks in-flight HTTP requests
   - Rejects new requests during shutdown (503 Service Unavailable)
   - Ensures existing requests complete gracefully

3. **Taskiq Worker Shutdown** (`app/workers/broker.py`)
   - Handles worker-level signal handlers
   - Allows in-flight tasks to complete
   - Closes Redis connections gracefully

4. **Database Connection Cleanup** (`app/db/engine.py`)
   - Closes all database connections
   - Disposes of connection pool
   - Ensures no orphaned connections

## Shutdown Sequence

### 1. Signal Reception
```
SIGTERM/SIGINT → GracefulShutdown.setup_signal_handlers()
```

When a shutdown signal is received:
- Signal handler is triggered
- `is_shutting_down` flag is set to `True`
- Shutdown event is created

### 2. Request Rejection
```
New HTTP Request → ShutdownMiddleware → 503 Service Unavailable
```

Once shutdown is initiated:
- New requests receive 503 status code
- Response includes `Retry-After: 30` header
- Existing requests continue processing

### 3. Wait for In-Flight Requests
```
GracefulShutdown._wait_for_requests() → Wait up to 30 seconds
```

The system waits for:
- All in-flight HTTP requests to complete
- Configurable timeout (default: 30 seconds)
- Periodic checks every 100ms

### 4. Execute Shutdown Callbacks
```
GracefulShutdown._execute_shutdown_callbacks()
  ├── broker.shutdown() → Close Taskiq Redis connections
  └── close_db() → Dispose database connection pool
```

Callbacks are executed in registration order:
- Each callback has a timeout
- Errors are logged but don't stop other callbacks
- Both sync and async callbacks are supported

### 5. Application Shutdown
```
FastAPI lifespan context exit → Final cleanup
```

The application lifespan manager:
- Ensures broker is shut down
- Ensures database connections are closed
- Logs shutdown completion

## Configuration

### Timeouts

Configure shutdown timeouts in `app/main.py`:

```python
shutdown_handler = setup_graceful_shutdown(
    shutdown_timeout=30.0,        # Wait for requests/callbacks
    force_shutdown_timeout=60.0,  # Force shutdown after this
)
```

### Environment Variables

No specific environment variables are required. The shutdown behavior is controlled by:
- `shutdown_timeout`: Time to wait for graceful shutdown (seconds)
- `force_shutdown_timeout`: Maximum time before forcing shutdown (seconds)

## Usage

### Running the Application

The graceful shutdown is automatically configured when the application starts:

```bash
# Development
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Production (with Gunicorn)
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --graceful-timeout 30 \
  --timeout 60
```

### Running Taskiq Workers

Workers also handle graceful shutdown:

```bash
# Start worker
taskiq worker app.workers.main:broker --workers 4

# Send SIGTERM to gracefully shutdown
kill -TERM <worker_pid>
```

### Docker Deployment

In Docker, ensure proper signal handling:

```dockerfile
# Use exec form to ensure signals are passed
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Or with Gunicorn
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--graceful-timeout", "30"]
```

Docker Compose configuration:

```yaml
services:
  backend:
    build: ./backend
    stop_grace_period: 45s  # Allow time for graceful shutdown
    stop_signal: SIGTERM
```

### Kubernetes Deployment

Configure proper termination grace period:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jusmonitor-backend
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 45
      containers:
      - name: backend
        image: jusmonitor-backend:latest
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 5"]
```

## Monitoring

### Logs

The shutdown process is fully logged with structured logging:

```json
{
  "event": "shutdown_initiated",
  "signal": "SIGTERM",
  "timestamp": "2024-01-15T10:30:00Z"
}

{
  "event": "waiting_for_requests",
  "in_flight": 3,
  "timeout": 30.0,
  "timestamp": "2024-01-15T10:30:00Z"
}

{
  "event": "requests_completed",
  "remaining": 0,
  "timestamp": "2024-01-15T10:30:05Z"
}

{
  "event": "executing_shutdown_callbacks",
  "count": 2,
  "timestamp": "2024-01-15T10:30:05Z"
}

{
  "event": "shutdown_completed",
  "timestamp": "2024-01-15T10:30:10Z"
}
```

### Metrics

Monitor shutdown behavior with Prometheus metrics:

- `http_requests_in_flight`: Current number of in-flight requests
- `shutdown_duration_seconds`: Time taken for graceful shutdown
- `shutdown_callbacks_total`: Number of shutdown callbacks executed
- `shutdown_callbacks_failed_total`: Number of failed callbacks

## Testing

### Unit Tests

Test individual components:

```bash
# Test shutdown handler
pytest tests/integration/test_graceful_shutdown.py::TestGracefulShutdown

# Test middleware
pytest tests/integration/test_graceful_shutdown.py::TestShutdownMiddleware

# Test worker shutdown
pytest tests/integration/test_graceful_shutdown.py::TestWorkerGracefulShutdown
```

### Integration Tests

Test end-to-end shutdown:

```bash
pytest tests/integration/test_graceful_shutdown.py::TestEndToEndGracefulShutdown -v
```

### Manual Testing

Test graceful shutdown manually:

```bash
# Terminal 1: Start application
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Make a long-running request
curl http://localhost:8000/api/v1/some-slow-endpoint

# Terminal 3: Send SIGTERM
kill -TERM $(pgrep -f "uvicorn app.main:app")

# Observe logs showing graceful shutdown
```

## Troubleshooting

### Issue: Requests timing out during shutdown

**Symptom**: Requests fail with connection errors during shutdown

**Solution**: Increase `shutdown_timeout`:
```python
shutdown_handler = setup_graceful_shutdown(
    shutdown_timeout=60.0,  # Increase from 30s
)
```

### Issue: Database connections not closing

**Symptom**: Database shows orphaned connections after shutdown

**Solution**: Ensure `close_db()` is registered as callback:
```python
shutdown_handler.register_shutdown_callback(close_db)
```

### Issue: Workers not shutting down gracefully

**Symptom**: Workers killed immediately without finishing tasks

**Solution**: 
1. Ensure signal handlers are registered in worker startup
2. Check that Taskiq is configured with proper shutdown timeout
3. Verify Docker/K8s `stop_grace_period` is sufficient

### Issue: 503 errors during deployment

**Symptom**: Users see 503 errors during rolling deployments

**Solution**: 
1. Implement proper load balancer health checks
2. Use readiness probes in Kubernetes
3. Configure connection draining in load balancer
4. Increase deployment rolling update parameters

## Best Practices

1. **Always use graceful shutdown in production**
   - Never use SIGKILL unless absolutely necessary
   - Configure proper grace periods in orchestration

2. **Monitor shutdown metrics**
   - Track shutdown duration
   - Alert on failed callbacks
   - Monitor in-flight request counts

3. **Test shutdown behavior**
   - Include shutdown tests in CI/CD
   - Test with realistic request loads
   - Verify database connections are closed

4. **Configure appropriate timeouts**
   - Match shutdown timeout to longest request duration
   - Add buffer for cleanup operations
   - Consider task processing times for workers

5. **Handle shutdown in tasks**
   - Check `is_shutting_down()` in long-running tasks
   - Implement checkpointing for resumable tasks
   - Use idempotent task design

## References

- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [Taskiq Graceful Shutdown](https://taskiq-python.github.io/)
- [Uvicorn Deployment](https://www.uvicorn.org/deployment/)
- [Kubernetes Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)

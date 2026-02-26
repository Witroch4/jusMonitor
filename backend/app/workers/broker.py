"""Taskiq broker configuration with Redis backend."""

import asyncio
import signal
from typing import Optional

import structlog
from taskiq import TaskiqEvents, TaskiqMiddleware
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.config import settings

logger = structlog.get_logger(__name__)


class LoggingMiddleware(TaskiqMiddleware):
    """Middleware for structured logging of task execution."""

    async def pre_execute(self, message: "TaskiqMessage") -> "TaskiqMessage":
        """Log before task execution."""
        logger.info(
            "task_started",
            task_name=message.task_name,
            task_id=message.task_id,
            labels=message.labels,
        )
        return message

    async def post_execute(
        self,
        message: "TaskiqMessage",
        result: "TaskiqResult",
    ) -> None:
        """Log after task execution."""
        if result.is_err:
            logger.error(
                "task_failed",
                task_name=message.task_name,
                task_id=message.task_id,
                error=str(result.error),
                execution_time=result.execution_time,
            )
        else:
            logger.info(
                "task_completed",
                task_name=message.task_name,
                task_id=message.task_id,
                execution_time=result.execution_time,
            )


# Configure Redis result backend
result_backend = RedisAsyncResultBackend(
    redis_url=str(settings.redis_url),
    max_connection_pool_size=settings.redis_max_connections,
)

# Configure broker with Redis
broker = ListQueueBroker(
    url=str(settings.redis_url),
    max_connection_pool_size=settings.redis_max_connections,
    queue_name="jusmonitor:tasks",
).with_result_backend(result_backend)

# Add logging middleware
broker.add_middlewares(LoggingMiddleware())


# Graceful shutdown state for workers
_shutdown_event: Optional[asyncio.Event] = None
_is_shutting_down = False


def _handle_shutdown_signal(signum: int) -> None:
    """
    Handle shutdown signals (SIGTERM, SIGINT) for Taskiq workers.
    
    Args:
        signum: Signal number
    """
    global _is_shutting_down, _shutdown_event
    
    signal_name = signal.Signals(signum).name
    logger.info("worker_shutdown_signal_received", signal=signal_name)
    
    _is_shutting_down = True
    
    if _shutdown_event:
        _shutdown_event.set()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state: "TaskiqState") -> None:
    """Initialize broker on worker startup."""
    global _shutdown_event
    
    logger.info("taskiq_worker_started")
    
    # Setup signal handlers for graceful shutdown
    _shutdown_event = asyncio.Event()
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, lambda s, f: _handle_shutdown_signal(s))
    signal.signal(signal.SIGINT, lambda s, f: _handle_shutdown_signal(s))
    
    logger.info("worker_signal_handlers_configured")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state: "TaskiqState") -> None:
    """Cleanup broker on worker shutdown."""
    logger.info("taskiq_worker_shutdown_initiated")
    
    # Wait a bit for in-flight tasks to complete
    # Taskiq handles this internally, but we log it
    await asyncio.sleep(1)
    
    logger.info("taskiq_worker_shutdown_complete")


def is_shutting_down() -> bool:
    """
    Check if worker is shutting down.
    
    Returns:
        True if shutdown is in progress
    """
    return _is_shutting_down


"""Structured logging configuration using structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.config import settings


def add_tenant_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add tenant_id to log context if available."""
    # This will be populated by middleware
    return event_dict


def add_request_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add request_id and user_id to log context if available."""
    # This will be populated by middleware
    return event_dict


def configure_logging() -> None:
    """
    Configure structured logging with structlog.
    
    Logs are sent to stdout in JSON format for Docker/Kubernetes.
    Includes context: tenant_id, user_id, request_id
    Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Shared processors for both dev and prod
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_tenant_context,
        add_request_context,
    ]

    if settings.is_development:
        # Development: human-readable console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # Production: JSON output for log aggregation
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured structlog logger
    
    Example:
        logger = get_logger(__name__)
        logger.info("user_login", user_id=user.id, tenant_id=tenant.id)
    """
    return structlog.get_logger(name)


# Context management utilities
def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables that will be included in all subsequent logs.
    
    Args:
        **kwargs: Context variables (tenant_id, user_id, request_id, etc.)
    
    Example:
        bind_context(tenant_id=str(tenant_id), request_id=request_id)
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


def unbind_context(*keys: str) -> None:
    """
    Remove specific context variables.
    
    Args:
        *keys: Context variable names to remove
    
    Example:
        unbind_context("request_id", "user_id")
    """
    structlog.contextvars.unbind_contextvars(*keys)

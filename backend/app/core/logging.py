"""
Structured logging configuration for the application.

This module sets up structured logging using structlog for better
observability and debugging in production environments.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.
    
    Sets up structlog with appropriate processors and formatters
    based on the environment (development vs production).
    """
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
    )
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if settings.ENVIRONMENT == "development":
        # Pretty console output for development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        structlog.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


class LogContext:
    """
    Context manager for adding structured logging context.
    
    Usage:
        with LogContext(user_id="123", action="login"):
            logger.info("User logged in")
    """
    
    def __init__(self, **context: Any):
        """
        Initialize logging context.
        
        Args:
            **context: Key-value pairs to add to log context
        """
        self.context = context
        self.logger = structlog.get_logger()
    
    def __enter__(self) -> structlog.BoundLogger:
        """Enter context and bind logger with context."""
        return self.logger.bind(**self.context)
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context (no cleanup needed)."""
        pass


def log_api_request(
    method: str,
    path: str,
    user_id: str = None,
    status_code: int = None,
    duration_ms: float = None,
    **extra: Any
) -> None:
    """
    Log API request with structured data.
    
    Args:
        method: HTTP method
        path: Request path
        user_id: User ID (if authenticated)
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **extra: Additional context data
    """
    logger = get_logger("api.request")
    
    log_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
        **extra
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    if status_code and status_code >= 400:
        logger.warning("API request completed with error", **log_data)
    else:
        logger.info("API request completed", **log_data)


def log_auth_event(
    event_type: str,
    user_id: str = None,
    email: str = None,
    provider: str = None,
    success: bool = True,
    **extra: Any
) -> None:
    """
    Log authentication events.
    
    Args:
        event_type: Type of auth event (login, logout, token_refresh, etc.)
        user_id: User ID
        email: User email
        provider: OAuth provider (google, hubspot)
        success: Whether the event was successful
        **extra: Additional context data
    """
    logger = get_logger("auth.event")
    
    log_data = {
        "event_type": event_type,
        "success": success,
        "provider": provider,
        **extra
    }
    
    if user_id:
        log_data["user_id"] = user_id
    if email:
        log_data["email"] = email
    
    if success:
        logger.info("Authentication event", **log_data)
    else:
        logger.warning("Authentication event failed", **log_data)


def log_ai_interaction(
    interaction_type: str,
    user_id: str,
    model: str = None,
    tokens_used: int = None,
    duration_ms: float = None,
    **extra: Any
) -> None:
    """
    Log AI/LLM interactions for monitoring and cost tracking.
    
    Args:
        interaction_type: Type of interaction (chat, embedding, tool_call)
        user_id: User ID
        model: AI model used
        tokens_used: Number of tokens consumed
        duration_ms: Interaction duration in milliseconds
        **extra: Additional context data
    """
    logger = get_logger("ai.interaction")
    
    log_data = {
        "interaction_type": interaction_type,
        "user_id": user_id,
        "model": model,
        "tokens_used": tokens_used,
        "duration_ms": duration_ms,
        **extra
    }
    
    logger.info("AI interaction", **log_data)


def log_integration_event(
    integration: str,
    event_type: str,
    user_id: str = None,
    success: bool = True,
    error: str = None,
    **extra: Any
) -> None:
    """
    Log third-party integration events (Gmail, Calendar, HubSpot).
    
    Args:
        integration: Integration name (gmail, calendar, hubspot)
        event_type: Type of event (webhook, sync, api_call)
        user_id: User ID
        success: Whether the event was successful
        error: Error message if failed
        **extra: Additional context data
    """
    logger = get_logger("integration.event")
    
    log_data = {
        "integration": integration,
        "event_type": event_type,
        "success": success,
        **extra
    }
    
    if user_id:
        log_data["user_id"] = user_id
    if error:
        log_data["error"] = error
    
    if success:
        logger.info("Integration event", **log_data)
    else:
        logger.error("Integration event failed", **log_data)
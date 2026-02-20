"""
Structured logging configuration using structlog.

Provides JSON logging for production and human-readable console logging for development.
"""

import logging
import sys
from typing import Any, Dict
import structlog
from rich.console import Console
from rich.logging import RichHandler

from ..config.settings import get_settings


def setup_logging() -> None:
    """
    Configure structured logging with JSON output and context support.

    Sets up:
    - JSON formatting for production
    - Rich console formatting for development
    - Contextual logging with request IDs and agent names
    - Proper log levels and filtering
    """
    settings = get_settings()

    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(message)s",
        handlers=[
            RichHandler(
                console=Console(stderr=True),
                show_time=True,
                show_path=True,
                enable_link_path=False,
                markup=True
            ) if settings.log_format == "console" else logging.StreamHandler(sys.stdout)
        ]
    )

    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]

    if settings.log_format == "json":
        processors.extend([
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.JSONRenderer()
        ])
    else:
        processors.extend([
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.dev.ConsoleRenderer(colors=True)
        ])

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a configured structlog logger with context.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class LoggingMixin:
    """
    Mixin class to add structured logging capabilities to agents.
    """

    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger with class context."""
        return get_logger(self.__class__.__name__)

    def log_operation_start(self, operation: str, **context: Any) -> None:
        """Log the start of an operation with context."""
        self.logger.info(
            "Operation started",
            operation=operation,
            **context
        )

    def log_operation_success(
        self,
        operation: str,
        duration: float = None,
        **context: Any
    ) -> None:
        """Log successful completion of an operation."""
        log_data = {
            "operation": operation,
            "status": "success",
            **context
        }
        if duration is not None:
            log_data["duration_seconds"] = round(duration, 3)

        self.logger.info("Operation completed", **log_data)

    def log_operation_error(
        self,
        operation: str,
        error: Exception,
        duration: float = None,
        **context: Any
    ) -> None:
        """Log operation failure with error details."""
        log_data = {
            "operation": operation,
            "status": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            **context
        }
        if duration is not None:
            log_data["duration_seconds"] = round(duration, 3)

        self.logger.error("Operation failed", **log_data, exc_info=True)

    def log_article_processed(
        self,
        url: str,
        source: str,
        category: str,
        severity: str,
        valid: bool = True
    ) -> None:
        """Log article processing result."""
        self.logger.info(
            "Article processed" if valid else "Article rejected",
            url=url,
            source=source,
            category=category,
            severity=severity,
            valid=valid
        )

    def log_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log performance and execution metrics."""
        self.logger.info("Execution metrics", **metrics)


def log_workflow_state(state_update: Dict[str, Any], node: str) -> None:
    """
    Log workflow state transitions.

    Args:
        state_update: State changes being applied
        node: Current workflow node
    """
    logger = get_logger("workflow")

    # Extract meaningful metrics
    metrics = {}
    if "phase1_articles" in state_update:
        metrics["phase1_articles_count"] = len(state_update["phase1_articles"])
    if "phase2_articles" in state_update:
        metrics["phase2_articles_count"] = len(state_update["phase2_articles"])
    if "validated_articles" in state_update:
        metrics["validated_articles_count"] = len(state_update["validated_articles"])
    if "errors" in state_update:
        metrics["error_count"] = len(state_update["errors"])

    logger.info(
        "Workflow state updated",
        node=node,
        **metrics
    )
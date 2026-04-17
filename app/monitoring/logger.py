"""Structured logging for the application."""

import os
import json
import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    # Sensitive fields to redact
    SENSITIVE_FIELDS = [
        "password", "token", "api_key", "secret", "credential",
        "authorization", "auth", "private_key", "access_token"
    ]

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add extra fields if present
        if hasattr(record, "channel"):
            log_data["channel"] = record.channel
        if hasattr(record, "ticket_id"):
            log_data["ticket_id"] = record.ticket_id
        if hasattr(record, "customer_id"):
            log_data["customer_id"] = self._redact_if_sensitive(record.customer_id)
        if hasattr(record, "metadata"):
            log_data["metadata"] = self._redact_sensitive_data(record.metadata)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

    def _redact_if_sensitive(self, value: str) -> str:
        """Redact value if it looks like sensitive data."""
        if not value:
            return value

        # Check if value contains sensitive patterns
        value_lower = value.lower()
        for field in self.SENSITIVE_FIELDS:
            if field in value_lower:
                return "[REDACTED]"

        return value

    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact sensitive data from dictionary."""
        if not isinstance(data, dict):
            return data

        redacted = {}
        for key, value in data.items():
            key_lower = key.lower()

            # Check if key is sensitive
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive_data(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value

        return redacted


def setup_logging(
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    component: str = "app"
) -> None:
    """
    Setup structured logging for the application.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
        component: Component name for log file
    """
    # Get log level from environment or parameter
    level_name = log_level or os.getenv("LOG_LEVEL", "INFO")
    level = getattr(logging, level_name.upper(), logging.INFO)

    # Get log directory
    if log_dir is None:
        log_dir = os.getenv("LOG_DIR", "logs")

    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create formatters
    json_formatter = JSONFormatter()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (JSON format)
    log_file = log_path / f"{component}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(json_formatter)
    root_logger.addHandler(file_handler)

    # Error log file (errors only)
    error_log_file = log_path / f"{component}_errors.log"
    error_handler = logging.FileHandler(error_log_file)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    root_logger.addHandler(error_handler)


def get_logger(
    name: str,
    channel: Optional[str] = None,
    ticket_id: Optional[str] = None,
    customer_id: Optional[str] = None
) -> logging.LoggerAdapter:
    """
    Get a logger with contextual information.

    Args:
        name: Logger name
        channel: Optional channel name
        ticket_id: Optional ticket ID
        customer_id: Optional customer ID

    Returns:
        LoggerAdapter with context
    """
    logger = logging.getLogger(name)

    # Build context
    context = {}
    if channel:
        context["channel"] = channel
    if ticket_id:
        context["ticket_id"] = ticket_id
    if customer_id:
        context["customer_id"] = customer_id

    return logging.LoggerAdapter(logger, context)


class StructuredLogger:
    """Structured logger with convenience methods."""

    def __init__(
        self,
        name: str,
        channel: Optional[str] = None,
        ticket_id: Optional[str] = None,
        customer_id: Optional[str] = None
    ):
        """Initialize structured logger."""
        self.logger = get_logger(name, channel, ticket_id, customer_id)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=kwargs)

    def log_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: float
    ):
        """Log HTTP request."""
        self.info(
            f"{method} {endpoint} - {status_code}",
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms
        )

    def log_ticket_event(
        self,
        event: str,
        ticket_id: str,
        status: Optional[str] = None
    ):
        """Log ticket event."""
        self.info(
            f"Ticket {event}: {ticket_id}",
            event=event,
            ticket_id=ticket_id,
            status=status
        )

    def log_escalation(
        self,
        ticket_id: str,
        reason: str,
        urgency: str
    ):
        """Log escalation event."""
        self.warning(
            f"Ticket escalated: {ticket_id}",
            ticket_id=ticket_id,
            reason=reason,
            urgency=urgency
        )

    def log_metric(
        self,
        metric_name: str,
        metric_value: float,
        **kwargs
    ):
        """Log metric."""
        self.info(
            f"Metric: {metric_name} = {metric_value}",
            metric_name=metric_name,
            metric_value=metric_value,
            **kwargs
        )

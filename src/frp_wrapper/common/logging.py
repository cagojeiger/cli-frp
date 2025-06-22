"""Centralized logging configuration using structlog."""

import logging
import sys

import structlog
from structlog.typing import Processor


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: str | None = None,
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, output JSON formatted logs
        log_file: Optional file path to write logs to
    """
    # Configure standard library logging
    log_level = getattr(logging, level.upper())

    # Get root logger and clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(log_level)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)

    # Build processor list
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add appropriate renderer
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(file_handler)


# Convenience function to get logger
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]

"""Structured logging configuration."""

import logging
import os
import sys
from pathlib import Path

import structlog

LOG_DIR = Path(os.getenv("LOG_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "logs")))
LOG_FILE = LOG_DIR / "dashboard.log"


def setup_logging(debug: bool = False) -> None:
    """Configure structlog for the application."""
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # File handler for debug log
    file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    # Configure stdlib logging (used by structlog as backend)
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler],
        format="%(message)s",
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a named logger."""
    return structlog.get_logger(name)

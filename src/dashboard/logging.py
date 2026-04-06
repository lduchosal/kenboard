"""Structured logging configuration."""

import logging
import os
import sys
from pathlib import Path
from typing import Any

import structlog

LOG_DIR = Path(
    os.getenv("LOG_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
)
LOG_FILE = LOG_DIR / "dashboard.log"


def setup_logging(debug: bool = False) -> None:
    """Configure structlog to output to both console and file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Configure stdlib logging as the backend
    file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Route structlog through stdlib logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Formatter for both handlers
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            (
                structlog.dev.ConsoleRenderer()
                if debug
                else structlog.processors.JSONRenderer()
            ),
        ],
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)


def get_logger(name: str) -> Any:
    """Get a named logger."""
    return structlog.get_logger(name)

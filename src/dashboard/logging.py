"""Structured logging configuration."""

import logging
import logging.handlers
import os
import signal
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any

import structlog

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / "dashboard.log"


def _ignore_sighup() -> None:
    """Ignore SIGHUP so newsyslog's post-rotate reload script does not kill us.

    Default Python behaviour for SIGHUP is to terminate the process. On
    FreeBSD (web2) newsyslog rotates ``/var/log/kenboard/kenboard.log``
    every day at 00:00 and signals the daemon afterwards via the rc.d
    ``reload`` script. We don't need to do anything on the signal — log
    re-opening is handled transparently by ``WatchedFileHandler`` — so
    we just refuse to die.
    """
    # SIGHUP does not exist on Windows; signal() may also fail when
    # called from a non-main thread (e.g. tests inside a thread).
    with suppress(AttributeError, ValueError):
        signal.signal(signal.SIGHUP, signal.SIG_IGN)


def setup_logging(debug: bool = False) -> None:
    """Configure structlog to output to both console and file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _ignore_sighup()

    # WatchedFileHandler reopens the log file when its inode changes,
    # which makes newsyslog rotation transparent: when the file is
    # renamed/removed at midnight the next emit() opens a fresh handle
    # at the same path. A plain FileHandler would silently keep writing
    # to the deleted inode forever.
    file_handler = logging.handlers.WatchedFileHandler(str(LOG_FILE), encoding="utf-8")
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

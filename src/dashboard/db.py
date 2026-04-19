"""Database connection and query loading."""

import functools
import time
from pathlib import Path
from typing import Any

import aiosql
import pymysql  # type: ignore[import-untyped]
import pymysql.cursors  # type: ignore[import-untyped]

from dashboard.config import Config

QUERIES_DIR = Path(__file__).parent / "queries"


class _InstrumentedQueries:
    """Proxy around aiosql queries that records timing in flask.g (#214).

    When called inside a Flask request with ``g.perf`` set, each query
    call is timed and recorded.  Outside Flask (CLI, tests) the proxy
    is a transparent passthrough.
    """

    def __init__(self, queries: Any) -> None:
        """Wrap the raw aiosql queries object."""
        object.__setattr__(self, "_queries", queries)

    def __getattr__(self, name: str) -> Any:
        """Intercept attribute access to wrap callable queries."""
        attr = getattr(object.__getattribute__(self, "_queries"), name)
        if not callable(attr):
            return attr

        @functools.wraps(attr)
        def timed(*args: Any, **kwargs: Any) -> Any:
            """Execute the query and record timing if perf is active."""
            try:
                from flask import g, has_request_context
            except ImportError:
                return attr(*args, **kwargs)

            if not has_request_context() or not hasattr(g, "perf"):
                return attr(*args, **kwargs)

            start = time.perf_counter()
            try:
                return attr(*args, **kwargs)
            finally:
                ms = (time.perf_counter() - start) * 1000
                g.perf.record_query(name, ms)

        return timed


def get_connection() -> pymysql.Connection:
    """Create a new database connection."""
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def load_queries() -> Any:
    """Load SQL queries from the queries directory.

    Returns an instrumented proxy that records query timing in
    ``flask.g.perf`` when running inside a Flask request (#214).
    """
    raw = aiosql.from_path(str(QUERIES_DIR), "pymysql", mandatory_parameters=False)
    return _InstrumentedQueries(raw)

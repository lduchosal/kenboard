"""Database connection and query loading."""

from pathlib import Path
from typing import Any

import aiosql
import pymysql  # type: ignore[import-untyped]
import pymysql.cursors  # type: ignore[import-untyped]

from dashboard.config import Config

QUERIES_DIR = Path(__file__).parent / "queries"


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
    """Load SQL queries from the queries directory."""
    return aiosql.from_path(str(QUERIES_DIR), "pymysql", mandatory_parameters=False)

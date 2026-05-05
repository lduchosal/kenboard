"""Test schema loader.

Reads ``tests/sql/schema.sql`` and executes each statement on the supplied PyMySQL
cursor. Used by both ``tests/conftest.py`` (unit/integration) and
``tests/e2e/conftest.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_SCHEMA_PATH = Path(__file__).parent / "sql" / "schema.sql"


def _split_statements(sql: str) -> list[str]:
    """Strip ``--`` line comments and split on ``;`` into statements."""
    lines = []
    for line in sql.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    return [stmt.strip() for stmt in "\n".join(lines).split(";") if stmt.strip()]


def load_schema(cursor: Any) -> None:
    """Execute every CREATE TABLE statement in ``tests/sql/schema.sql``."""
    for statement in _split_statements(_SCHEMA_PATH.read_text()):
        cursor.execute(statement)

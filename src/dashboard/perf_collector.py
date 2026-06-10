"""Per-request performance metrics accumulator (#214).

Split out of ``perf.py`` (ken #808): the dataclass that collects SQL query timings,
template render time and builds the request summary.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerfCollector:
    """Accumulates performance metrics for a single HTTP request."""

    queries: list[tuple[str, float]] = field(default_factory=list)
    template_name: str | None = None
    template_ms: float = 0.0
    _template_start: float = 0.0

    def record_query(self, name: str, duration_ms: float) -> None:
        """Record a SQL query execution."""
        self.queries.append((name, duration_ms))

    def start_template(self) -> None:
        """Mark the start of template rendering."""
        self._template_start = time.perf_counter()

    def end_template(self, name: str) -> None:
        """Mark the end of template rendering and record duration."""
        self.template_ms = (time.perf_counter() - self._template_start) * 1000
        self.template_name = name

    @property
    def query_count(self) -> int:
        """Return the number of queries executed."""
        return len(self.queries)

    @property
    def sql_total_ms(self) -> float:
        """Return the total SQL execution time in milliseconds."""
        return sum(ms for _, ms in self.queries)

    def summary(
        self,
        total_ms: float,
        response_kb: float,
        route: str,
        method: str,
    ) -> dict[str, Any]:
        """Build a summary dict of all collected metrics."""
        return {
            "method": method,
            "route": route,
            "total_ms": round(total_ms, 1),
            "query_count": self.query_count,
            "sql_total_ms": round(self.sql_total_ms, 1),
            "template_name": self.template_name,
            "template_ms": round(self.template_ms, 1),
            "response_kb": round(response_kb, 1),
            "queries_detail": [(n, round(ms, 1)) for n, ms in self.queries],
        }

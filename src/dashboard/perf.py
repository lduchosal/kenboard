"""Server-side performance monitoring (#214).

Collects per-request metrics (SQL queries, template rendering, total request time) and
creates kenboard tasks when configurable thresholds are exceeded — allowing the board to
feed its own backlog.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from flask import Flask, g, has_request_context, request

import dashboard.db as db
from dashboard.config import Config
from dashboard.logging import get_logger

log = get_logger("perf")

# In-memory cooldown: {route_key: last_task_created_timestamp}
_cooldowns: dict[str, float] = {}
_cooldowns_lock = threading.Lock()


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


def _route_key(method: str, route: str) -> str:
    """Build a stable key for cooldown tracking."""
    return f"{method} {route}"


def _check_thresholds(summary: dict[str, Any]) -> list[str]:
    """Return a list of threshold violations (empty if all OK)."""
    violations: list[str] = []
    if summary["total_ms"] > Config.PERF_BUDGET_MS:
        violations.append(f"budget {summary['total_ms']}ms > {Config.PERF_BUDGET_MS}ms")
    if summary["query_count"] > Config.PERF_MAX_QUERIES:
        violations.append(
            f"queries {summary['query_count']} > {Config.PERF_MAX_QUERIES}"
        )
    if summary["sql_total_ms"] > Config.PERF_MAX_SQL_MS:
        violations.append(
            f"SQL {summary['sql_total_ms']}ms > {Config.PERF_MAX_SQL_MS}ms"
        )
    if summary["response_kb"] > Config.PERF_MAX_RESPONSE_KB:
        violations.append(
            f"response {summary['response_kb']}KB > {Config.PERF_MAX_RESPONSE_KB}KB"
        )
    return violations


def _task_title(method: str, route: str, violations: list[str]) -> str:
    """Build a task title from the route and violations."""
    return f"PERF / {method} {route} / {', '.join(violations)}"


def _task_title_prefix(method: str, route: str) -> str:
    """Build the prefix used for dedup lookup."""
    return f"PERF / {method} {route} /"


def _can_create_task(route_key: str) -> bool:
    """Check cooldown — True if enough time has passed since last creation."""
    now = time.time()
    with _cooldowns_lock:
        last = _cooldowns.get(route_key, 0.0)
        if now - last < Config.PERF_COOLDOWN_S:
            return False
        _cooldowns[route_key] = now
        return True


def _build_description(summary: dict[str, Any], violations: list[str]) -> str:
    """Build a task description with all metrics."""
    lines = [
        f"Performance issue on `{summary['method']} {summary['route']}`.",
        "",
        "## Metriques",
        "",
        f"- **Temps total** : {summary['total_ms']}ms",
        f"- **Queries SQL** : {summary['query_count']} "
        f"({summary['sql_total_ms']}ms cumule)",
        f"- **Template** : {summary['template_name'] or 'N/A'} "
        f"({summary['template_ms']}ms)",
        f"- **Taille reponse** : {summary['response_kb']}KB",
        "",
        "## Violations",
        "",
    ]
    for v in violations:
        lines.append(f"- {v}")
    lines.extend(
        [
            "",
            "## Detail des queries",
            "",
        ]
    )
    for name, ms in summary["queries_detail"]:
        lines.append(f"- `{name}` : {ms}ms")
    lines.extend(
        [
            "",
            "---",
            "",
            "*Tache creee automatiquement par le monitoring de performance (#214).*",
        ]
    )
    return "\n".join(lines)


def _create_perf_task(summary: dict[str, Any], violations: list[str]) -> None:
    """Create a performance task in the kenboard if no duplicate exists."""
    project_id = Config.PERF_PROJECT_ID
    if not project_id:
        return

    route_key = _route_key(summary["method"], summary["route"])
    if not _can_create_task(route_key):
        log.debug("perf_task_cooldown", route=route_key)
        return

    title = _task_title(summary["method"], summary["route"], violations)
    title_prefix = _task_title_prefix(summary["method"], summary["route"])
    description = _build_description(summary, violations)

    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.perf_find_open_task(
            conn, project_id=project_id, title_pattern=f"{title_prefix}%"
        )
        if existing:
            log.debug(
                "perf_task_exists",
                task_id=existing["id"],
                title=existing["title"],
            )
            return

        max_pos = queries.task_max_position(conn, project_id=project_id, status="todo")
        queries.task_create(
            conn,
            project_id=project_id,
            title=title,
            description=description,
            status="todo",
            who=Config.PERF_TASK_WHO,
            due_date=None,
            position=max_pos + 1,
        )
        log.info("perf_task_created", title=title, route=route_key)
    except Exception:
        log.error("perf_task_error", route=route_key, exc_info=True)
        with _cooldowns_lock:
            _cooldowns.pop(route_key, None)
    finally:
        conn.close()


# Paths to skip (static assets, etc.)
_SKIP_PREFIXES = ("/static/", "/favicon")
_SKIP_SUFFIXES = (".css", ".js", ".ico", ".png", ".jpg", ".svg")


def _should_skip() -> bool:
    """Return True if this request should not be instrumented."""
    path = request.path
    return any(path.startswith(p) for p in _SKIP_PREFIXES) or any(
        path.endswith(s) for s in _SKIP_SUFFIXES
    )


def _build_request_summary(response: Any) -> dict[str, Any] | None:
    """Build a performance summary for the current request."""
    start = getattr(request, "_start_time", None)
    if start is None:
        return None
    total_ms = (time.time() - start) * 1000
    route = str(request.url_rule) if request.url_rule else request.path
    method = request.method
    response_kb = len(response.get_data()) / 1024
    return dict(g.perf.summary(total_ms, response_kb, route, method))


def _log_and_evaluate(summary: dict[str, Any]) -> None:
    """Log metrics and create a task if thresholds are exceeded."""
    log.info(
        "perf",
        route=summary["route"],
        method=summary["method"],
        total_ms=summary["total_ms"],
        queries=summary["query_count"],
        sql_ms=summary["sql_total_ms"],
        template=summary["template_name"],
        template_ms=summary["template_ms"],
        response_kb=summary["response_kb"],
    )
    violations = _check_thresholds(summary)
    if violations:
        log.warning(
            "perf_threshold_exceeded",
            violations=violations,
            route=summary["route"],
            method=summary["method"],
            total_ms=summary["total_ms"],
            queries=summary["query_count"],
            sql_ms=summary["sql_total_ms"],
            response_kb=summary["response_kb"],
        )
        _create_perf_task(summary, violations)


def init_perf(app: Flask) -> None:
    """Initialize performance monitoring on the Flask app."""
    if not Config.PERF_ENABLED:
        log.info("perf_disabled")
        return

    from flask import before_render_template, template_rendered

    @app.before_request
    def perf_before() -> None:
        """Initialize perf collector for this request."""
        if _should_skip():
            return
        g.perf = PerfCollector()

    @before_render_template.connect_via(app)
    def perf_before_template(_sender: Any, **kwargs: Any) -> None:
        """Record template render start."""
        if has_request_context() and hasattr(g, "perf"):
            g.perf.start_template()

    @template_rendered.connect_via(app)
    def perf_after_template(_sender: Any, template: Any, **kwargs: Any) -> None:
        """Record template render end."""
        if has_request_context() and hasattr(g, "perf"):
            g.perf.end_template(template.name or "unknown")

    @app.after_request
    def perf_after(response: Any) -> Any:
        """Evaluate performance budget and create a task if exceeded."""
        if not hasattr(g, "perf"):
            return response
        summary = _build_request_summary(response)
        if summary is None:
            return response
        _log_and_evaluate(summary)
        return response

    log.info(
        "perf_enabled",
        budget_ms=Config.PERF_BUDGET_MS,
        max_queries=Config.PERF_MAX_QUERIES,
        max_sql_ms=Config.PERF_MAX_SQL_MS,
        max_response_kb=Config.PERF_MAX_RESPONSE_KB,
        project_id=Config.PERF_PROJECT_ID or "(log only)",
        cooldown_s=Config.PERF_COOLDOWN_S,
    )

"""Page routes — serve dynamic HTML from database."""

from datetime import date, timedelta
from typing import Any

from flask import Blueprint, abort, render_template
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pymysql import Connection

from dashboard import __version__, db
from dashboard.auth_scopes import current_user_can
from dashboard.auth_user import _is_login_disabled
from dashboard.db import Queries
from dashboard.routes.charts import (
    TASKERS_WINDOW_DAYS,
    _build_taskers_daily_chart,
    _build_wiki_sections_per_project_chart,
)
from dashboard.routes.charts_pie import _build_tasks_per_board_pie

bp = Blueprint("pages", __name__)


def _visible_category_ids() -> set[str] | None:
    """Return the set of category ids the current user may read.

    Returns ``None`` to signal "no filtering" (admin, test mode). The caller treats
    ``None`` as "show everything", while an empty set means "show nothing".
    """
    if _is_login_disabled():
        return None
    if not current_user.is_authenticated:
        return set()
    if current_user.is_admin:
        return None
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        rows = list(queries.usr_scopes_get(conn, user_id=current_user.id))
        return {r["category_id"] for r in rows}
    finally:
        conn.close()


COLUMNS = [
    {"id": "todo", "name": "A faire", "color": "var(--todo)"},
    {"id": "doing", "name": "En cours", "color": "var(--cyan)"},
    {"id": "review", "name": "Revue", "color": "var(--purple)"},
    {"id": "done", "name": "Fait", "color": "var(--green)"},
]

COLOR_LIST = [
    ("Orange", "var(--orange)"),
    ("Vert", "var(--green)"),
    ("Bleu", "var(--accent)"),
    ("Violet", "var(--purple)"),
    ("Cyan", "var(--cyan)"),
    ("Rouge", "var(--red)"),
    ("Rose", "var(--todo)"),
    ("Jaune", "var(--yellow)"),
    ("Gris", "var(--dimmed)"),
]


def fmt_date(when_str: str) -> str:
    """Format ISO date to dd.mm."""
    d = date.fromisoformat(when_str)
    return f"{d.day:02d}.{d.month:02d}"


def _filter_by_scope(
    categories: list[dict[str, Any]],
    all_projects: list[dict[str, Any]],
    visible_cat_ids: set[str] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter categories and projects by user scope (#197)."""
    if visible_cat_ids is None:
        return categories, all_projects
    categories = [c for c in categories if c["id"] in visible_cat_ids]
    all_projects = [p for p in all_projects if p["cat_id"] in visible_cat_ids]
    return categories, all_projects


def _build_context(  # noqa: PLR0913 — contexte template : un kwarg par dataset, par design
    categories: list[dict[str, Any]],
    all_projects: list[dict[str, Any]],
    users: list[dict[str, Any]],
    cat_snapshots: dict[str, list[dict[str, Any]]] | None = None,
    prefix: str = "",
    current_cat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build shared template context from loaded data."""
    projects_by_cat: dict[str, list[dict[str, Any]]] = {}
    cat_project_counts: dict[str, int] = {}
    for c in categories:
        cp = [p for p in all_projects if p["cat_id"] == c["id"]]
        projects_by_cat[c["id"]] = cp
        cat_project_counts[c["id"]] = len(cp)

    # CAT_PROJECTS JSON for JS — use pre-computed total if available,
    # fall back to counting loaded tasks for backwards compatibility.
    cat_projects_js: dict[str, list[dict[str, Any]]] = {}
    for c in categories:
        cat_projects_js[c["id"]] = [
            {
                "id": p["id"],
                "name": p["name"],
                "acronym": p.get("acronym", p["name"][:4].upper()),
                "tasks": p.get("total", len(p.get("tasks", []))),
            }
            for p in all_projects
            if p["cat_id"] == c["id"]
        ]

    avatar_colors = {u["name"]: u["color"] for u in users}

    return {
        "prefix": prefix,
        "current_cat": current_cat,
        "categories": categories,
        "projects_by_cat": projects_by_cat,
        "cat_project_counts": cat_project_counts,
        "cat_projects": cat_projects_js,
        "cat_snapshots": cat_snapshots or {},
        "columns": COLUMNS,
        "color_list": COLOR_LIST,
        "avatar_colors": avatar_colors,
        "users": users,
        "version": __version__,
        "fmt_date": fmt_date,
    }


def _attach_index_project_data(
    conn: Connection, queries: Queries, all_projects: list[dict[str, Any]]
) -> None:
    """Attach per-project counts and doing tasks (#226) — two batched queries."""
    counts_rows = list(queries.task_counts_by_project(conn))
    counts = {r["project_id"]: r for r in counts_rows}
    doing_rows = list(queries.task_get_all_doing(conn))
    doing_by_project: dict[str, list[dict[str, Any]]] = {}
    for t in doing_rows:
        doing_by_project.setdefault(t["project_id"], []).append(t)
    for p in all_projects:
        c = counts.get(p["id"], {})
        p["total"] = c.get("total", 0)
        p["done"] = c.get("done", 0)
        p["tasks"] = doing_by_project.get(p["id"], [])


def _doing_tasks_ctx(
    categories: list[dict[str, Any]], all_projects: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Flatten the per-project doing tasks for the dashboard list."""
    cat_by_id = {c["id"]: c for c in categories}
    doing_tasks: list[dict[str, Any]] = []
    for p in all_projects:
        cat = cat_by_id.get(p["cat_id"])
        if not cat:
            continue
        doing_tasks.extend(
            {"task": t, "cat_id": cat["id"], "project_id": p["id"]}
            for t in p.get("tasks", [])
            if t.get("status") == "doing"
        )
    return doing_tasks


@bp.route("/", methods=["GET"])
@login_required
def index() -> ResponseReturnValue:
    """Serve the dashboard with doing tasks and per-project counts (#226)."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        categories = list(queries.cat_get_all(conn))
        all_projects = list(queries.proj_get_all(conn))
        users = list(queries.usr_get_all(conn))
        visible = _visible_category_ids()
        categories, all_projects = _filter_by_scope(categories, all_projects, visible)
        _attach_index_project_data(conn, queries, all_projects)

        cat_snapshots: dict[str, list[dict[str, Any]]] = {}
        for c in categories:
            cat_snapshots[c["id"]] = list(
                queries.burndown_get_by_category(conn, category_id=c["id"], days=60)
            )

        # Daily activity totals across all boards for the engagement line
        # graph (#261). The query returns only days with activity; the
        # template fills missing days with zero so the SVG span is uniform.
        activity_rows = list(queries.activity_daily_total(conn, days=30))
        activity_by_day = {str(r["day"]): r["count"] for r in activity_rows}

        # Per-day taskers chart (#507): grouped bars, one per person per day
        # over the last week, token activity folded into the owning user.
        # Local date wanted: the chart window follows the viewer's calendar
        # day, consistent with the DATE() bucketing in the query (#785).
        today = date.today()  # noqa: DTZ011
        taskers_since = (today - timedelta(days=TASKERS_WINDOW_DAYS - 1)).isoformat()
        taskers_rows = list(queries.activity_daily_by_user(conn, since=taskers_since))
    finally:
        conn.close()

    ctx = _build_context(categories, all_projects, users, cat_snapshots, prefix="/")
    ctx["title"] = "KEN"
    ctx["doing_tasks"] = _doing_tasks_ctx(categories, all_projects)

    # Build a contiguous 30-day series (today minus 29 → today) so the
    # template can render a uniform line graph regardless of which days
    # have data. Days without activity get a 0.
    activity_series = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        activity_series.append(
            {"day": d.isoformat(), "count": activity_by_day.get(str(d), 0)}
        )
    ctx["activity_series"] = activity_series
    ctx["activity_total"] = sum(s["count"] for s in activity_series)
    ctx.update(_build_taskers_daily_chart(taskers_rows, users, today=today))
    ctx.update(_build_tasks_per_board_pie(categories, all_projects))
    return render_template("index.html", **ctx)


@bp.route("/aide", methods=["GET"])
@login_required
def aide() -> ResponseReturnValue:
    """Serve the help page: using ken for bots and the browser extension."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        categories = list(queries.cat_get_all(conn))
        all_projects = list(queries.proj_get_all(conn))
        users = list(queries.usr_get_all(conn))
        visible = _visible_category_ids()
        categories, all_projects = _filter_by_scope(categories, all_projects, visible)
    finally:
        conn.close()

    ctx = _build_context(categories, all_projects, users, prefix="/")
    ctx["title"] = "KEN / Aide"
    return render_template("aide.html", **ctx)


def _attach_category_project_data(
    conn: Connection, queries: Queries, cat_id: str, cat_projects: list[dict[str, Any]]
) -> None:
    """Attach tasks, done/total counts and burndown snapshots to each project.

    Loads tasks and burndown for the whole category in two batched queries instead of
    fanning out per project (#338). Previously a 9-project category did 18 queries (one
    task + one snapshot per project) plus the 4 setup queries → 21 > 20 perf budget.
    """
    all_tasks = list(queries.task_get_by_category(conn, category_id=cat_id))
    tasks_by_project: dict[str, list[dict[str, Any]]] = {}
    for t in all_tasks:
        tasks_by_project.setdefault(t["project_id"], []).append(t)
    snapshot_rows = list(
        queries.burndown_get_for_category_projects(conn, category_id=cat_id, days=60)
    )
    snapshots_by_project: dict[str, list[dict[str, Any]]] = {}
    for s in snapshot_rows:
        # Strip ``project_id`` before grouping — the partials/burndown.html
        # template expects rows shaped like ``burndown_get_by_project``
        # (no project_id field).
        snapshots_by_project.setdefault(s["project_id"], []).append(
            {
                "snapshot_date": s["snapshot_date"],
                "todo": s["todo"],
                "doing": s["doing"],
                "review": s["review"],
                "done": s["done"],
            }
        )
    for p in cat_projects:
        p["tasks"] = tasks_by_project.get(p["id"], [])
        p["done"] = sum(1 for t in p["tasks"] if t["status"] == "done")
        p["total"] = len(p["tasks"])
        p["snapshots"] = snapshots_by_project.get(p["id"], [])


@bp.route("/cat/<cat_id>.html", methods=["GET"])
@login_required
def category(cat_id: str) -> ResponseReturnValue:
    """Serve a category detail page (#221).

    Loads only the projects and tasks for the requested category instead of all
    categories.
    """
    if not current_user_can(cat_id, "read"):
        abort(403)
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        categories = list(queries.cat_get_all(conn))
        all_projects = list(queries.proj_get_all(conn))
        users = list(queries.usr_get_all(conn))
        visible = _visible_category_ids()
        categories, all_projects = _filter_by_scope(categories, all_projects, visible)

        cat = next((c for c in categories if c["id"] == cat_id), None)
        if not cat:
            return "Not found", 404

        cat_projects = [p for p in all_projects if p["cat_id"] == cat_id]
        _attach_category_project_data(conn, queries, cat_id, cat_projects)

        cat_snapshots: dict[str, list[dict[str, Any]]] = {}
        cat_snapshots[cat_id] = list(
            queries.burndown_get_by_category(conn, category_id=cat_id, days=60)
        )

        # Tasks-per-wiki-section grid (#572): one mini-chart per project so
        # the bars carry real signal. The category-wide aggregate (#533)
        # still mixed métiers — finance + server boards live under the
        # same KEN cat — so each board now draws its own card.
        wiki_section_rows = list(
            queries.wiki_section_counts_by_category_per_project(
                conn, category_id=cat_id
            )
        )
    finally:
        conn.close()

    ctx = _build_context(
        categories,
        all_projects,
        users,
        cat_snapshots,
        prefix="/",
        current_cat=cat,
    )
    ctx["title"] = f"KEN / {cat['name']}"
    ctx["cat"] = cat
    ctx["active_projects"] = [
        p for p in cat_projects if p.get("status", "active") == "active"
    ]
    ctx["archived_projects"] = [
        p for p in cat_projects if p.get("status") == "archived"
    ]
    ctx.update(_build_wiki_sections_per_project_chart(wiki_section_rows, cat_projects))
    return render_template("category.html", **ctx)

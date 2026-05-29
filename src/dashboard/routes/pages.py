"""Page routes — serve dynamic HTML from database."""

from datetime import date, datetime, timedelta
from typing import Any

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

import dashboard.db as db
from dashboard import __version__
from dashboard.auth_user import (
    _is_login_disabled,
    admin_required,
    current_user_can,
)

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

# Trailing window (days) for the "biggest ken tasker" leaderboard (#492).
LEADERBOARD_WINDOW_DAYS = 90


def _resolve_activity_author(raw: str, users_by_id: dict[str, str]) -> str | None:
    """Map a raw ``activities.user_name`` principal to a person's display name.

    Session writes already store the display name verbatim; token writes store
    the ``key:<id>:user:<owner>`` principal from the auth middleware, which we
    resolve back to the owning user's name (#492 — the token owner *is* the
    author). Returns ``None`` when no human can be attributed (anonymous
    writes, unowned/legacy ``key:<id>`` tokens, or a since-deleted owner) so
    the caller drops the row from the per-person chart.

    Args:
        raw: The stored ``user_name`` value.
        users_by_id: Map of user id to display name.

    Returns:
        The resolved display name, or ``None`` when unattributable.
    """
    if not raw:
        return None
    if raw.startswith("key:"):
        marker = ":user:"
        idx = raw.find(marker)
        if idx == -1:
            return None
        return users_by_id.get(raw[idx + len(marker) :])
    return raw


def _build_author_leaderboard(
    rows: list[dict[str, Any]],
    users: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build bar geometry for the "biggest ken tasker" leaderboard (#492).

    ``rows`` are ``{user_name, count}`` aggregates from
    ``activity_count_by_user``. Each raw principal is resolved to a person
    (token writes fold into the token owner), counts are summed per person,
    and one vertical bar per person is laid out left-to-right, tallest first
    — a ranking of who drove the most board activity over the window. The
    SVG rects are precomputed here so the template just paints them; the
    name/count labels live in HTML, since the SVG is stretched with
    ``preserveAspectRatio=none`` and text would distort.

    Args:
        rows: Per-principal activity counts over the window.
        users: All users (provides id→name and name→color maps).

    Returns:
        A context dict with ``leaderboard_bars``, ``leaderboard_total`` and
        the SVG viewBox dimensions.
    """
    w, h = 760.0, 150.0
    empty: dict[str, Any] = {
        "leaderboard_bars": [],
        "leaderboard_total": 0,
        "leaderboard_vb_w": w,
        "leaderboard_vb_h": h,
    }
    users_by_id = {u["id"]: u["name"] for u in users}
    color_by_name = {u["name"]: u["color"] for u in users}

    totals_by_person: dict[str, int] = {}
    for r in rows:
        person = _resolve_activity_author(str(r["user_name"]), users_by_id)
        if person is None:
            continue
        totals_by_person[person] = totals_by_person.get(person, 0) + int(r["count"])

    if not totals_by_person:
        return empty

    # Tallest (most active) first — the leaderboard is a ranking.
    persons = sorted(totals_by_person, key=lambda p: (-totals_by_person[p], p))
    default_color = "var(--dimmed)"
    pad_top, pad_bottom = 8.0, 4.0
    plot_h = h - pad_top - pad_bottom
    band = w / len(persons)
    bar_w = band * 0.6
    max_count = max(totals_by_person.values())

    bars: list[dict[str, Any]] = []
    for i, person in enumerate(persons):
        cnt = totals_by_person[person]
        bar_h = (cnt / max_count) * plot_h
        x = i * band + (band - bar_w) / 2
        bars.append(
            {
                "x": round(x, 1),
                "y": round(h - pad_bottom - bar_h, 1),
                "w": round(bar_w, 1),
                "h": round(bar_h, 1),
                "color": color_by_name.get(person, default_color),
                "person": person,
                "count": cnt,
            }
        )

    return {
        "leaderboard_bars": bars,
        "leaderboard_total": sum(totals_by_person.values()),
        "leaderboard_window_days": LEADERBOARD_WINDOW_DAYS,
        "leaderboard_vb_w": w,
        "leaderboard_vb_h": h,
    }


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


def _build_context(
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


@bp.route("/", methods=["GET"])
@login_required
def index() -> Any:
    """Serve the dashboard with doing tasks and per-project counts (#226)."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        categories = list(queries.cat_get_all(conn))
        all_projects = list(queries.proj_get_all(conn))
        users = list(queries.usr_get_all(conn))
        visible = _visible_category_ids()
        categories, all_projects = _filter_by_scope(categories, all_projects, visible)

        # Per-project counts in one query instead of loading all tasks
        counts_rows = list(queries.task_counts_by_project(conn))
        counts = {r["project_id"]: r for r in counts_rows}
        # Doing tasks only
        doing_rows = list(queries.task_get_all_doing(conn))
        doing_by_project: dict[str, list[dict[str, Any]]] = {}
        for t in doing_rows:
            doing_by_project.setdefault(t["project_id"], []).append(t)

        for p in all_projects:
            c = counts.get(p["id"], {})
            p["total"] = c.get("total", 0)
            p["done"] = c.get("done", 0)
            p["tasks"] = doing_by_project.get(p["id"], [])

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

        # "Biggest ken tasker" leaderboard (#492): one bar per person, their
        # activity count over the window, token activity folded into the
        # owning user.
        today = date.today()
        leaderboard_since = (
            today - timedelta(days=LEADERBOARD_WINDOW_DAYS)
        ).isoformat()
        leaderboard_rows = list(
            queries.activity_count_by_user(conn, since=leaderboard_since)
        )
    finally:
        conn.close()

    ctx = _build_context(categories, all_projects, users, cat_snapshots, prefix="/")
    ctx["title"] = "KEN"

    cat_by_id = {c["id"]: c for c in categories}
    doing_tasks: list[dict[str, Any]] = []
    for p in all_projects:
        cat = cat_by_id.get(p["cat_id"])
        if not cat:
            continue
        for t in p.get("tasks", []):
            if t.get("status") == "doing":
                doing_tasks.append(
                    {"task": t, "cat_id": cat["id"], "project_id": p["id"]}
                )
    ctx["doing_tasks"] = doing_tasks

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
    ctx.update(_build_author_leaderboard(leaderboard_rows, users))
    return render_template("index.html", **ctx)


@bp.route("/admin/users", methods=["GET"])
@login_required
def admin_users() -> Any:
    """Serve the user management admin page (#225).

    No tasks or burndown needed — only categories, users, and scopes.
    """
    admin_required()
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        categories = list(queries.cat_get_all(conn))
        all_projects = list(queries.proj_get_all(conn))
        users = list(queries.usr_get_all(conn))
        for u in users:
            u["scopes"] = [
                {"category_id": s["category_id"], "scope": s["scope"]}
                for s in queries.usr_scopes_get(conn, user_id=u["id"])
            ]
    finally:
        conn.close()

    ctx = _build_context(categories, all_projects, users, prefix="/")
    ctx["title"] = "KEN / Utilisateurs"
    ctx["all_categories"] = categories
    return render_template("admin_users.html", **ctx)


@bp.route("/admin/keys", methods=["GET"])
@login_required
def admin_keys() -> Any:
    """Serve the API keys management admin page (#223).

    No tasks or burndown needed — only categories, projects, users, and API keys with
    their scopes.
    """
    admin_required()
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        categories = list(queries.cat_get_all(conn))
        all_projects = list(queries.proj_get_all(conn))
        users = list(queries.usr_get_all(conn))
        api_keys = list(queries.key_get_all(conn))
        # Batch the scopes lookup into a single round-trip (#257). Previously
        # each key triggered its own ``key_scopes_get`` call — for 20 keys
        # that's 20 queries on top of the 5 used by this route, tripping
        # the perf budget at 25 > 20. Now: one query, group in Python.
        scopes_rows = list(queries.key_scopes_get_all(conn))
        scopes_by_key: dict[str, list[dict[str, str]]] = {}
        for s in scopes_rows:
            scopes_by_key.setdefault(s["api_key_id"], []).append(
                {"project_id": s["project_id"], "scope": s["scope"]}
            )
        for k in api_keys:
            k["scopes"] = scopes_by_key.get(k["id"], [])
    finally:
        conn.close()

    ctx = _build_context(categories, all_projects, users, prefix="/")
    ctx["title"] = "KEN / Cles API"
    ctx["api_keys"] = api_keys
    ctx["projects"] = all_projects
    ctx["key_users"] = users
    ctx["now"] = datetime.now()
    return render_template("admin_keys.html", **ctx)


@bp.route("/admin/board", methods=["GET"])
@login_required
def admin_board() -> Any:
    """Serve the category/project management admin page (#224).

    No tasks or burndown needed — only categories and projects.
    """
    admin_required()
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        categories = list(queries.cat_get_all(conn))
        all_projects = list(queries.proj_get_all(conn))
        users = list(queries.usr_get_all(conn))
    finally:
        conn.close()

    ctx = _build_context(categories, all_projects, users, prefix="/")
    ctx["title"] = "KEN / Board"
    ctx["all_categories"] = categories
    ctx["all_projects"] = all_projects
    return render_template("admin_board.html", **ctx)


@bp.route("/cat/<cat_id>.html", methods=["GET"])
@login_required
def category(cat_id: str) -> Any:
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

        # Load tasks and burndown for the whole category in two batched
        # queries instead of fanning out per project (#338). Previously a
        # 9-project category did 18 queries (one task + one snapshot per
        # project) plus the 4 setup queries → 21 > 20 perf budget.
        cat_projects = [p for p in all_projects if p["cat_id"] == cat_id]
        all_tasks = list(queries.task_get_by_category(conn, category_id=cat_id))
        tasks_by_project: dict[str, list[dict[str, Any]]] = {}
        for t in all_tasks:
            tasks_by_project.setdefault(t["project_id"], []).append(t)
        snapshot_rows = list(
            queries.burndown_get_for_category_projects(
                conn, category_id=cat_id, days=60
            )
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

        cat_snapshots: dict[str, list[dict[str, Any]]] = {}
        cat_snapshots[cat_id] = list(
            queries.burndown_get_by_category(conn, category_id=cat_id, days=60)
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
    return render_template("category.html", **ctx)

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

# Trailing window (days) for the per-day taskers chart (#507).
TASKERS_WINDOW_DAYS = 7


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


_FR_WEEKDAYS = ("lun", "mar", "mer", "jeu", "ven", "sam", "dim")


def _build_taskers_daily_chart(
    rows: list[dict[str, Any]],
    users: list[dict[str, Any]],
    *,
    today: date,
    days: int = TASKERS_WINDOW_DAYS,
) -> dict[str, Any]:
    """Build grouped-bar geometry for the per-day taskers chart (#507).

    ``rows`` are ``{day, user_name, count}`` aggregates from
    ``activity_daily_by_user``. Each raw principal is resolved to a person
    (token writes fold into the owner, #492), counts are bucketed per
    (day, person), and within each of the last ``days`` days one bar per
    active person is laid out side by side — a per-day comparison of who did
    the most. The SVG rects are precomputed here; day labels and the person
    legend live in HTML since the SVG is stretched with
    ``preserveAspectRatio=none`` and text would distort.

    Args:
        rows: Per-(day, principal) activity counts.
        users: All users (provides id→name and name→color maps).
        today: Anchor date for the trailing window (injected for testing).
        days: Number of days to render, ending today.

    Returns:
        A context dict with ``taskers_bars``, ``taskers_axis``,
        ``taskers_legend``, ``taskers_total`` and the SVG viewBox dimensions.
    """
    w, h = 760.0, 150.0
    empty: dict[str, Any] = {
        "taskers_bars": [],
        "taskers_axis": [],
        "taskers_legend": [],
        "taskers_total": 0,
        "taskers_vb_w": w,
        "taskers_vb_h": h,
    }
    users_by_id = {u["id"]: u["name"] for u in users}
    color_by_name = {u["name"]: u["color"] for u in users}

    day_seq = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    day_keys = [d.isoformat() for d in day_seq]

    per_day: dict[str, dict[str, int]] = {k: {} for k in day_keys}
    totals_by_person: dict[str, int] = {}
    for r in rows:
        key = str(r["day"])
        if key not in per_day:
            continue
        person = _resolve_activity_author(str(r["user_name"]), users_by_id)
        if person is None:
            continue
        cnt = int(r["count"])
        per_day[key][person] = per_day[key].get(person, 0) + cnt
        totals_by_person[person] = totals_by_person.get(person, 0) + cnt

    if not totals_by_person:
        return empty

    # Stable person order (most active first) shared across every day so a
    # person keeps the same slot + colour across the week.
    persons = sorted(totals_by_person, key=lambda p: (-totals_by_person[p], p))
    default_color = "var(--dimmed)"
    pad_top, pad_bottom = 8.0, 4.0
    plot_h = h - pad_top - pad_bottom
    band = w / days
    group_w = band * 0.82
    slot_w = group_w / len(persons)
    bar_w = slot_w * 0.85
    max_count = max(max(d.values()) for d in per_day.values() if d)

    bars: list[dict[str, Any]] = []
    for di, key in enumerate(day_keys):
        for pj, person in enumerate(persons):
            cnt = per_day[key].get(person, 0)
            if cnt == 0:
                continue
            bar_h = (cnt / max_count) * plot_h
            x = di * band + (band - group_w) / 2 + pj * slot_w + (slot_w - bar_w) / 2
            bars.append(
                {
                    "x": round(x, 1),
                    "y": round(h - pad_bottom - bar_h, 1),
                    "w": round(bar_w, 1),
                    "h": round(bar_h, 1),
                    "color": color_by_name.get(person, default_color),
                    "person": person,
                    "day": key,
                    "count": cnt,
                }
            )

    axis = [{"label": "%s %d" % (_FR_WEEKDAYS[d.weekday()], d.day)} for d in day_seq]
    legend = [
        {
            "person": p,
            "color": color_by_name.get(p, default_color),
            "count": totals_by_person[p],
        }
        for p in persons
    ]
    return {
        "taskers_bars": bars,
        "taskers_axis": axis,
        "taskers_legend": legend,
        "taskers_total": sum(totals_by_person.values()),
        "taskers_window_days": days,
        "taskers_vb_w": w,
        "taskers_vb_h": h,
    }


def _build_wiki_sections_chart(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build horizontal-bar data for the tasks-per-wiki-section chart (#516).

    ``rows`` are ``{section_path, count}`` aggregates from ``wiki_section_counts``
    (already busiest-first). Each bar's width is its share of the busiest section so the
    longest bar fills the track.
    """
    counts = [(str(r["section_path"]), int(r["count"])) for r in rows]
    max_count = max((c for _, c in counts), default=0)
    sections = [
        {
            "section": name,
            "count": cnt,
            "pct": round(100 * cnt / max_count, 1) if max_count else 0,
        }
        for name, cnt in counts
    ]
    return {
        "wiki_sections": sections,
        "wiki_sections_total": sum(c for _, c in counts),
    }


def _build_wiki_sections_per_category_chart(
    rows: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    *,
    top_n: int = 6,
) -> dict[str, Any]:
    """Build per-category mini-chart data for the dashboard (#540).

    ``rows`` are ``{category_id, section_path, count}`` aggregates from
    ``wiki_section_counts_grouped`` (already ordered by category, then count desc).
    ``categories`` is the visible-to-user list — categories without classifications are
    dropped, the rest follow ``categories`` order (== the user's preferred category
    order). Each category card shows its top ``top_n`` sections, scaled to its own
    busiest section so bars stay comparable within a card.

    Args:
        rows: Per-(category, section) classification counts.
        categories: Visible categories in display order.
        top_n: Maximum number of section rows per mini-card.

    Returns:
        A context dict with ``wiki_by_category`` (list of cards, each with
        ``cat``, ``sections``, ``total``) and ``wiki_by_category_total``.
    """
    by_cat: dict[str, list[tuple[str, int]]] = {}
    for r in rows:
        cid = str(r["category_id"])
        by_cat.setdefault(cid, []).append((str(r["section_path"]), int(r["count"])))

    cards: list[dict[str, Any]] = []
    grand_total = 0
    for c in categories:
        cat_rows = by_cat.get(c["id"], [])
        if not cat_rows:
            continue
        max_count = cat_rows[0][1]
        sections = [
            {
                "section": name,
                "count": cnt,
                "pct": round(100 * cnt / max_count, 1) if max_count else 0,
            }
            for name, cnt in cat_rows[:top_n]
        ]
        total = sum(cnt for _, cnt in cat_rows)
        grand_total += total
        cards.append({"cat": c, "sections": sections, "total": total})
    return {
        "wiki_by_category": cards,
        "wiki_by_category_total": grand_total,
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

        # Per-day taskers chart (#507): grouped bars, one per person per day
        # over the last week, token activity folded into the owning user.
        today = date.today()
        taskers_since = (today - timedelta(days=TASKERS_WINDOW_DAYS - 1)).isoformat()
        taskers_rows = list(queries.activity_daily_by_user(conn, since=taskers_since))

        # Per-category wiki mini-chart (#540): scoped signal on the home,
        # one small card per visible category. The detailed per-section
        # view stays on /cat/<id>.html (#533).
        wiki_grouped_rows = list(queries.wiki_section_counts_grouped(conn))
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
    ctx.update(_build_taskers_daily_chart(taskers_rows, users, today=today))
    ctx.update(_build_wiki_sections_per_category_chart(wiki_grouped_rows, categories))
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


@bp.route("/aide", methods=["GET"])
@login_required
def aide() -> Any:
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

        # Tasks-per-wiki-section chart (#533): scoped to this category's
        # projects so the bars carry real signal — the global aggregate
        # (formerly on the dashboard, #516) mixed sections from unrelated
        # boards (#532).
        wiki_section_rows = list(
            queries.wiki_section_counts_by_category(conn, category_id=cat_id)
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
    ctx.update(_build_wiki_sections_chart(wiki_section_rows))
    return render_template("category.html", **ctx)

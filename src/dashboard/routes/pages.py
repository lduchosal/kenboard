"""Page routes — serve dynamic HTML from database."""

from datetime import date, datetime
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

    Returns ``None`` to signal "no filtering" (admin, test mode). The
    caller treats ``None`` as "show everything", while an empty set
    means "show nothing".
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
        for k in api_keys:
            scopes = list(queries.key_scopes_get(conn, api_key_id=k["id"]))
            k["scopes"] = [
                {"project_id": s["project_id"], "scope": s["scope"]} for s in scopes
            ]
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

        # Load tasks and burndown only for this category's projects
        cat_projects = [p for p in all_projects if p["cat_id"] == cat_id]
        for p in cat_projects:
            p["tasks"] = list(queries.task_get_by_project(conn, project_id=p["id"]))
            p["done"] = len([t for t in p["tasks"] if t["status"] == "done"])
            p["total"] = len(p["tasks"])
            p["snapshots"] = list(
                queries.burndown_get_by_project(conn, project_id=p["id"], days=60)
            )

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

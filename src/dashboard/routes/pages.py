"""Page routes — serve dynamic HTML from database."""

from datetime import date, datetime
from typing import Any

from flask import Blueprint, render_template
from flask_login import login_required

import dashboard.db as db
from dashboard import __version__
from dashboard.auth_user import admin_required

bp = Blueprint("pages", __name__)

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


def _load_all_data() -> dict[str, Any]:
    """Load all data from the database."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        categories = list(queries.cat_get_all(conn))
        all_projects = list(queries.proj_get_all(conn))
        users = list(queries.usr_get_all(conn))
        # Attach tasks to each project
        for p in all_projects:
            p["tasks"] = list(queries.task_get_by_project(conn, project_id=p["id"]))
            p["done"] = len([t for t in p["tasks"] if t["status"] == "done"])
            p["total"] = len(p["tasks"])
            # Build burndown from task counts (simple: just remaining per week placeholder)
            remaining = p["total"] - p["done"]
            p["actual"] = [remaining] if remaining >= 0 else [0]
            p["ideal"] = [p["total"]]
        return {
            "categories": categories,
            "all_projects": all_projects,
            "users": users,
        }
    finally:
        conn.close()


def _build_context(
    data: dict[str, Any],
    prefix: str = "",
    current_cat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build shared template context from database data."""
    categories = data["categories"]
    all_projects = data["all_projects"]

    projects_by_cat: dict[str, list[dict[str, Any]]] = {}
    cat_project_counts: dict[str, int] = {}
    for c in categories:
        cp = [p for p in all_projects if p["cat_id"] == c["id"]]
        projects_by_cat[c["id"]] = cp
        cat_project_counts[c["id"]] = len(cp)

    # CAT_PROJECTS JSON for JS
    cat_projects_js: dict[str, list[dict[str, Any]]] = {}
    for c in categories:
        cat_projects_js[c["id"]] = [
            {
                "id": p["id"],
                "name": p["name"],
                "acronym": p.get("acronym", p["name"][:4].upper()),
                "tasks": len(p.get("tasks", [])),
            }
            for p in all_projects
            if p["cat_id"] == c["id"]
        ]

    def aggregate_burndown(project_list: list[dict[str, Any]]) -> list[int]:
        """Aggregate burndown actual values."""
        if not project_list:
            return [0]
        length = len(project_list[0].get("actual", [0]))
        return [
            sum(p.get("actual", [0])[i] for p in project_list) for i in range(length)
        ]

    users = data.get("users", [])
    avatar_colors = {u["name"]: u["color"] for u in users}

    return {
        "prefix": prefix,
        "current_cat": current_cat,
        "categories": categories,
        "projects_by_cat": projects_by_cat,
        "cat_project_counts": cat_project_counts,
        "cat_projects": cat_projects_js,
        "columns": COLUMNS,
        "color_list": COLOR_LIST,
        "avatar_colors": avatar_colors,
        "users": users,
        "version": __version__,
        "fmt_date": fmt_date,
        "aggregate_burndown": aggregate_burndown,
    }


@bp.route("/", methods=["GET"])
@login_required
def index() -> Any:
    """Serve the dashboard."""
    data = _load_all_data()
    ctx = _build_context(data, prefix="/")
    ctx["title"] = "KEN"
    # Flat overview of all "doing" tasks across every project, with the
    # cat/project context needed to build deep links back to the kanban.
    cat_by_id = {c["id"]: c for c in data["categories"]}
    doing_tasks: list[dict[str, Any]] = []
    for p in data["all_projects"]:
        cat = cat_by_id.get(p["cat_id"])
        if not cat:
            continue
        for t in p.get("tasks", []):
            if t.get("status") == "doing":
                doing_tasks.append(
                    {
                        "task": t,
                        "cat_id": cat["id"],
                        "project_id": p["id"],
                    }
                )
    ctx["doing_tasks"] = doing_tasks
    return render_template("index.html", **ctx)


@bp.route("/admin/users", methods=["GET"])
@login_required
def admin_users() -> Any:
    """Serve the user management admin page."""
    admin_required()
    data = _load_all_data()
    ctx = _build_context(data, prefix="/")
    ctx["title"] = "KEN / Utilisateurs"
    return render_template("admin_users.html", **ctx)


@bp.route("/admin/keys", methods=["GET"])
@login_required
def admin_keys() -> Any:
    """Serve the API keys management admin page."""
    admin_required()
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        api_keys = list(queries.key_get_all(conn))
        for k in api_keys:
            scopes = list(queries.key_scopes_get(conn, api_key_id=k["id"]))
            k["scopes"] = [
                {"project_id": s["project_id"], "scope": s["scope"]} for s in scopes
            ]
    finally:
        conn.close()
    data = _load_all_data()
    ctx = _build_context(data, prefix="/")
    ctx["title"] = "KEN / Cles API"
    ctx["api_keys"] = api_keys
    ctx["projects"] = data["all_projects"]
    # Users list powers the "owner" column in the admin_keys table (#110).
    ctx["key_users"] = data["users"]
    ctx["now"] = datetime.now()
    return render_template("admin_keys.html", **ctx)


@bp.route("/admin/board", methods=["GET"])
@login_required
def admin_board() -> Any:
    """Serve the category/project management admin page (#162)."""
    admin_required()
    data = _load_all_data()
    ctx = _build_context(data, prefix="/")
    ctx["title"] = "KEN / Board"
    ctx["all_categories"] = data["categories"]
    ctx["all_projects"] = data["all_projects"]
    return render_template("admin_board.html", **ctx)


@bp.route("/cat/<cat_id>.html", methods=["GET"])
@login_required
def category(cat_id: str) -> Any:
    """Serve a category detail page."""
    data = _load_all_data()
    cat = next((c for c in data["categories"] if c["id"] == cat_id), None)
    if not cat:
        return "Not found", 404
    ctx = _build_context(data, prefix="/", current_cat=cat)
    cp = [p for p in data["all_projects"] if p["cat_id"] == cat_id]
    ctx["title"] = f"KEN / {cat['name']}"
    ctx["cat"] = cat
    ctx["active_projects"] = [p for p in cp if p.get("status", "active") == "active"]
    ctx["archived_projects"] = [p for p in cp if p.get("status") == "archived"]
    return render_template("category.html", **ctx)

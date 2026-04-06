"""Page routes — serve dynamic HTML from database."""

import json
from datetime import date
from typing import Any

from flask import Blueprint, render_template

import dashboard.db as db

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

AVATAR_COLORS = {
    "Q": "#0969da",
    "Alice": "#8250df",
    "Bob": "#bf8700",
    "Claire": "#1a7f37",
}


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
        # Attach tasks to each project
        for p in all_projects:
            p["tasks"] = list(
                queries.task_get_by_project(conn, project_id=p["id"])
            )
            p["done"] = len([t for t in p["tasks"] if t["status"] == "done"])
            p["total"] = len(p["tasks"])
            # Build burndown from task counts (simple: just remaining per week placeholder)
            remaining = p["total"] - p["done"]
            p["actual"] = [remaining] if remaining >= 0 else [0]
            p["ideal"] = [p["total"]]
        return {
            "categories": categories,
            "all_projects": all_projects,
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

    return {
        "prefix": prefix,
        "current_cat": current_cat,
        "categories": categories,
        "projects_by_cat": projects_by_cat,
        "cat_project_counts": cat_project_counts,
        "cat_projects_json": json.dumps(cat_projects_js),
        "columns": COLUMNS,
        "color_list": COLOR_LIST,
        "avatar_colors": AVATAR_COLORS,
        "fmt_date": fmt_date,
        "aggregate_burndown": aggregate_burndown,
    }


@bp.route("/")
def index() -> Any:
    """Serve the dashboard."""
    data = _load_all_data()
    ctx = _build_context(data, prefix="/")
    ctx["title"] = "Dashboard"
    return render_template("index.html", **ctx)


@bp.route("/cat/<cat_id>.html")
def category(cat_id: str) -> Any:
    """Serve a category detail page."""
    data = _load_all_data()
    cat = next((c for c in data["categories"] if c["id"] == cat_id), None)
    if not cat:
        return "Not found", 404
    ctx = _build_context(data, prefix="/", current_cat=cat)
    cp = [p for p in data["all_projects"] if p["cat_id"] == cat_id]
    ctx["title"] = cat["name"]
    ctx["cat"] = cat
    ctx["active_projects"] = [p for p in cp if p.get("status", "active") == "active"]
    ctx["archived_projects"] = [p for p in cp if p.get("status") == "archived"]
    return render_template("category.html", **ctx)

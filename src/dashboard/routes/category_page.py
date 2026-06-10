"""Category detail page (#221) — projects, tasks, burndown and wiki cards.

Split out of ``routes/pages.py`` (ken #808); registers on the same ``pages`` blueprint,
imported for side effects by ``app._register_blueprints``.
"""

from typing import Any

from flask import abort, render_template
from flask.typing import ResponseReturnValue
from flask_login import login_required
from pymysql import Connection

from dashboard import db
from dashboard.auth_scopes import current_user_can
from dashboard.db import Queries
from dashboard.routes.charts import _build_wiki_sections_per_project_chart
from dashboard.routes.pages import (
    _build_context,
    _filter_by_scope,
    _visible_category_ids,
    bp,
)


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


def _category_rows(
    conn: Connection, queries: Queries, cat_id: str
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Burndown snapshots + per-project wiki-section counts of the category.

    The wiki grid (#572) draws one mini-chart per project — the category-wide aggregate
    (#533) still mixed métiers under the same cat.
    """
    cat_snapshots = {
        cat_id: list(
            queries.burndown_get_by_category(conn, category_id=cat_id, days=60)
        )
    }
    wiki_section_rows = list(
        queries.wiki_section_counts_by_category_per_project(conn, category_id=cat_id)
    )
    return cat_snapshots, wiki_section_rows


def _category_ctx(
    cat: dict[str, Any],
    cat_projects: list[dict[str, Any]],
    wiki_section_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Category-specific template context: title, project lists, wiki cards."""
    ctx: dict[str, Any] = {
        "title": f"KEN / {cat['name']}",
        "cat": cat,
        "active_projects": [
            p for p in cat_projects if p.get("status", "active") == "active"
        ],
        "archived_projects": [p for p in cat_projects if p.get("status") == "archived"],
    }
    ctx.update(_build_wiki_sections_per_project_chart(wiki_section_rows, cat_projects))
    return ctx


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

        cat_snapshots, wiki_section_rows = _category_rows(conn, queries, cat_id)
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
    ctx.update(_category_ctx(cat, cat_projects, wiki_section_rows))
    return render_template("category.html", **ctx)

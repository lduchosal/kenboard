"""Admin HTML pages — users, API keys and board management.

Split out of ``routes/pages.py`` (ken #806); the routes register on the same ``pages``
blueprint, imported for side effects by ``app._register_blueprints``.
"""

from datetime import datetime

from flask import render_template
from flask.typing import ResponseReturnValue
from flask_login import login_required

from dashboard import db
from dashboard.auth_user import admin_required
from dashboard.routes.pages import _build_context, bp


@bp.route("/admin/users", methods=["GET"])
@login_required
def admin_users() -> ResponseReturnValue:
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
def admin_keys() -> ResponseReturnValue:
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
    # Naive local now wanted: the template compares it to expires_at, a naive
    # local DATETIME entered via the admin form and stored as-is (#785).
    ctx["now"] = datetime.now()  # noqa: DTZ005
    return render_template("admin_keys.html", **ctx)


@bp.route("/admin/board", methods=["GET"])
@login_required
def admin_board() -> ResponseReturnValue:
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

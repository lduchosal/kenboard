"""Project API routes."""

from typing import Any

from flask import Blueprint, current_app, g, jsonify, request
from flask_login import current_user

import dashboard.db as db
from dashboard.auth_user import (
    _is_api_key_principal,
    current_user_can,
    current_user_can_project,
)
from dashboard.models.project import Project, ProjectCreate, ProjectUpdate

bp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")


def _should_filter_for_current_user() -> bool:
    """True when list endpoints should be filtered to the current user's scopes."""
    if current_app.config.get("LOGIN_DISABLED"):
        return False
    if _is_api_key_principal(g.get("api_auth_principal")):
        return False
    if not current_user.is_authenticated:
        return False
    return not current_user.is_admin


@bp.route("", methods=["GET"])
def list_projects() -> Any:
    """List projects, optionally filtered by category.

    Non-admin cookie users only see projects in categories they have a
    scope on. If ``?cat=X`` is passed, the user must have at least read
    access on X or the response is a 403.
    """
    cat_id = request.args.get("cat")
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        if cat_id:
            if not current_user_can(cat_id, "read"):
                return jsonify({"error": "forbidden"}), 403
            rows = list(queries.proj_get_by_cat(conn, cat_id=cat_id))
        elif _should_filter_for_current_user():
            rows = list(queries.proj_list_for_user(conn, user_id=current_user.id))
        else:
            rows = list(queries.proj_get_all(conn))
        return jsonify([Project(**row).model_dump() for row in rows])
    finally:
        conn.close()


@bp.route("", methods=["POST"])
def create_project() -> Any:
    """Create a new project (write scope on the target category required)."""
    payload = request.get_json() or {}
    target_cat = payload.get("cat")
    if target_cat and not current_user_can(target_cat, "write"):
        return jsonify({"error": "forbidden"}), 403
    data = ProjectCreate(**payload)
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        max_pos = queries.proj_max_position_in_cat(conn, cat_id=data.cat)
        import uuid

        proj_id = str(uuid.uuid4())
        queries.proj_create(
            conn,
            id=proj_id,
            cat_id=data.cat,
            name=data.name,
            acronym=data.acronym.upper(),
            status=data.status,
            position=max_pos + 1,
            default_who=data.default_who,
        )
        row = queries.proj_get_by_id(conn, id=proj_id)
        return jsonify(Project(**row).model_dump()), 201
    finally:
        conn.close()


@bp.route("/<proj_id>", methods=["PATCH"])
def update_project(proj_id: str) -> Any:
    """Update a project (write scope on its owning category required)."""
    if not current_user_can_project(proj_id, "write"):
        return jsonify({"error": "forbidden"}), 403
    data = ProjectUpdate(**request.get_json())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.proj_get_by_id(conn, id=proj_id)
        if not existing:
            return jsonify({"error": "Not found"}), 404
        # If the project is being moved to a different category, the user
        # must also have write on the target category.
        if (
            data.cat
            and data.cat != existing["cat_id"]
            and not current_user_can(data.cat, "write")
        ):
            return jsonify({"error": "forbidden"}), 403
        queries.proj_update(
            conn,
            id=proj_id,
            name=data.name or existing["name"],
            acronym=(data.acronym or existing["acronym"]).upper(),
            cat_id=data.cat or existing["cat_id"],
            status=data.status or existing["status"],
            default_who=(
                data.default_who
                if data.default_who is not None
                else existing["default_who"]
            ),
        )
        # Reorder sibling projects if requested
        if data.project_order:
            for i, pid in enumerate(data.project_order):
                queries.proj_update_position(conn, id=pid, position=i)
        row = queries.proj_get_by_id(conn, id=proj_id)
        return jsonify(Project(**row).model_dump())
    finally:
        conn.close()


@bp.route("/<proj_id>", methods=["DELETE"])
def delete_project(proj_id: str) -> Any:
    """Delete a project (only if no tasks, write scope on its category)."""
    if not current_user_can_project(proj_id, "write"):
        return jsonify({"error": "forbidden"}), 403
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        count = queries.proj_count_tasks(conn, project_id=proj_id)
        if count > 0:
            return jsonify({"error": "Cannot delete project with tasks"}), 400
        queries.proj_delete(conn, id=proj_id)
        return "", 204
    finally:
        conn.close()

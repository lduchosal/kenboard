"""Project API routes."""

from flask import Blueprint, jsonify, request

from dashboard.db import get_connection, load_queries
from dashboard.models.project import Project, ProjectCreate, ProjectUpdate

bp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")


@bp.route("", methods=["GET"])
def list_projects():
    """List projects, optionally filtered by category."""
    cat_id = request.args.get("cat")
    conn = get_connection()
    queries = load_queries()
    try:
        if cat_id:
            rows = list(queries.proj_get_by_cat(conn, cat_id=cat_id))
        else:
            rows = list(queries.proj_get_all(conn))
        return jsonify([Project(**row).model_dump() for row in rows])
    finally:
        conn.close()


@bp.route("", methods=["POST"])
def create_project():
    """Create a new project."""
    data = ProjectCreate(**request.get_json())
    conn = get_connection()
    queries = load_queries()
    try:
        max_pos = queries.proj_max_position_in_cat(conn, cat_id=data.cat)
        proj_id = data.name.lower().replace(" ", "-")
        queries.proj_create(
            conn,
            id=proj_id,
            cat_id=data.cat,
            name=data.name,
            acronym=data.acronym.upper(),
            status=data.status,
            position=max_pos + 1,
        )
        row = queries.proj_get_by_id(conn, id=proj_id)
        return jsonify(Project(**row).model_dump()), 201
    finally:
        conn.close()


@bp.route("/<proj_id>", methods=["PATCH"])
def update_project(proj_id: str):
    """Update a project."""
    data = ProjectUpdate(**request.get_json())
    conn = get_connection()
    queries = load_queries()
    try:
        existing = queries.proj_get_by_id(conn, id=proj_id)
        if not existing:
            return jsonify({"error": "Not found"}), 404
        queries.proj_update(
            conn,
            id=proj_id,
            name=data.name or existing["name"],
            acronym=(data.acronym or existing["acronym"]).upper(),
            cat_id=data.cat or existing["cat_id"],
            status=data.status or existing["status"],
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
def delete_project(proj_id: str):
    """Delete a project (only if no tasks)."""
    conn = get_connection()
    queries = load_queries()
    try:
        count = queries.proj_count_tasks(conn, project_id=proj_id)
        if count > 0:
            return jsonify({"error": "Cannot delete project with tasks"}), 400
        queries.proj_delete(conn, id=proj_id)
        return "", 204
    finally:
        conn.close()

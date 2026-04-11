"""Task API routes."""

from typing import Any

from flask import Blueprint, jsonify, request

import dashboard.db as db
from dashboard.models.task import Task, TaskCreate, TaskUpdate

bp = Blueprint("tasks", __name__, url_prefix="/api/v1/tasks")


@bp.route("", methods=["GET"])
def list_tasks() -> Any:
    """List tasks for a project."""
    project_id = request.args.get("project")
    if not project_id:
        return jsonify({"error": "project parameter required"}), 400
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        rows = list(queries.task_get_by_project(conn, project_id=project_id))
        return jsonify([Task(**row).model_dump(mode="json") for row in rows])
    finally:
        conn.close()


@bp.route("/<int:task_id>", methods=["GET"])
def get_task(task_id: int) -> Any:
    """Get a single task by id (#168)."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        row = queries.task_get_by_id(conn, id=task_id)
        if not row:
            return jsonify({"error": "Not found"}), 404
        return jsonify(Task(**row).model_dump(mode="json"))
    finally:
        conn.close()


@bp.route("", methods=["POST"])
def create_task() -> Any:
    """Create a new task."""
    data = TaskCreate(**request.get_json())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        max_pos = queries.task_max_position(
            conn, project_id=data.project_id, status=data.status
        )
        queries.task_create(
            conn,
            project_id=data.project_id,
            title=data.title,
            description=data.description,
            status=data.status,
            who=data.who,
            due_date=data.parsed_due_date(),
            position=max_pos + 1,
        )
        cur = conn.cursor()
        cur.execute("SELECT LAST_INSERT_ID()")
        task_id = cur.fetchone()["LAST_INSERT_ID()"]
        row = queries.task_get_by_id(conn, id=task_id)
        return jsonify(Task(**row).model_dump(mode="json")), 201
    finally:
        conn.close()


def _apply_position_change(
    queries: Any,
    conn: Any,
    task_id: int,
    data: TaskUpdate,
    existing: dict[str, Any],
) -> None:
    """Apply project move / status / position changes from a PATCH payload."""
    # Move to different project (drag between kanbans)
    if data.project_id is not None:
        queries.task_move(
            conn,
            id=task_id,
            project_id=data.project_id,
            status=data.status or existing["status"],
            position=(
                data.position if data.position is not None else existing["position"]
            ),
        )
        return
    # Status + position change (drag within kanban)
    if data.status is not None and data.position is not None:
        queries.task_update_status(
            conn, id=task_id, status=data.status, position=data.position
        )
        return
    if data.status is not None or data.position is not None:
        queries.task_update_status(
            conn,
            id=task_id,
            status=data.status or existing["status"],
            position=(
                data.position if data.position is not None else existing["position"]
            ),
        )


def _has_field_updates(data: TaskUpdate) -> bool:
    """Return True if the payload has any plain-field update."""
    return any(
        [
            data.title,
            data.description is not None,
            data.who is not None,
            data.parsed_due_date(),
        ]
    )


def _apply_field_updates(
    queries: Any,
    conn: Any,
    task_id: int,
    data: TaskUpdate,
    existing: dict[str, Any],
) -> None:
    """Apply title/description/who/due_date updates from a PATCH payload."""
    queries.task_update(
        conn,
        id=task_id,
        title=data.title or existing["title"],
        description=(
            data.description
            if data.description is not None
            else existing["description"]
        ),
        status=data.status or existing["status"],
        who=data.who if data.who is not None else existing["who"],
        due_date=data.parsed_due_date() or existing["due_date"],
    )


@bp.route("/<int:task_id>", methods=["PATCH"])
def update_task(task_id: int) -> Any:
    """Update a task."""
    data = TaskUpdate(**request.get_json())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.task_get_by_id(conn, id=task_id)
        if not existing:
            return jsonify({"error": "Not found"}), 404

        _apply_position_change(queries, conn, task_id, data, existing)
        if _has_field_updates(data):
            _apply_field_updates(queries, conn, task_id, data, existing)

        row = queries.task_get_by_id(conn, id=task_id)
        return jsonify(Task(**row).model_dump(mode="json"))
    finally:
        conn.close()


@bp.route("/<int:task_id>", methods=["DELETE"])
def delete_task(task_id: int) -> Any:
    """Delete a task."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        queries.task_delete(conn, id=task_id)
        return "", 204
    finally:
        conn.close()

"""Wiki classification API routes (#376b).

The CLI ``ken wiki groom`` is the only intended consumer. The server here stays
*unaware* of ``ARCHITECTURE.md``: it just persists opaque ``(task_id, section_path)``
pairs. Section-path validation is the CLI's responsibility (it reads the architecture
file locally and refuses any path that isn't declared there). That keeps the
architecture file out of the DB and out of the server's request path.
"""

from contextlib import suppress
from typing import Any

from flask import Blueprint, g, jsonify, request
from flask_login import current_user

import dashboard.db as db
from dashboard.auth_user import current_user_can_project

bp = Blueprint("wiki", __name__, url_prefix="/api/v1/wiki")


def _principal_name() -> str:
    """Best-effort actor name for the ``classified_by`` column."""
    with suppress(RuntimeError, AttributeError):
        if current_user.is_authenticated:
            return getattr(current_user, "name", "") or ""
    with suppress(RuntimeError):
        return str(g.get("api_auth_principal") or "")
    return ""


@bp.route("/unclassified", methods=["GET"])
def list_unclassified() -> Any:
    """Return every task without a wiki classification.

    Optional ``?project=<id>`` filter — when set, the response is scoped to a single
    project (and read scope is enforced). Without it, every unclassified task across
    every project the caller can see.
    """
    project_filter = request.args.get("project")
    if project_filter and not current_user_can_project(project_filter, "read"):
        return jsonify({"error": "forbidden"}), 403
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        rows = list(queries.wiki_get_unclassified_tasks(conn))
    finally:
        conn.close()
    if project_filter:
        rows = [r for r in rows if r["project_id"] == project_filter]
    return jsonify(rows)


@bp.route("/all", methods=["GET"])
def list_all() -> Any:
    """Return every classification joined with task data.

    Consumed by ``ken wiki sync`` to render the MD tree. Same project-scoping rules as
    ``/unclassified``: optional ``?project=<id>`` filter, server stores opaque
    ``section_path`` strings.
    """
    project_filter = request.args.get("project")
    if project_filter and not current_user_can_project(project_filter, "read"):
        return jsonify({"error": "forbidden"}), 403
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        rows = list(queries.wiki_get_all(conn))
    finally:
        conn.close()
    if project_filter:
        rows = [r for r in rows if r["project_id"] == project_filter]
    return jsonify(
        [
            {
                "task_id": r["task_id"],
                "section_path": r["section_path"],
                "classified_at": (
                    r["classified_at"].isoformat() if r["classified_at"] else None
                ),
                "classified_by": r["classified_by"],
                "title": r["title"],
                "description": r["description"],
                "status": r["status"],
                "who": r["who"],
                "project_id": r["project_id"],
            }
            for r in rows
        ],
    )


@bp.route("/classify/<int:task_id>", methods=["GET"])
def get_classification(task_id: int) -> Any:
    """Return the current classification for a task, or 404 if unclassified."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        task = queries.task_get_by_id(conn, id=task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        if not current_user_can_project(task["project_id"], "read"):
            return jsonify({"error": "forbidden"}), 403
        row = queries.wiki_get_for_task(conn, task_id=task_id)
        if not row:
            return jsonify({"error": "Unclassified"}), 404
        return jsonify(
            {
                "task_id": row["task_id"],
                "section_path": row["section_path"],
                "classified_at": (
                    row["classified_at"].isoformat() if row["classified_at"] else None
                ),
                "classified_by": row["classified_by"],
            },
        )
    finally:
        conn.close()


@bp.route("/classify", methods=["POST"])
def classify() -> Any:
    """Upsert a classification.

    Body: ``{task_id: int, section_path: str}``.
        Section-path validity is the caller's responsibility (the CLI validates
        against the local ARCHITECTURE.md before sending). The server stores
        whatever string it gets — that keeps the architecture out of the DB.
    """
    payload = request.get_json() or {}
    task_id = payload.get("task_id")
    section_path = (payload.get("section_path") or "").strip()
    if not isinstance(task_id, int) or task_id <= 0:
        return jsonify({"error": "task_id must be a positive integer"}), 400
    if not section_path:
        return jsonify({"error": "section_path required"}), 400
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        task = queries.task_get_by_id(conn, id=task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        if not current_user_can_project(task["project_id"], "write"):
            return jsonify({"error": "forbidden"}), 403
        queries.wiki_classify(
            conn,
            task_id=task_id,
            section_path=section_path,
            classified_by=_principal_name(),
        )
        row = queries.wiki_get_for_task(conn, task_id=task_id)
    finally:
        conn.close()
    return (
        jsonify(
            {
                "task_id": row["task_id"],
                "section_path": row["section_path"],
                "classified_at": (
                    row["classified_at"].isoformat() if row["classified_at"] else None
                ),
                "classified_by": row["classified_by"],
            },
        ),
        200,
    )


@bp.route("/classify/<int:task_id>", methods=["DELETE"])
def clear_classification(task_id: int) -> Any:
    """Drop the classification for a task."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        task = queries.task_get_by_id(conn, id=task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        if not current_user_can_project(task["project_id"], "write"):
            return jsonify({"error": "forbidden"}), 403
        queries.wiki_clear(conn, task_id=task_id)
    finally:
        conn.close()
    return "", 204

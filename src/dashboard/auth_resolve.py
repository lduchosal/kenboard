"""Resolve the project_id targeted by an API request (auth middleware).

Split out of ``auth.py`` (ken #806): given the method + path of the current request,
derive which project the per-project api_key scope check applies to.
"""

from __future__ import annotations

from flask import request

from dashboard import db


def _int_suffix(path: str) -> int | None:
    """Parse the trailing ``/<int>`` segment of ``path``, or ``None``."""
    try:
        return int(path.rsplit("/", 1)[1])
    except (ValueError, IndexError):
        return None


def _task_project_id(task_id: int | None) -> str | None:
    """Look up the project_id owning ``task_id`` in the DB (``None`` if unknown)."""
    if task_id is None:
        return None
    conn = db.get_connection()
    try:
        row = db.load_queries().task_get_by_id(conn, id=task_id)
        return row["project_id"] if row else None
    finally:
        conn.close()


def _project_from_tasks(method: str, path: str) -> str | None:
    """Resolve the project for ``/api/v1/tasks`` endpoints."""
    # GET /api/v1/tasks?project=X
    if path == "/api/v1/tasks" and method == "GET":
        return request.args.get("project")
    # POST /api/v1/tasks → body.project_id
    if path == "/api/v1/tasks" and method == "POST":
        body = request.get_json(silent=True) or {}
        return body.get("project_id")
    # PATCH/DELETE /api/v1/tasks/<id> → SELECT project_id from DB
    if path.startswith("/api/v1/tasks/") and method in ("PATCH", "DELETE"):
        return _task_project_id(_int_suffix(path))
    return None


def _project_from_wiki(method: str, path: str) -> str | None:
    """Resolve the project for ``/api/v1/wiki`` endpoints."""
    # GET /api/v1/wiki/{unclassified,all}?project=X — cross-project by
    # design, but api_keys are per-project so we require the explicit
    # filter for them. The route handlers also enforce
    # ``current_user_can_project``.
    if path in ("/api/v1/wiki/unclassified", "/api/v1/wiki/all") and method == "GET":
        return request.args.get("project")
    # POST /api/v1/wiki/classify → body.task_id → SELECT project_id from DB
    if path == "/api/v1/wiki/classify" and method == "POST":
        body = request.get_json(silent=True) or {}
        body_task_id = body.get("task_id")
        return _task_project_id(body_task_id if isinstance(body_task_id, int) else None)
    # GET/DELETE /api/v1/wiki/classify/<task_id> → URL → SELECT project_id
    if path.startswith("/api/v1/wiki/classify/") and method in ("GET", "DELETE"):
        return _task_project_id(_int_suffix(path))
    return None


def _resolve_project_id(method: str, path: str) -> str | None:
    """Best-effort: derive the project_id targeted by the current request.

    Returns ``None`` if the endpoint is not project-scoped (admin-only) or if the
    project_id cannot be determined (in which case the caller will deny the request).
    """
    if path.startswith("/api/v1/tasks"):
        return _project_from_tasks(method, path)
    # PATCH/DELETE /api/v1/projects/<id> → URL <id>
    if path.startswith("/api/v1/projects/") and method in ("PATCH", "DELETE"):
        return path.rsplit("/", 1)[1]
    if path.startswith("/api/v1/wiki"):
        return _project_from_wiki(method, path)
    return None

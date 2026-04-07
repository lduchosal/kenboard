"""API key authentication middleware.

See ``doc/api-keys.md`` for the full spec.

Behaviour:

- Reads ``Authorization: Bearer <key>`` from the request.
- Short-circuit: if the bearer matches ``Config.KENBOARD_ADMIN_KEY`` (the
  static admin key from ``.env``), all checks pass.
- Otherwise, looks up the key by ``sha256(key)`` in ``api_keys`` (must not
  be revoked, must not be expired). On match, derives the project_id of
  the request and verifies the scope:

  - ``GET``  → ``read``
  - ``POST`` / ``PATCH`` / ``DELETE`` → ``write``
  - ``admin`` operations are reserved to the admin key only (no per-project
    admin scope is needed for the current endpoints — admin = "create
    api_keys, manage users, manage categories", which all live under
    /api/v1/keys, /api/v1/users, /api/v1/categories and are blocked here
    when the requester is not the admin key).

- Rollout: if ``Config.KENBOARD_AUTH_ENFORCED`` is False, the middleware
  validates a present token (and updates ``last_used_at``) but never
  blocks a request that has no token. This is the deploy-without-breaking
  mode used until the web UI itself authenticates.
"""

from __future__ import annotations

import hashlib
from typing import Any

from flask import Flask, g, jsonify, request

import dashboard.db as db
from dashboard.config import Config
from dashboard.logging import get_logger

log = get_logger("auth")

# Endpoints that need a project_id from the request to scope the check.
# The mapping logic itself lives in ``_resolve_project_id`` below.

# Endpoints that REQUIRE the admin key (no per-project api_key works).
# Tuples of (path_prefix, methods | None for "any").
ADMIN_ONLY_PREFIXES: tuple[tuple[str, frozenset[str] | None], ...] = (
    ("/api/v1/keys", None),
    ("/api/v1/users", None),
    ("/api/v1/categories", None),
    # Project create / list also reserved to admin (no project_id to scope on)
    ("/api/v1/projects", frozenset({"GET", "POST"})),
)


def _hash_key(key: str) -> str:
    """Return the sha256 hex digest of an API key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _required_scope(method: str) -> str:
    """Return the scope required for a given HTTP method."""
    if method == "GET":
        return "read"
    return "write"


def _resolve_project_id(method: str, path: str) -> str | None:
    """Best-effort: derive the project_id targeted by the current request.

    Returns ``None`` if the endpoint is not project-scoped (admin-only) or
    if the project_id cannot be determined (in which case the caller will
    deny the request).
    """
    # GET /api/v1/tasks?project=X
    if path == "/api/v1/tasks" and method == "GET":
        return request.args.get("project")
    # POST /api/v1/tasks → body.project_id
    if path == "/api/v1/tasks" and method == "POST":
        body = request.get_json(silent=True) or {}
        return body.get("project_id")
    # PATCH/DELETE /api/v1/tasks/<id> → SELECT project_id from DB
    if path.startswith("/api/v1/tasks/") and method in ("PATCH", "DELETE"):
        try:
            task_id = int(path.rsplit("/", 1)[1])
        except (ValueError, IndexError):
            return None
        conn = db.get_connection()
        try:
            row = db.load_queries().task_get_by_id(conn, id=task_id)
            return row["project_id"] if row else None
        finally:
            conn.close()
    # PATCH/DELETE /api/v1/projects/<id> → URL <id>
    if path.startswith("/api/v1/projects/") and method in ("PATCH", "DELETE"):
        return path.rsplit("/", 1)[1]
    return None


def _is_admin_only(method: str, path: str) -> bool:
    """Return True if the endpoint is reserved to the admin key."""
    for prefix, methods in ADMIN_ONLY_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            if methods is None or method in methods:
                return True
    return False


def _lookup_api_key(token: str) -> dict[str, Any] | None:
    """Look up an api_key row by its plain-text bearer token."""
    key_hash = _hash_key(token)
    conn = db.get_connection()
    try:
        row = db.load_queries().key_get_by_hash(conn, key_hash=key_hash)
        return dict(row) if row else None
    finally:
        conn.close()


def _project_scope_for_key(api_key_id: str, project_id: str) -> str | None:
    """Return the scope an api_key has on a project, or None if none."""
    conn = db.get_connection()
    try:
        row = db.load_queries().key_scopes_get_for_project(
            conn, api_key_id=api_key_id, project_id=project_id
        )
    finally:
        conn.close()
    return row["scope"] if row else None


def _scope_satisfies(actual: str, required: str) -> bool:
    """Return True if ``actual`` scope grants the ``required`` scope."""
    order = {"read": 0, "write": 1, "admin": 2}
    return order.get(actual, -1) >= order.get(required, 99)


def _touch_last_used(api_key_id: str) -> None:
    """Update last_used_at = NOW() for an api_key."""
    conn = db.get_connection()
    try:
        db.load_queries().key_touch_last_used(conn, id=api_key_id)
    finally:
        conn.close()


def _extract_bearer() -> str | None:
    """Extract a bearer token from the Authorization header."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer ") :].strip() or None


def _enforce() -> Any:
    """Run the middleware on the current request.

    Returns a Flask response (tuple) to short-circuit if denied, or
    ``None`` to let the request through.
    """
    # Only API requests are subject to the middleware.
    if not request.path.startswith("/api/v1/"):
        return None

    method = request.method
    path = request.path
    token = _extract_bearer()
    enforced = Config.KENBOARD_AUTH_ENFORCED

    g.api_auth_principal = None  # populated below if a token validates

    # Admin shortcut: matches the static .env key.
    if token and Config.KENBOARD_ADMIN_KEY and token == Config.KENBOARD_ADMIN_KEY:
        g.api_auth_principal = "admin"
        return None

    # Token-less request
    if token is None:
        if not enforced:
            return None  # legacy open mode
        return jsonify({"error": "missing Authorization header"}), 401

    # Token present → validate against api_keys
    row = _lookup_api_key(token)
    if row is None:
        if not enforced:
            log.warning("api_key_invalid_soft", path=path)
            return None
        return jsonify({"error": "invalid or revoked api key"}), 401

    api_key_id = row["id"]
    g.api_auth_principal = api_key_id
    _touch_last_used(api_key_id)

    # Admin-only endpoints reject any non-admin api_key (only KENBOARD_ADMIN_KEY
    # can reach them).
    if _is_admin_only(method, path):
        if not enforced:
            log.warning("api_key_admin_only_soft", path=path)
            return None
        return jsonify({"error": "admin key required for this endpoint"}), 403

    # Project-scoped endpoints
    project_id = _resolve_project_id(method, path)
    if project_id is None:
        if not enforced:
            return None
        return jsonify({"error": "cannot resolve project for scope check"}), 403

    actual = _project_scope_for_key(api_key_id, project_id)
    required = _required_scope(method)
    if actual is None or not _scope_satisfies(actual, required):
        if not enforced:
            log.warning(
                "api_key_scope_denied_soft",
                path=path,
                project_id=project_id,
                actual=actual,
                required=required,
            )
            return None
        return (
            jsonify(
                {
                    "error": "insufficient scope",
                    "required": required,
                    "project_id": project_id,
                }
            ),
            403,
        )

    return None


def init_auth(app: Flask) -> None:
    """Register the auth middleware as a before_request handler."""

    @app.before_request
    def _auth_before_request() -> Any:
        """Run the auth middleware on every incoming request."""
        return _enforce()

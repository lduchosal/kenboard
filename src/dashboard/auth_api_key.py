"""Bearer-token (api_key) enforcement of the API auth middleware.

Split out of ``auth.py`` (ken #808): key lookup/hashing, per-project scope check, admin-
only endpoint policy, last-used touch and onboarding-key promotion (#159).
``_enforce_api_key`` is the entry point called by ``auth._enforce``.
"""

from __future__ import annotations

import hashlib
from typing import Any

from flask import g, jsonify, request
from flask.typing import ResponseReturnValue

from dashboard import db
from dashboard.auth_resolve import _resolve_project_id
from dashboard.logging import get_logger

log = get_logger("auth")

# Endpoints that REQUIRE the admin key (no per-project api_key works).
# Tuples of (path_prefix, methods | None for "any").
ADMIN_ONLY_PREFIXES: tuple[tuple[str, frozenset[str] | None], ...] = (
    ("/api/v1/keys", None),
    ("/api/v1/users", None),
    # ``/api/v1/categories`` and ``/api/v1/projects`` used to be entirely
    # admin-only for cookie sessions. Since #197 they accept non-admin
    # sessions: the route handlers filter by ``user_category_scopes`` and
    # call ``api_admin_required`` for the mutations that stay admin-only
    # (POST/DELETE on categories — creating or destroying a board is a
    # board-admin action, not a per-board one).
)


def _hash_key(key: str) -> str:
    """Return the sha256 hex digest of an API key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _required_scope(method: str) -> str:
    """Return the scope required for a given HTTP method."""
    if method == "GET":
        return "read"
    return "write"


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
    """Update last_used_at, IP and User-Agent for an api_key (#209, #210)."""
    ip = request.remote_addr or ""
    agent = (request.user_agent.string or "")[:200]
    conn = db.get_connection()
    try:
        db.load_queries().key_touch_last_used(conn, id=api_key_id, ip=ip, agent=agent)
    finally:
        conn.close()


def _promote_onboarding_key(api_key_id: str) -> None:
    """Promote an onboarding token to onboarded on first use (#159)."""
    conn = db.get_connection()
    try:
        db.load_queries().key_update_type(conn, id=api_key_id, key_type="onboarded")
    finally:
        conn.close()
    log.info("auth.onboarding_promoted", api_key_id=api_key_id)


def _check_key_scope(
    api_key_id: str, method: str, path: str
) -> ResponseReturnValue | None:
    """Check the key's per-project scope; return the 403 response or ``None``."""
    project_id = _resolve_project_id(method, path)
    if project_id is None:
        return jsonify({"error": "cannot resolve project for scope check"}), 403

    actual = _project_scope_for_key(api_key_id, project_id)
    required = _required_scope(method)
    if actual is None or not _scope_satisfies(actual, required):
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


def _enforce_api_key(token: str, method: str, path: str) -> ResponseReturnValue | None:
    """Validate a bearer-token request and check its scope.

    Returns a Flask response tuple to deny, or ``None`` to let it through.
    """
    row = _lookup_api_key(token)
    if row is None:
        log.warning(
            "auth.api_key.invalid",
            method=method,
            path=path,
            ip=request.remote_addr,
        )
        return jsonify({"error": "invalid or revoked api key"}), 401

    api_key_id = row["id"]
    # Tag the principal with the owning user when the key is linked to one
    # (#110, traceability "qui fait quoi"). Falls back to bare key id for
    # legacy / unowned keys so audit logs always have *something*.
    owner = row.get("user_id")
    g.api_auth_principal = (
        f"key:{api_key_id}:user:{owner}" if owner else f"key:{api_key_id}"
    )
    _touch_last_used(api_key_id)

    # Admin-only endpoints reject any non-admin api_key (only
    # KENBOARD_ADMIN_KEY can reach them).
    if _is_admin_only(method, path):
        return jsonify({"error": "admin key required for this endpoint"}), 403

    denied = _check_key_scope(api_key_id, method, path)
    if denied is not None:
        return denied

    # #159: on first successful use of an onboarding token, promote it to
    # "onboarded" so the copy-onboard-link button can create a fresh one
    # for the next agent.
    if row.get("key_type") == "onboarding":
        _promote_onboarding_key(api_key_id)

    return None

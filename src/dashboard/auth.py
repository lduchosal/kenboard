"""API key authentication middleware.

See ``doc/api-keys.md`` for the full spec.

Behaviour:

- Reads ``Authorization: Bearer <key>`` from the request.
- Short-circuit: a logged-in Flask-Login session grants full access (the
  web UI keeps working without juggling tokens). On unsafe methods this
  short-circuit also enforces a Same-Origin check (cf. ``_origin_matches_host``)
  to block CSRF — a malicious site can trigger an authenticated POST via
  the user's cookie, but it cannot forge the ``Origin`` header.
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

- Tests can opt-out by setting ``app.config["LOGIN_DISABLED"] = True``,
  which mirrors how ``auth_user.admin_required`` already behaves.
"""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import urlparse

from flask import Flask, current_app, g, jsonify, request
from flask_login import current_user

import dashboard.db as db
from dashboard.config import Config
from dashboard.logging import get_logger
from dashboard.onboarding import cat_id_from_path, onboarding_json

log = get_logger("auth")

# HTTP methods that are conventionally safe (no side effects). CSRF
# protection is only enforced on the others.
SAFE_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})

# Endpoints that need a project_id from the request to scope the check.
# The mapping logic itself lives in ``_resolve_project_id`` below.

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

# Endpoints under an admin-only prefix that are nonetheless reachable by a
# non-admin **cookie** session because the route handler enforces its own
# ownership check (#53). They are NOT exempt for bearer-token callers — the
# admin api key still works there, normal api keys are still rejected.
SELF_SERVICE_COOKIE_PATHS: tuple[tuple[str, str], ...] = (
    # POST /api/v1/users/<id>/password — owner changes their own password
    ("/api/v1/users/", "/password"),
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


def _is_self_service_cookie_path(path: str) -> bool:
    """Return True for paths a non-admin cookie session may reach.

    The route handler is responsible for the actual ownership check
    (e.g. verifying ``current_user.id == user_id``).
    """
    for prefix, suffix in SELF_SERVICE_COOKIE_PATHS:
        if path.startswith(prefix) and path.endswith(suffix):
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


def _promote_onboarding_key(api_key_id: str) -> None:
    """Promote an onboarding token to onboarded on first use (#159)."""
    conn = db.get_connection()
    try:
        db.load_queries().key_update_type(conn, id=api_key_id, key_type="onboarded")
    finally:
        conn.close()
    log.info("auth.onboarding_promoted", api_key_id=api_key_id)


def _extract_bearer() -> str | None:
    """Extract a bearer token from the Authorization header."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer ") :].strip() or None


def _origin_matches_host() -> bool:
    """Check that ``Origin`` (or ``Referer``) matches the request ``Host``.

    Used as a CSRF defence on cookie-authenticated unsafe requests:
    browsers always set ``Origin`` (or at least ``Referer``) on
    cross-origin POST/PATCH/DELETE that carry cookies, and a malicious
    page cannot forge either header. A request whose ``Origin`` matches
    the server's own host is by definition same-origin and therefore
    not a CSRF.
    """
    expected = request.host  # e.g. "kanban.example.com" or "localhost:5000"
    origin = request.headers.get("Origin")
    if origin:
        return urlparse(origin).netloc == expected
    referer = request.headers.get("Referer")
    if referer:
        return urlparse(referer).netloc == expected
    # Modern browsers always emit at least one of those headers on
    # cookie-bearing unsafe requests. Their joint absence is suspicious
    # enough to refuse on principle.
    return False


def _enforce_cookie_session(method: str, path: str) -> Any:
    """Validate a cookie-authenticated request: CSRF + admin scope.

    Returns a Flask response tuple to deny, or ``None`` to let it through.
    """
    # CSRF defence: cookies are auto-attached cross-origin by the
    # browser, so we additionally require the request to be Same-Origin
    # on any unsafe method. Bearer-token requests skip this branch.
    if method not in SAFE_METHODS and not _origin_matches_host():
        log.warning(
            "auth.cookie.csrf_rejected",
            method=method,
            path=path,
            host=request.host,
            origin=request.headers.get("Origin"),
            referer=request.headers.get("Referer"),
            user_id=getattr(current_user, "id", None),
        )
        return (
            jsonify(
                {
                    "error": (
                        "CSRF: Origin/Referer header is missing or "
                        "does not match the request host"
                    )
                }
            ),
            403,
        )
    # Admin-only endpoints (managing users / api_keys / categories /
    # listing projects) require ``is_admin`` even via cookie auth.
    # Without this, any logged-in user could PATCH themselves with
    # ``is_admin=true``, create a new admin, or revoke another user.
    # Self-service paths (#53: /api/v1/users/<id>/password) are
    # exempt — the route handler enforces its own ownership check.
    if (
        _is_admin_only(method, path)
        and not getattr(current_user, "is_admin", False)
        and not _is_self_service_cookie_path(path)
    ):
        log.warning(
            "auth.cookie.admin_required",
            method=method,
            path=path,
            user_id=getattr(current_user, "id", None),
            user_name=getattr(current_user, "name", None),
            is_admin=getattr(current_user, "is_admin", None),
        )
        return (
            jsonify({"error": "admin required for this endpoint"}),
            403,
        )
    g.api_auth_principal = f"user:{current_user.id}"
    return None


def _enforce_api_key(token: str, method: str, path: str) -> Any:
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

    # #159: on first successful use of an onboarding token, promote it to
    # "onboarded" so the copy-onboard-link button can create a fresh one
    # for the next agent.
    if row.get("key_type") == "onboarding":
        _promote_onboarding_key(api_key_id)

    return None


def _enforce() -> Any:
    """Run the middleware on the current request.

    Returns a Flask response (tuple) to short-circuit if denied, or
    ``None`` to let the request through.
    """
    # Only API requests are subject to the middleware.
    if not request.path.startswith("/api/v1/"):
        return None

    # Tests bypass the middleware via ``LOGIN_DISABLED`` (same flag that
    # disables Flask-Login's @login_required). Mirrors auth_user.admin_required.
    if current_app.config.get("LOGIN_DISABLED"):
        g.api_auth_principal = "test"
        return None

    method = request.method
    path = request.path
    g.api_auth_principal = None  # populated below if a token validates

    # Logged-in user (cookie session) → full access on non-admin endpoints.
    # Checked first so that the web UI keeps working without a bearer token.
    if current_user and current_user.is_authenticated:
        return _enforce_cookie_session(method, path)

    token = _extract_bearer()

    # Admin shortcut: matches the static .env key.
    if token and Config.KENBOARD_ADMIN_KEY and token == Config.KENBOARD_ADMIN_KEY:
        g.api_auth_principal = "admin"
        return None

    if token is None:
        # Embed the install / init runbook so an LLM agent that hits an
        # API endpoint without credentials learns how to self-onboard
        # instead of just seeing a one-line "missing header" error (#117).
        from dashboard.onboarding import derive_base_url

        return jsonify(onboarding_json(cat_id_from_path(path), derive_base_url())), 401

    return _enforce_api_key(token, method, path)


def init_auth(app: Flask) -> None:
    """Register the auth middleware as a before_request handler."""

    @app.before_request
    def _auth_before_request() -> Any:
        """Run the auth middleware on every incoming request."""
        return _enforce()

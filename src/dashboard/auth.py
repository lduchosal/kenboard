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

from urllib.parse import urlparse

from flask import Flask, g, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user

from dashboard.auth_api_key import _enforce_api_key, _is_admin_only
from dashboard.auth_user import _is_login_disabled
from dashboard.config import Config
from dashboard.logging import get_logger
from dashboard.onboarding import (
    cat_id_from_path,
    derive_base_url,
    onboarding_json,
)

log = get_logger("auth")

# HTTP methods that are conventionally safe (no side effects). CSRF
# protection is only enforced on the others.
SAFE_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})

# Endpoints that need a project_id from the request to scope the check.
# The mapping logic itself lives in ``_resolve_project_id`` below.

# Endpoints under an admin-only prefix that are nonetheless reachable by a
# non-admin **cookie** session because the route handler enforces its own
# ownership check (#53). They are NOT exempt for bearer-token callers — the
# admin api key still works there, normal api keys are still rejected.
SELF_SERVICE_COOKIE_PATHS: tuple[tuple[str, str], ...] = (
    # POST /api/v1/users/<id>/password — owner changes their own password
    ("/api/v1/users/", "/password"),
)


def _is_self_service_cookie_path(path: str) -> bool:
    """Return True for paths a non-admin cookie session may reach.

    The route handler is responsible for the actual ownership check (e.g. verifying
    ``current_user.id == user_id``).
    """
    for prefix, suffix in SELF_SERVICE_COOKIE_PATHS:
        if path.startswith(prefix) and path.endswith(suffix):
            return True
    return False


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


def _csrf_reject(method: str, path: str) -> ResponseReturnValue | None:
    """CSRF defence: unsafe cookie-authenticated methods must be Same-Origin.

    Cookies are auto-attached cross-origin by the browser; bearer-token requests skip
    this check. Returns the 403 response or ``None``.
    """
    if method in SAFE_METHODS or _origin_matches_host():
        return None
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


def _enforce_cookie_session(method: str, path: str) -> ResponseReturnValue | None:
    """Validate a cookie-authenticated request: CSRF + admin scope.

    Returns a Flask response tuple to deny, or ``None`` to let it through.
    """
    denied = _csrf_reject(method, path)
    if denied is not None:
        return denied
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


def _enforce() -> ResponseReturnValue | None:
    """Run the middleware on the current request.

    Returns a Flask response (tuple) to short-circuit if denied, or ``None`` to let the
    request through.
    """
    # Only API requests are subject to the middleware.
    if not request.path.startswith("/api/v1/"):
        return None

    # Tests bypass the middleware via ``LOGIN_DISABLED`` (same flag that
    # disables Flask-Login's @login_required). The helper carries the
    # production guard (#199) — it raises if the flag is set without
    # ``Config.DEBUG=True`` so a misconfigured prod crashes loud.
    if _is_login_disabled():
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
        return jsonify(onboarding_json(cat_id_from_path(path), derive_base_url())), 401

    return _enforce_api_key(token, method, path)


def init_auth(app: Flask) -> None:
    """Register the auth middleware as a before_request handler."""

    @app.before_request
    def _auth_before_request() -> ResponseReturnValue | None:
        """Run the auth middleware on every incoming request."""
        return _enforce()

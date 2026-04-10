"""User session authentication via Flask-Login.

See ``doc/auth-user.md`` for the full spec.

This module exposes:
- ``init_login_manager(app)``: wires Flask-Login on the app, sets up the
  session cookie, registers the user loader and the ``/login`` /
  ``/logout`` routes blueprint.
- ``CurrentUser``: ``UserMixin`` wrapper around a DB user row.

Bootstrap: a user must already exist in the ``users`` table with a
non-empty ``password_hash``. Use ``kenboard set-password <name>`` to
seed the first admin password.
"""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import (
    Blueprint,
    Flask,
    abort,
    current_app,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_user,
    logout_user,
)

import dashboard.db as db
from dashboard.config import Config
from dashboard.logging import get_logger
from dashboard.onboarding import (
    cat_id_from_path,
    onboarding_text,
    wants_machine_response,
)

REMEMBER_DAYS = 30
# Per-IP brute-force budget on /login. The two limits are AND-combined,
# so a burst stops at 5 requests / minute and the long-term ceiling caps
# at 20 / hour. Sized to be invisible to a real human (5 honest typos in
# a minute = unusual) but to break credential-stuffing scripts.
LOGIN_RATE_LIMITS = "5 per minute; 20 per hour"
LOGIN_VIEW_ENDPOINT = "auth_user.login"
_LOGIN_TEMPLATE = "login.html"

log = get_logger("auth_user")

login_manager = LoginManager()
login_manager.login_view = LOGIN_VIEW_ENDPOINT
login_manager.session_protection = "strong"

bp = Blueprint("auth_user", __name__)

# Module-level limiter; bound to the app inside ``init_login_manager``.
# Default storage is in-memory (one bucket per worker process). For prod
# behind multiple Gunicorn workers this is approximate but still useful;
# upgrade to Redis (``RATELIMIT_STORAGE_URI``) when single-IP slip-through
# becomes a concern.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # no global limit; opt-in per route
    headers_enabled=True,
    storage_uri="memory://",
)

_hasher = PasswordHasher()


class CurrentUser(UserMixin):
    """Flask-Login wrapper for a row from the ``users`` table."""

    def __init__(self, row: dict[str, Any]):
        """Wrap a DB row into a Flask-Login compatible user object."""
        self.id = row["id"]
        self.name = row["name"]
        self.color = row.get("color", "")
        self.is_admin = bool(row.get("is_admin", False))
        self.session_nonce = row.get("session_nonce", "") or ""

    def get_id(self) -> str:
        """Return the user id with the session nonce embedded.

        Flask-Login stores this string in the session cookie. The user
        loader splits it back into ``(id, nonce)`` and refuses any value
        whose nonce doesn't match the current row in DB. That's how we
        invalidate cookies after /logout (cf. ken #54): rotating
        ``users.session_nonce`` makes the embedded nonce stale.
        """
        return f"{self.id}:{self.session_nonce}"


def _rotate_session_nonce(user_id: str) -> str:
    """Generate a fresh nonce, persist it on the user row, and return it."""
    nonce = secrets.token_hex(16)  # 32 hex chars = CHAR(32)
    conn = db.get_connection()
    try:
        db.load_queries().usr_rotate_session_nonce(conn, id=user_id, nonce=nonce)
    finally:
        conn.close()
    return nonce


@login_manager.user_loader
def _load_user(packed_id: str) -> CurrentUser | None:
    """Look up a user by id and verify the embedded session nonce.

    ``packed_id`` is the value previously returned by ``CurrentUser.get_id``,
    namely ``"<uuid>:<nonce>"``. We split it, fetch the user, and refuse
    if the nonce doesn't match what's currently in DB. That's what makes
    /logout effective despite Flask's signed-cookie sessions.
    """
    if ":" in packed_id:
        user_id, nonce = packed_id.split(":", 1)
    else:
        # Legacy session created before the nonce field existed: only
        # accept it if the user has no nonce yet (back-fill on first
        # successful login → next request flips us to the new format).
        user_id, nonce = packed_id, ""
    conn = db.get_connection()
    try:
        row = db.load_queries().usr_get_by_id(conn, id=user_id)
    finally:
        conn.close()
    if not row:
        return None
    expected = row.get("session_nonce") or ""
    if nonce != expected:
        return None
    return CurrentUser(row)


@login_manager.unauthorized_handler
def _unauthorized() -> Any:
    """Redirect browsers to login; serve an onboarding runbook to agents.

    Browser callers (``Accept`` includes ``text/html``) get the original
    302 → /login redirect so the cookie flow stays unchanged. CLI tools
    and LLM agents instead receive a 401 with a plain-text body explaining
    how to ``pip install kenboard`` and ``ken init <category-id>`` (#117).
    The category id, when present in the URL, is interpolated into the
    init command so the agent can copy-paste it.

    The ``?onboard`` query parameter forces the machine response regardless
    of the ``Accept`` header. This is what the copy-onboard-link button
    generates, so that agents using WebFetch (which sends ``Accept:
    text/html``) still receive the runbook instead of the login page.
    """
    if wants_machine_response(request) or "onboard" in request.args:
        cat_id = cat_id_from_path(request.path)
        base_url = request.host_url.rstrip("/")
        response = make_response(onboarding_text(cat_id, base_url), 401)
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        response.headers["WWW-Authenticate"] = 'Bearer realm="kenboard"'
        return response
    next_url = request.full_path if request.method == "GET" else None
    if next_url and next_url.endswith("?"):
        next_url = next_url[:-1]
    return redirect(url_for(LOGIN_VIEW_ENDPOINT, next=next_url))


def admin_required() -> None:
    """Abort with 403 if the current user is not an admin.

    To call from inside a ``@login_required`` view. Respects the Flask
    ``LOGIN_DISABLED`` config flag (used by tests) by becoming a no-op.
    """
    if current_app.config.get("LOGIN_DISABLED"):
        return
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


def api_admin_required() -> None:
    """Abort with 403 unless the caller is admin via cookie OR admin API key.

    Use this in API routes that should be reachable both by a logged-in
    admin user (Flask-Login session) and by the static
    ``KENBOARD_ADMIN_KEY``. The API auth middleware sets
    ``g.api_auth_principal == "admin"`` for the latter case.

    Tests with ``LOGIN_DISABLED=True`` skip the check, mirroring how
    ``admin_required`` and the API middleware behave.
    """
    from flask import g

    if current_app.config.get("LOGIN_DISABLED"):
        return
    if g.get("api_auth_principal") == "admin":
        return
    if current_user.is_authenticated and current_user.is_admin:
        return
    abort(403)


def init_login_manager(app: Flask) -> None:
    """Wire Flask-Login on the app and register the auth blueprint.

    Raises:
        RuntimeError: when ``KENBOARD_SECRET_KEY`` is missing from the
            environment outside of dev/test mode (``Config.DEBUG=False``).
    """
    if not Config.KENBOARD_SECRET_KEY:
        # In dev/tests we tolerate a hardcoded fallback so the app boots
        # without a real secret. In prod (DEBUG=false) the absence of a
        # secret means cookie sessions can't be safely signed — fail fast.
        if not Config.DEBUG:
            raise RuntimeError(
                "KENBOARD_SECRET_KEY must be set in .env when DEBUG=false"
            )
        app.secret_key = "dev-only-insecure-key-do-not-use-in-prod"  # nosec B105
    else:
        app.secret_key = Config.KENBOARD_SECRET_KEY

    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=REMEMBER_DAYS)
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"

    # Session cookie hardening. SameSite=Lax blocks cross-site POSTs that
    # would otherwise carry the cookie. HTTPS-only flags are conditional
    # so the dev server (HTTP) can still log in.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if Config.KENBOARD_HTTPS:
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["REMEMBER_COOKIE_SECURE"] = True

    login_manager.init_app(app)
    limiter.init_app(app)
    app.register_blueprint(bp)


@bp.route("/login", methods=["GET"])
def login() -> Any:
    """Render the login form (GET only).

    Split from the POST handler (cf. sonar python:S3752) so each route
    has a single HTTP method. The POST handler ``login_post`` lives just
    below and is the only one wearing the brute-force rate limit.
    """
    next_url = request.args.get("next") or ""
    return render_template(_LOGIN_TEMPLATE, error=None, next_url=next_url)


@bp.route("/login", methods=["POST"])
@limiter.limit(
    LOGIN_RATE_LIMITS,
    deduct_when=lambda response: response.status_code != 302,
    on_breach=lambda limit: log.warning(
        "auth.brute_force_attempt",
        ip=get_remote_address(),
        limit=str(limit.limit),
        path="/login",
    ),
)
def login_post() -> Any:
    """Validate credentials submitted by the login form (POST only).

    Rate-limited per IP via flask-limiter (cf. ``LOGIN_RATE_LIMITS``).
    Successful logins (302 redirect) do not count against the budget so
    a user who fat-fingers their password 4 times can still log in on
    the 5th try without burning through their hour quota.
    """
    next_url = request.form.get("next") or ""
    name = (request.form.get("name") or "").strip()
    password = request.form.get("password") or ""
    user = _verify_credentials(name, password)
    if user is not None:
        # Seed a session nonce on first login so the cookie carries one.
        # Pre-existing users (DB row with empty nonce) get their first
        # nonce here. Re-logging in keeps the same nonce — it only
        # rotates on /logout, which is what makes /logout effective.
        if not user.session_nonce:
            user.session_nonce = _rotate_session_nonce(user.id)
        login_user(user, remember=True, duration=timedelta(days=REMEMBER_DAYS))
        target = next_url if _is_safe_url(next_url) else url_for("pages.index")
        return redirect(target)
    return render_template(
        "login.html", error="Identifiants invalides", next_url=next_url
    )


@bp.route("/logout", methods=["POST"])
def logout() -> Any:
    """Invalidate every existing session for this user and redirect to /login.

    Rotates ``users.session_nonce`` BEFORE clearing the Flask session, so
    that any cookie captured prior to logout (including the long-lived
    ``remember_token``) becomes unverifiable on the next request.
    """
    if current_user.is_authenticated:
        _rotate_session_nonce(current_user.id)
    logout_user()
    return redirect(url_for(LOGIN_VIEW_ENDPOINT))


@bp.errorhandler(429)
def login_rate_limited(e: Any) -> Any:
    """Re-render the login form with a friendly throttle message.

    Bypassing the JSON default keeps the UX consistent for browsers while still
    returning the 429 status so scripts notice.
    """
    next_url = request.form.get("next") or ""
    # Use ``make_response`` so the 429 status is attached to an explicit
    # Response object — sonar python:S6863 does not recognise the
    # ``(body, status)`` tuple shortcut as explicit enough for error handlers.
    return make_response(
        render_template(
            "login.html",
            error="Trop de tentatives. Réessaye dans une minute.",
            next_url=next_url,
        ),
        429,
    )


def _verify_credentials(name: str, password: str) -> CurrentUser | None:
    """Look up a user by name and verify their argon2 password."""
    if not name or not password:
        return None
    conn = db.get_connection()
    try:
        row = db.load_queries().usr_get_by_name(conn, name=name)
    finally:
        conn.close()
    if not row or not row.get("password_hash"):
        return None
    try:
        _hasher.verify(row["password_hash"], password)
    except VerifyMismatchError:
        return None
    return CurrentUser(row)


def _is_safe_url(target: str) -> bool:
    """Allow only same-origin redirects to prevent open-redirect attacks."""
    if not target:
        return False
    # Reject absolute URLs and protocol-relative URLs
    if target.startswith("//") or "://" in target:
        return False
    # Must start with /
    return target.startswith("/")

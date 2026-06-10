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

import hashlib
from datetime import timedelta

from argon2 import PasswordHasher
from flask import (
    Blueprint,
    Flask,
    abort,
    current_app,
    g,
    request,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (
    LoginManager,
    current_user,
)

from dashboard.config import Config
from dashboard.logging import get_logger

REMEMBER_DAYS = 30
# Per-IP brute-force budget on /login. The two limits are AND-combined,
# so a burst stops at 5 requests / minute and the long-term ceiling caps
# at 20 / hour. Sized to be invisible to a real human (5 honest typos in
# a minute = unusual) but to break credential-stuffing scripts.
LOGIN_RATE_LIMITS = "5 per minute; 20 per hour"
LOGIN_VIEW_ENDPOINT = "auth_user.login"
_LOGIN_TEMPLATE = "login.html"

log = get_logger("auth_user")


def _ua_only_session_identifier() -> str:
    """Session-identifier override: hash User-Agent only, drop the IP (#254).

    Flask-Login's default ``_create_identifier`` hashes ``(remote_addr | UA)``
    and ``session_protection = "strong"`` deletes the session on any
    mismatch. That trips on every legitimate IP change (WiFi → 4G roaming,
    VPN flip, mobile carrier hop) and forces a re-login mid-task — losing
    in-flight modal drafts. Hashing only the UA preserves the defense
    against cookies replayed from a different browser while tolerating
    same-browser roaming.

    The session_nonce stored on ``users.session_nonce`` (rotated on logout
    and password change) remains the primary anti-cookie-theft control.
    """
    ua = request.headers.get("User-Agent", "") or ""
    return hashlib.sha512(ua.encode("utf-8")).hexdigest()


login_manager = LoginManager()
login_manager.login_view = LOGIN_VIEW_ENDPOINT
login_manager.session_protection = "strong"
# Flask-Login reads ``_session_identifier_generator`` (private name); the
# public ``session_identifier_generator`` attribute is silently ignored.
login_manager._session_identifier_generator = (  # noqa: SLF001 — seul hook exposé par flask-login
    _ua_only_session_identifier
)

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


def _is_login_disabled() -> bool:
    """Check the ``LOGIN_DISABLED`` test bypass with a production guard (#199).

    ``LOGIN_DISABLED`` is a pytest convenience that short-circuits every auth
    gate so unit tests don't have to juggle sessions. It MUST NEVER take
    effect in production. Python has no ``#ifdef DEBUG`` so the code path
    can't be stripped at build time — instead we centralize the read in
    this helper and refuse the bypass whenever the app is in production
    mode (neither ``Config.DEBUG`` nor Flask ``TESTING``).

    Every production read of the flag goes through this function so a
    misconfigured ``.env`` or a leaked secret that sets ``LOGIN_DISABLED``
    crashes the request loudly instead of silently disabling auth.

    Returns:
        ``True`` if the flag is set AND we are in debug or test mode.
        ``False`` when the flag is off.

    Raises:
        RuntimeError: when ``LOGIN_DISABLED`` is True but neither
            ``Config.DEBUG`` nor ``TESTING`` is set — the bypass is
            forbidden outside of test/dev.
    """
    if not current_app.config.get("LOGIN_DISABLED"):
        return False
    if not Config.DEBUG and not current_app.config.get("TESTING"):
        log.error(
            "login_disabled.refused_in_production",
            path=getattr(request, "path", None),
        )
        msg = (
            "LOGIN_DISABLED is a test-only flag and requires Config.DEBUG=True. "
            "Refusing to bypass authentication in production."
        )
        raise RuntimeError(msg)
    return True


def admin_required() -> None:
    """Abort with 403 if the current user is not an admin.

    To call from inside a ``@login_required`` view. Respects the Flask
    ``LOGIN_DISABLED`` config flag (used by tests) by becoming a no-op in debug mode.
    See :func:`_is_login_disabled` for the prod guard (it raises ``RuntimeError`` if the
    flag is set without ``DEBUG=True``).
    """
    if _is_login_disabled():
        return
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


def api_admin_required() -> None:
    """Abort with 403 unless the caller is admin via cookie OR admin API key.

    Use this in API routes that should be reachable both by a logged-in admin user
    (Flask-Login session) and by the static ``KENBOARD_ADMIN_KEY``. The API auth
    middleware sets ``g.api_auth_principal == "admin"`` for the latter case.

    Tests with ``LOGIN_DISABLED=True`` skip the check, mirroring how ``admin_required``
    and the API middleware behave. See :func:`_is_login_disabled` for the prod guard (it
    raises ``RuntimeError`` if the flag is set without ``DEBUG=True``).
    """
    if _is_login_disabled():
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
            msg = "KENBOARD_SECRET_KEY must be set in .env when DEBUG=false"
            raise RuntimeError(msg)
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

    # Expose to Jinja2 templates so login.html can show "Créer un compte"
    if Config.REGISTER_ALLOWED_DOMAIN:
        app.config["REGISTER_ALLOWED_DOMAIN"] = Config.REGISTER_ALLOWED_DOMAIN

    login_manager.init_app(app)
    limiter.init_app(app)

    # Import-for-side-effect: the password-reset (#798) and registration
    # (#232) modules attach their routes to ``bp``. Local import — they
    # import back from this module, top-level would be circular.
    from dashboard import (  # noqa: F401,PLC0415
        auth_login,
        auth_register,
        auth_reset,
        auth_session,
    )

    app.register_blueprint(bp)

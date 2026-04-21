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
import secrets
import uuid
from datetime import datetime, timedelta
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
        from dashboard.onboarding import derive_base_url

        response = make_response(onboarding_text(cat_id, derive_base_url()), 401)
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        response.headers["WWW-Authenticate"] = 'Bearer realm="kenboard"'
        return response
    next_url = request.full_path if request.method == "GET" else None
    if next_url and next_url.endswith("?"):
        next_url = next_url[:-1]
    return redirect(url_for(LOGIN_VIEW_ENDPOINT, next=next_url))


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
        raise RuntimeError(
            "LOGIN_DISABLED is a test-only flag and requires Config.DEBUG=True. "
            "Refusing to bypass authentication in production."
        )
    return True


def admin_required() -> None:
    """Abort with 403 if the current user is not an admin.

    To call from inside a ``@login_required`` view. Respects the Flask
    ``LOGIN_DISABLED`` config flag (used by tests) by becoming a no-op
    in debug mode. See :func:`_is_login_disabled` for the prod guard
    (it raises ``RuntimeError`` if the flag is set without ``DEBUG=True``).
    """
    if _is_login_disabled():
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
    ``admin_required`` and the API middleware behave. See
    :func:`_is_login_disabled` for the prod guard (it raises
    ``RuntimeError`` if the flag is set without ``DEBUG=True``).
    """
    from flask import g

    if _is_login_disabled():
        return
    if g.get("api_auth_principal") == "admin":
        return
    if current_user.is_authenticated and current_user.is_admin:
        return
    abort(403)


def _user_scope_for_category(user_id: str, category_id: str) -> str | None:
    """Return the scope a user has on a category, or ``None`` if no entry (#197).

    Args:
        user_id: Id of the user to check.
        category_id: Id of the category to check.

    Returns:
        ``"read"`` or ``"write"`` if the user has an entry, else ``None``.
    """
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        row = queries.usr_scopes_get_for_category(
            conn, user_id=user_id, category_id=category_id
        )
        return row["scope"] if row else None
    finally:
        conn.close()


def _user_scope_for_project(user_id: str, project_id: str) -> str | None:
    """Return the scope a user inherits on a project via its category (#197).

    Projects inherit the scope of their owning category, per spec §2 ("accès category ⇒
    accès transitif à tous ses projects et tasks").
    """
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        row = queries.usr_scopes_get_for_project(
            conn, user_id=user_id, project_id=project_id
        )
        return row["scope"] if row else None
    finally:
        conn.close()


def _is_api_key_principal(principal: str | None) -> bool:
    """Return True when the principal identifies a bearer-token caller.

    Cookie sessions set ``g.api_auth_principal = "user:<id>"`` (see
    ``auth._enforce_cookie_session``). Bearer tokens set it to
    ``"admin"`` (static admin key) or to the api-key UUID. Only the
    latter two bypass the per-user scope check.
    """
    if principal is None:
        return False
    return not principal.startswith("user:")


def _scope_allows(scope: str | None, action: str) -> bool:
    """Check whether ``scope`` is enough to perform ``action``.

    ``"write"`` implies ``"read"``; ``None`` means no access at all.
    """
    if scope is None:
        return False
    if action == "read":
        return scope in ("read", "write")
    if action == "write":
        return scope == "write"
    return False


def current_user_can(category_id: str, action: str) -> bool:
    """Return True if the logged-in user may perform ``action`` on ``category_id``.

    Rules (#197):
    - Tests with ``LOGIN_DISABLED=True`` → always allowed (unit suite bypass).
    - API-key principal (any) → always allowed: the API auth middleware
      (``auth.py``) already enforced per-project scopes before reaching
      the route, so we don't double-gate bearer-token callers here.
    - ``current_user.is_admin`` → always allowed (bypass scopes).
    - Otherwise, check ``user_category_scopes`` for the user.

    Args:
        category_id: Id of the category to test.
        action: Either ``"read"`` or ``"write"``.
    """
    from flask import g

    if _is_login_disabled():
        return True
    if _is_api_key_principal(g.get("api_auth_principal")):
        return True
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin:
        return True
    scope = _user_scope_for_category(current_user.id, category_id)
    return _scope_allows(scope, action)


def current_user_can_project(project_id: str, action: str) -> bool:
    """Same as :func:`current_user_can` but resolves the category from a project."""
    from flask import g

    if _is_login_disabled():
        return True
    if _is_api_key_principal(g.get("api_auth_principal")):
        return True
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin:
        return True
    scope = _user_scope_for_project(current_user.id, project_id)
    return _scope_allows(scope, action)


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

    # Expose to Jinja2 templates so login.html can show "Créer un compte"
    if Config.REGISTER_ALLOWED_DOMAIN:
        app.config["REGISTER_ALLOWED_DOMAIN"] = Config.REGISTER_ALLOWED_DOMAIN

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
        log.info(
            "auth.login_success",
            user_id=user.id,
            user_name=user.name,
            ip=get_remote_address(),
        )
        if _is_safe_url(next_url):
            return redirect(next_url)
        return redirect(url_for("pages.index"))
    log.warning(
        "auth.login_failed",
        user_name=name,
        ip=get_remote_address(),
    )
    return render_template(
        _LOGIN_TEMPLATE, error="Identifiants invalides", next_url=next_url
    )


@bp.route("/logout", methods=["POST"])
def logout() -> Any:
    """Invalidate every existing session for this user and redirect to /login.

    Rotates ``users.session_nonce`` BEFORE clearing the Flask session, so
    that any cookie captured prior to logout (including the long-lived
    ``remember_token``) becomes unverifiable on the next request.
    """
    if current_user.is_authenticated:
        log.info(
            "auth.logout",
            user_id=current_user.id,
            user_name=current_user.name,
            ip=get_remote_address(),
        )
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
            _LOGIN_TEMPLATE,
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


# -- Password reset (#231) ---------------------------------------------------

_FORGOT_TEMPLATE = "forgot_password.html"
_RESET_TEMPLATE = "reset_password.html"
_RESET_TOKEN_MINUTES = 30
_FORGOT_RATE_LIMITS = "3 per hour"
_INVALID_LINK_MSG = "Lien invalide ou expiré."


@bp.route("/forgot-password", methods=["GET"])
def forgot_password() -> Any:
    """Render the forgot-password form."""
    return render_template(_FORGOT_TEMPLATE, message=None, is_error=False)


@bp.route("/forgot-password", methods=["POST"])
@limiter.limit(_FORGOT_RATE_LIMITS)
def forgot_password_post() -> Any:
    """Generate a reset token and send the email.

    Always responds with the same message regardless of whether the email exists — no
    information leakage.
    """
    from dashboard.email import send_email

    email = (request.form.get("email") or "").strip().lower()
    # Always show the same message (no email existence leak)
    ok_msg = "Si un compte existe avec cet email, un lien a été envoyé."

    if not email:
        return render_template(_FORGOT_TEMPLATE, message="Email requis.", is_error=True)

    conn = db.get_connection()
    queries = db.load_queries()
    try:
        user = queries.usr_get_by_email(conn, email=email)
        if user:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires = datetime.now() + timedelta(minutes=_RESET_TOKEN_MINUTES)
            queries.prt_create(
                conn,
                id=str(uuid.uuid4()),
                user_id=user["id"],
                token_hash=token_hash,
                expires_at=expires,
            )
            reset_url = request.host_url.rstrip("/") + f"/reset-password/{token}"
            send_email(
                to=email,
                subject="Kenboard — Réinitialisation du mot de passe",
                template="email/password_reset.html",
                reset_url=reset_url,
            )
            log.info("auth.password_reset_requested", email=email)
    finally:
        conn.close()

    return render_template(_FORGOT_TEMPLATE, message=ok_msg, is_error=False)


@bp.route("/reset-password/<token>", methods=["GET"])
def reset_password(token: str) -> Any:
    """Render the new-password form if the token is valid."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        row = queries.prt_get_by_hash(conn, token_hash=token_hash)
    finally:
        conn.close()
    if not row:
        return render_template(
            _FORGOT_TEMPLATE,
            message=_INVALID_LINK_MSG,
            is_error=True,
        )
    return render_template(_RESET_TEMPLATE, token=token, error=None)


@bp.route("/reset-password/<token>", methods=["POST"])
def reset_password_post(token: str) -> Any:
    """Validate the token and apply the new password."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    if password != password_confirm:
        return render_template(
            _RESET_TEMPLATE,
            token=token,
            error="Les mots de passe ne correspondent pas.",
        )

    # Validate password strength
    from dashboard.password_strength import validate_password_strength

    try:
        validate_password_strength(password)
    except ValueError as e:
        return render_template(_RESET_TEMPLATE, token=token, error=str(e))

    conn = db.get_connection()
    queries = db.load_queries()
    try:
        row = queries.prt_get_by_hash(conn, token_hash=token_hash)
        if not row:
            return render_template(
                _FORGOT_TEMPLATE,
                message=_INVALID_LINK_MSG,
                is_error=True,
            )
        # Apply new password
        new_hash = _hasher.hash(password)
        queries.usr_update_password(conn, id=row["user_id"], password_hash=new_hash)
        # Invalidate all sessions (force re-login with new password)
        _rotate_session_nonce(row["user_id"])
        # Mark token as used
        queries.prt_mark_used(conn, id=row["id"])
        log.info("auth.password_reset_success", user_id=row["user_id"])
    finally:
        conn.close()

    return render_template(
        _LOGIN_TEMPLATE,
        error=None,
        next_url="",
        message="Mot de passe modifié. Connectez-vous avec le nouveau.",
    )


# -- Self-registration (#232) ------------------------------------------------

_REGISTER_TEMPLATE = "register.html"
_VERIFY_TOKEN_HOURS = 24
_REGISTER_RATE_LIMITS = "5 per hour"
_USERS_CATEGORY_NAME = "Users"
_USERS_CATEGORY_COLOR = "var(--accent)"
# Random avatar colors for new users.
_AVATAR_COLORS = [
    "#0969da",
    "#8250df",
    "#1a7f37",
    "#cf222e",
    "#bf8700",
    "#e16f24",
    "#0550ae",
    "#6639ba",
]


def _get_or_create_users_category(
    queries: Any,
    conn: Any,
) -> str:
    """Return the id of the 'Users' category, creating it if needed."""
    cats = list(queries.cat_get_all(conn))
    for c in cats:
        if c["name"] == _USERS_CATEGORY_NAME:
            return str(c["id"])
    cat_id = str(uuid.uuid4())
    max_pos = queries.cat_max_position(conn)
    queries.cat_create(
        conn,
        id=cat_id,
        name=_USERS_CATEGORY_NAME,
        color=_USERS_CATEGORY_COLOR,
        position=max_pos + 1,
    )
    return cat_id


@bp.route("/register", methods=["GET"])
def register() -> Any:
    """Render the registration form (only if domain restriction is set)."""
    domain = Config.REGISTER_ALLOWED_DOMAIN
    if not domain:
        abort(404)
    return render_template(_REGISTER_TEMPLATE, domain=domain, error=None, message=None)


@bp.route("/register", methods=["POST"])
@limiter.limit(_REGISTER_RATE_LIMITS)
def register_post() -> Any:
    """Validate input, send verification email, and store pending registration."""
    from dashboard.email import send_email
    from dashboard.password_strength import validate_password_strength

    domain = Config.REGISTER_ALLOWED_DOMAIN
    if not domain:
        abort(404)

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    def _err(msg: str) -> Any:
        """Render the register form with an error message."""
        return render_template(
            _REGISTER_TEMPLATE, domain=domain, error=msg, message=None
        )

    if not email:
        return _err("Email requis.")
    if not email.endswith(f"@{domain}"):
        return _err(f"Seules les adresses @{domain} sont acceptées.")
    if password != password_confirm:
        return _err("Les mots de passe ne correspondent pas.")
    try:
        validate_password_strength(password)
    except ValueError as e:
        return _err(str(e))

    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.usr_get_by_email(conn, email=email)
        if existing:
            return _err("Un compte existe déjà avec cet email.")

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        pw_hash = _hasher.hash(password)
        expires = datetime.now() + timedelta(hours=_VERIFY_TOKEN_HOURS)
        queries.evt_create(
            conn,
            id=str(uuid.uuid4()),
            email=email,
            password_hash=pw_hash,
            token_hash=token_hash,
            expires_at=expires,
        )
    finally:
        conn.close()

    verify_url = request.host_url.rstrip("/") + f"/verify-email/{token}"
    send_email(
        to=email,
        subject="Kenboard — Vérification de votre email",
        template="email/verify_email.html",
        verify_url=verify_url,
    )
    log.info("auth.registration_requested", email=email)

    return render_template(
        _REGISTER_TEMPLATE,
        domain=domain,
        error=None,
        message="Un email de vérification a été envoyé.",
    )


@bp.route("/verify-email/<token>", methods=["GET"])
def verify_email(token: str) -> Any:
    """Verify the token, create the user, their category and project."""
    import random

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        row = queries.evt_get_by_hash(conn, token_hash=token_hash)
        if not row:
            return render_template(
                _REGISTER_TEMPLATE,
                domain=Config.REGISTER_ALLOWED_DOMAIN,
                error=_INVALID_LINK_MSG,
                message=None,
            )

        email = row["email"]
        pw_hash = row["password_hash"]

        # Check email not taken (race condition guard)
        if queries.usr_get_by_email(conn, email=email):
            queries.evt_mark_used(conn, id=row["id"])
            return render_template(
                _LOGIN_TEMPLATE,
                error=None,
                next_url="",
                message="Ce compte existe déjà. Connectez-vous.",
            )

        # Create user
        user_id = str(uuid.uuid4())
        name = email
        color = random.choice(_AVATAR_COLORS)  # noqa: S311
        queries.usr_create(
            conn,
            id=user_id,
            name=name,
            email=email,
            color=color,
            password_hash=pw_hash,
            is_admin=0,
        )

        # Get or create "Users" category
        cat_id = _get_or_create_users_category(queries, conn)

        # Create personal project "user@email"
        proj_id = str(uuid.uuid4())
        max_pos = queries.proj_max_position_in_cat(conn, cat_id=cat_id)
        queries.proj_create(
            conn,
            id=proj_id,
            cat_id=cat_id,
            name=email,
            acronym=email.split("@")[0][:4].upper(),
            status="active",
            position=max_pos + 1,
            default_who=name,
        )

        # Grant write scope on "Users" category (write implies read)
        queries.usr_scopes_add(conn, user_id=user_id, category_id=cat_id, scope="write")

        # Mark token as used
        queries.evt_mark_used(conn, id=row["id"])
        log.info(
            "auth.registration_verified",
            user_id=user_id,
            email=email,
            project_id=proj_id,
        )
    finally:
        conn.close()

    return render_template(
        _LOGIN_TEMPLATE,
        error=None,
        next_url="",
        message="Compte activé ! Connectez-vous.",
    )

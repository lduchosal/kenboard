"""Self-registration flow (#232) — register + verify-email routes.

Split out of ``auth_user.py`` (ken #798); the routes register on the ``auth_user``
blueprint, imported by ``init_login_manager`` right before ``app.register_blueprint``.
See ``doc/auth-user.md`` for the full spec.

The flow is *prove the mailbox first, choose the password second* (#1194): ``POST
/register`` only takes an email and sends a link; the password is set on the page that
link opens. Whoever submits somebody else's address therefore never gets to pick the
password of the account it ends up creating.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Any

from flask import abort, render_template, request
from flask.typing import ResponseReturnValue
from pymysql import Connection

from dashboard import db
from dashboard import email as email_mod
from dashboard.auth_reset import _INVALID_LINK_MSG
from dashboard.auth_user import _LOGIN_TEMPLATE, _hasher, bp, limiter
from dashboard.config import Config
from dashboard.db import Queries
from dashboard.logging import get_logger
from dashboard.onboarding import derive_base_url
from dashboard.password_strength import validate_password_strength

log = get_logger("auth_user")

_REGISTER_TEMPLATE = "register.html"
_SET_PASSWORD_TEMPLATE = "reset_password.html"
_VERIFY_TOKEN_HOURS = 24
_REGISTER_RATE_LIMITS = "5 per hour"
_PERSONAL_CATEGORY_COLOR = "var(--accent)"
# Same answer whether or not the address already has an account (no enumeration).
_REGISTER_SENT_MSG = (
    "Si cette adresse peut s'inscrire, un email de vérification a été envoyé."
)
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


@bp.route("/register", methods=["GET"])
def register() -> ResponseReturnValue:
    """Render the registration form (only if domain restriction is set)."""
    domain = Config.REGISTER_ALLOWED_DOMAIN
    if not domain:
        abort(404)
    return render_template(_REGISTER_TEMPLATE, domain=domain, error=None, message=None)


def _validate_registration(domain: str, email: str) -> str | None:
    """Validate the registration form; return the error message or ``None``.

    The address must be a single bare ``local@domain`` (#1188): a suffix test alone
    accepts strings such as ``a@evil.example (x@allowed.example`` that an SMTP client
    then delivers to the *first* address.
    """
    if not email:
        return "Email requis."
    if (
        not email_mod.is_valid_address(email)
        or email.rsplit("@", 1)[1] != domain.lower()
    ):
        return f"Seules les adresses @{domain} sont acceptées."
    return None


def _create_verification_token(email: str) -> None:
    """Store the pending registration and send the verification email.

    Silently does nothing when the email already has an account — the caller shows the
    same message either way.
    """
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        if queries.usr_get_by_email(conn, email=email):
            log.info("auth.registration_duplicate", email=email)
            return
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        # The column predates #1194, when the hash travelled with the token.
        # It stays empty now: the password is chosen after the link is opened.
        queries.evt_create(
            conn,
            id=str(uuid.uuid4()),
            email=email,
            password_hash="",
            token_hash=token_hash,
            hours=_VERIFY_TOKEN_HOURS,
        )
    finally:
        conn.close()

    verify_url = f"{derive_base_url()}/verify-email/{token}"
    # Accès par attribut de module : les tests patchent
    # ``dashboard.email.send_email`` (late binding).
    email_mod.send_email(
        to=email,
        subject=f"{Config.KENBOARD_TITLE} — Vérification de votre email",
        template="email/verify_email.html",
        verify_url=verify_url,
    )
    log.info("auth.registration_requested", email=email)


@bp.route("/register", methods=["POST"])
@limiter.limit(_REGISTER_RATE_LIMITS)
def register_post() -> ResponseReturnValue:
    """Validate the address and send the verification email."""
    domain = Config.REGISTER_ALLOWED_DOMAIN
    if not domain:
        abort(404)

    email = (request.form.get("email") or "").strip().lower()
    error = _validate_registration(domain, email)
    if error:
        return render_template(
            _REGISTER_TEMPLATE, domain=domain, error=error, message=None
        )

    _create_verification_token(email)
    return render_template(
        _REGISTER_TEMPLATE, domain=domain, error=None, message=_REGISTER_SENT_MSG
    )


def _create_personal_board(
    queries: Queries, conn: Connection, email: str
) -> tuple[str, str]:
    """Create the category and project named after ``email``; return their ids."""
    cat_id = str(uuid.uuid4())
    queries.cat_create(
        conn,
        id=cat_id,
        name=email,
        color=_PERSONAL_CATEGORY_COLOR,
        position=queries.cat_max_position(conn) + 1,
    )
    proj_id = str(uuid.uuid4())
    queries.proj_create(
        conn,
        id=proj_id,
        cat_id=cat_id,
        name=email,
        acronym=email.split("@")[0][:4].upper(),
        status="active",
        position=0,
        default_who=email,
    )
    return cat_id, proj_id


def _provision_user(
    queries: Queries, conn: Connection, email: str, pw_hash: str
) -> str:
    """Create the user with a board of their own: category, project and scope.

    Each registered user gets a *personal* category (#1189). Scopes are granted per
    category, so the former shared "Users" category gave every registered user write
    access to everybody else's "personal" project.

    Returns the new project id.
    """
    user_id = str(uuid.uuid4())
    # secrets.choice: pas un besoin crypto (couleur d'avatar), mais évite
    # le hotspot Sonar "pseudorandom" et un import local pour rien.
    queries.usr_create(
        conn,
        id=user_id,
        name=email,
        email=email,
        color=secrets.choice(_AVATAR_COLORS),
        password_hash=pw_hash,
        is_admin=0,
    )

    cat_id, proj_id = _create_personal_board(queries, conn, email)
    # Write implies read; granted on the user's own category only.
    queries.usr_scopes_add(conn, user_id=user_id, category_id=cat_id, scope="write")
    log.info(
        "auth.registration_verified",
        user_id=user_id,
        email=email,
        project_id=proj_id,
    )
    return proj_id


def _invalid_link() -> ResponseReturnValue:
    """Render the register page with the "invalid or expired link" error."""
    return render_template(
        _REGISTER_TEMPLATE,
        domain=Config.REGISTER_ALLOWED_DOMAIN,
        error=_INVALID_LINK_MSG,
        message=None,
    )


def _set_password_form(token: str, error: str | None) -> ResponseReturnValue:
    """Render the "choose your password" form a verification link leads to."""
    return render_template(
        _SET_PASSWORD_TEMPLATE,
        token=token,
        error=error,
        form_action=f"/verify-email/{token}",
        heading="Choisir un mot de passe",
        submit_label="Activer le compte",
    )


def _pending_registration(token: str) -> dict[str, Any] | None:
    """Return the pending registration a token designates, or ``None``."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = db.get_connection()
    try:
        row = db.load_queries().evt_get_by_hash(conn, token_hash=token_hash)
        return dict(row) if row else None
    finally:
        conn.close()


@bp.route("/verify-email/<token>", methods=["GET"])
def verify_email(token: str) -> ResponseReturnValue:
    """Show the password form for a valid verification link.

    Opening the link changes nothing (mail scanners prefetch URLs); the account is
    created by the POST below.
    """
    if _pending_registration(token) is None:
        return _invalid_link()
    return _set_password_form(token, None)


def _password_error(password: str, password_confirm: str) -> str | None:
    """Return why the chosen password is rejected, or ``None`` when it is fine."""
    if password != password_confirm:
        return "Les mots de passe ne correspondent pas."
    try:
        validate_password_strength(password)
    except ValueError as e:
        return str(e)
    return None


@bp.route("/verify-email/<token>", methods=["POST"])
def verify_email_post(token: str) -> ResponseReturnValue:
    """Set the password and create the user, their category and project."""
    pending = _pending_registration(token)
    if pending is None:
        return _invalid_link()
    password = request.form.get("password") or ""
    error = _password_error(password, request.form.get("password_confirm") or "")
    if error:
        return _set_password_form(token, error)

    message = "Compte activé ! Connectez-vous."
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        # Check email not taken (race condition guard)
        if queries.usr_get_by_email(conn, email=pending["email"]):
            message = "Ce compte existe déjà. Connectez-vous."
        else:
            _provision_user(queries, conn, pending["email"], _hasher.hash(password))
        queries.evt_mark_used(conn, id=pending["id"])
    finally:
        conn.close()
    return render_template(_LOGIN_TEMPLATE, error=None, next_url="", message=message)

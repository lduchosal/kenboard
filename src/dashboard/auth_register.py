"""Self-registration flow (#232) — register + verify-email routes.

Split out of ``auth_user.py`` (ken #798); the routes register on the ``auth_user``
blueprint, imported by ``init_login_manager`` right before ``app.register_blueprint``.
See ``doc/auth-user.md`` for the full spec.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid

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
from dashboard.password_strength import validate_password_strength

log = get_logger("auth_user")

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
    queries: Queries,
    conn: Connection,
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
def register() -> ResponseReturnValue:
    """Render the registration form (only if domain restriction is set)."""
    domain = Config.REGISTER_ALLOWED_DOMAIN
    if not domain:
        abort(404)
    return render_template(_REGISTER_TEMPLATE, domain=domain, error=None, message=None)


def _validate_registration(
    domain: str, email: str, password: str, password_confirm: str
) -> str | None:
    """Validate the registration form; return the error message or ``None``."""
    if not email:
        return "Email requis."
    if not email.endswith(f"@{domain}"):
        return f"Seules les adresses @{domain} sont acceptées."
    if password != password_confirm:
        return "Les mots de passe ne correspondent pas."
    try:
        validate_password_strength(password)
    except ValueError as e:
        return str(e)
    return None


def _create_verification_token(email: str, password: str) -> bool:
    """Store the pending registration and send the verification email.

    Returns ``False`` (nothing sent) when the email is already taken.
    """
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        if queries.usr_get_by_email(conn, email=email):
            return False
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        pw_hash = _hasher.hash(password)
        queries.evt_create(
            conn,
            id=str(uuid.uuid4()),
            email=email,
            password_hash=pw_hash,
            token_hash=token_hash,
            hours=_VERIFY_TOKEN_HOURS,
        )
    finally:
        conn.close()

    verify_url = request.host_url.rstrip("/") + f"/verify-email/{token}"
    # Accès par attribut de module : les tests patchent
    # ``dashboard.email.send_email`` (late binding).
    email_mod.send_email(
        to=email,
        subject="Kenboard — Vérification de votre email",
        template="email/verify_email.html",
        verify_url=verify_url,
    )
    log.info("auth.registration_requested", email=email)
    return True


@bp.route("/register", methods=["POST"])
@limiter.limit(_REGISTER_RATE_LIMITS)
def register_post() -> ResponseReturnValue:
    """Validate input, send verification email, and store pending registration."""
    domain = Config.REGISTER_ALLOWED_DOMAIN
    if not domain:
        abort(404)

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    def _err(msg: str) -> ResponseReturnValue:
        """Render the register form with an error message."""
        return render_template(
            _REGISTER_TEMPLATE, domain=domain, error=msg, message=None
        )

    error = _validate_registration(domain, email, password, password_confirm)
    if error:
        return _err(error)

    if not _create_verification_token(email, password):
        return _err("Un compte existe déjà avec cet email.")

    return render_template(
        _REGISTER_TEMPLATE,
        domain=domain,
        error=None,
        message="Un email de vérification a été envoyé.",
    )


def _provision_user(
    queries: Queries, conn: Connection, email: str, pw_hash: str
) -> str:
    """Create the user, their 'Users' category, personal project and scope.

    Returns the new project id.
    """
    user_id = str(uuid.uuid4())
    name = email
    # secrets.choice: pas un besoin crypto (couleur d'avatar), mais évite
    # le hotspot Sonar "pseudorandom" et un import local pour rien.
    color = secrets.choice(_AVATAR_COLORS)
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
    log.info(
        "auth.registration_verified",
        user_id=user_id,
        email=email,
        project_id=proj_id,
    )
    return proj_id


@bp.route("/verify-email/<token>", methods=["GET"])
def verify_email(token: str) -> ResponseReturnValue:
    """Verify the token, create the user, their category and project."""
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

        # Check email not taken (race condition guard)
        if queries.usr_get_by_email(conn, email=email):
            queries.evt_mark_used(conn, id=row["id"])
            return render_template(
                _LOGIN_TEMPLATE,
                error=None,
                next_url="",
                message="Ce compte existe déjà. Connectez-vous.",
            )

        _provision_user(queries, conn, email, row["password_hash"])

        # Mark token as used
        queries.evt_mark_used(conn, id=row["id"])
    finally:
        conn.close()

    return render_template(
        _LOGIN_TEMPLATE,
        error=None,
        next_url="",
        message="Compte activé ! Connectez-vous.",
    )

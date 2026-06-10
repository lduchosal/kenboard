"""Password-reset flow (forgot-password + reset-password routes).

Split out of ``auth_user.py`` (ken #798); the routes register on the ``auth_user``
blueprint, imported by ``init_login_manager`` right before ``app.register_blueprint``.
See ``doc/auth-user.md`` for the full spec.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid

from flask import render_template, request
from flask.typing import ResponseReturnValue

from dashboard import db
from dashboard import email as email_mod
from dashboard.auth_session import _rotate_session_nonce
from dashboard.auth_user import _LOGIN_TEMPLATE, _hasher, bp, limiter
from dashboard.logging import get_logger
from dashboard.password_strength import validate_password_strength

log = get_logger("auth_user")

_FORGOT_TEMPLATE = "forgot_password.html"
_RESET_TEMPLATE = "reset_password.html"
_RESET_TOKEN_MINUTES = 30
_FORGOT_RATE_LIMITS = "3 per hour"
_INVALID_LINK_MSG = "Lien invalide ou expiré."


@bp.route("/forgot-password", methods=["GET"])
def forgot_password() -> ResponseReturnValue:
    """Render the forgot-password form."""
    return render_template(_FORGOT_TEMPLATE, message=None, is_error=False)


@bp.route("/forgot-password", methods=["POST"])
@limiter.limit(_FORGOT_RATE_LIMITS)
def forgot_password_post() -> ResponseReturnValue:
    """Generate a reset token and send the email.

    Always responds with the same message regardless of whether the email exists — no
    information leakage.
    """
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
            queries.prt_create(
                conn,
                id=str(uuid.uuid4()),
                user_id=user["id"],
                token_hash=token_hash,
                minutes=_RESET_TOKEN_MINUTES,
            )
            reset_url = request.host_url.rstrip("/") + f"/reset-password/{token}"
            # Accès par attribut de module : les tests patchent
            # ``dashboard.email.send_email`` (late binding).
            email_mod.send_email(
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
def reset_password(token: str) -> ResponseReturnValue:
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
def reset_password_post(token: str) -> ResponseReturnValue:
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

"""Optional OIDC authentication via Authlib (#126).

When ``Config.OIDC_ENABLED`` is True (all three required env vars are set),
this module registers a Flask blueprint with two routes:

- ``GET /oidc/login``  — redirects the browser to the IdP's authorization
  endpoint (authorization code flow + PKCE S256).
- ``GET /oidc/callback`` — exchanges the code for tokens, verifies the
  ``id_token``, looks up or creates the user in the ``users`` table, and
  calls ``login_user()`` exactly like the password login.

When ``OIDC_ENABLED`` is False (any of the three vars missing), the
``init_oidc()`` function is a silent no-op and no routes are registered.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Any

from authlib.integrations.flask_client import OAuth
from flask import (
    Blueprint,
    Flask,
    redirect,
    render_template,
    session,
    url_for,
)
from flask_login import login_user

import dashboard.db as db
from dashboard.auth_user import CurrentUser
from dashboard.config import Config
from dashboard.logging import get_logger

log = get_logger("auth_oidc")

bp = Blueprint("auth_oidc", __name__)
oauth = OAuth()


def init_oidc(app: Flask) -> None:
    """Register the OIDC client and blueprint if OIDC is configured.

    No-op when ``Config.OIDC_ENABLED`` is False, which keeps kenboard
    fully functional without an IdP (fail-soft).
    """
    if not Config.OIDC_ENABLED:
        return

    oauth.init_app(app)
    oauth.register(
        name="oidc",
        server_metadata_url=Config.OIDC_DISCOVERY_URL,
        client_id=Config.OIDC_CLIENT_ID,
        client_secret=Config.OIDC_CLIENT_SECRET,
        client_kwargs={
            "scope": "openid email profile",
            "code_challenge_method": "S256",
        },
    )
    app.config["OIDC_ENABLED"] = True
    app.register_blueprint(bp)


@bp.route("/oidc/login", methods=["GET"])
def oidc_login() -> Any:
    """Redirect the browser to the IdP's authorization endpoint."""
    session["oidc_next"] = session.get("next") or ""
    redirect_uri = url_for("auth_oidc.oidc_callback", _external=True)
    return oauth.oidc.authorize_redirect(redirect_uri)


@bp.route("/oidc/callback", methods=["GET"])
def oidc_callback() -> Any:
    """Exchange the authorization code for tokens and log the user in.

    The ``id_token`` is verified automatically by Authlib (signature,
    audience, expiry with 120 s leeway). Then we check ``email_verified``
    (unless ``OIDC_REQUIRE_EMAIL_VERIFIED=false``) and the allowed email
    domain. Finally we look up the user by email or lazy-create a new
    row with ``is_admin=False``.
    """
    token = oauth.oidc.authorize_access_token()
    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email") or ""
    name = userinfo.get("name") or email.split("@")[0] if email else ""

    if not email:
        log.warning("auth_oidc.no_email", userinfo=userinfo)
        return render_template(
            "login.html",
            error="Le fournisseur OIDC n'a pas retourné d'adresse email.",
            next_url="",
        )

    if Config.OIDC_REQUIRE_EMAIL_VERIFIED and not userinfo.get("email_verified"):
        log.warning("auth_oidc.email_not_verified", email=email)
        return render_template(
            "login.html",
            error="L'adresse email n'est pas vérifiée côté fournisseur.",
            next_url="",
        )

    if Config.OIDC_ALLOWED_EMAIL_DOMAIN:
        domain = email.rsplit("@", 1)[-1].lower()
        if domain != Config.OIDC_ALLOWED_EMAIL_DOMAIN.lower():
            log.warning(
                "auth_oidc.domain_rejected",
                email=email,
                expected=Config.OIDC_ALLOWED_EMAIL_DOMAIN,
            )
            return (
                render_template(
                    "login.html",
                    error=f"Le domaine {domain} n'est pas autorisé.",
                    next_url="",
                ),
                403,
            )

    conn = db.get_connection()
    queries = db.load_queries()
    try:
        row = queries.usr_get_by_email(conn, email=email)
        if row is None:
            user_id = str(uuid.uuid4())
            queries.usr_create(
                conn,
                id=user_id,
                name=name,
                email=email,
                color=_random_color(),
                password_hash="",
                is_admin=0,
            )
            row = queries.usr_get_by_id(conn, id=user_id)
            log.info("auth_oidc.user_created", user_id=user_id, email=email)
        nonce = secrets.token_hex(16)
        queries.usr_rotate_session_nonce(conn, id=row["id"], nonce=nonce)
        row["session_nonce"] = nonce
    finally:
        conn.close()

    user = CurrentUser(row)
    from datetime import timedelta

    from dashboard.auth_user import REMEMBER_DAYS

    login_user(user, remember=True, duration=timedelta(days=REMEMBER_DAYS))
    log.info("auth_oidc.login_success", user_id=user.id, email=email)

    next_url = session.pop("oidc_next", "") or url_for("pages.index")
    return redirect(next_url)


def _random_color() -> str:
    """Pick a random avatar color for a newly OIDC-created user."""
    colors = [
        "#0969da",
        "#8250df",
        "#bf8700",
        "#1a7f37",
        "#cf222e",
        "#6e7781",
    ]
    return secrets.choice(colors)

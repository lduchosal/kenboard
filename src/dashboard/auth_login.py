"""Login / logout routes and credential checks.

Split out of ``auth_user.py`` (ken #806); the routes register on the ``auth_user``
blueprint, imported by ``init_login_manager`` right before ``app.register_blueprint``.
See ``doc/auth-user.md`` for the full spec.
"""

from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus

from argon2.exceptions import VerifyMismatchError
from flask import make_response, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_limiter.util import get_remote_address
from flask_login import current_user, login_user, logout_user

from dashboard import db
from dashboard.auth_user import (
    _LOGIN_TEMPLATE,
    LOGIN_RATE_LIMITS,
    LOGIN_VIEW_ENDPOINT,
    REMEMBER_DAYS,
    CurrentUser,
    _hasher,
    _rotate_session_nonce,
    bp,
    limiter,
)
from dashboard.logging import get_logger

log = get_logger("auth_user")


@bp.route("/login", methods=["GET"])
def login() -> ResponseReturnValue:
    """Render the login form (GET only).

    Split from the POST handler (cf. sonar python:S3752) so each route has a single HTTP
    method. The POST handler ``login_post`` lives just below and is the only one wearing
    the brute-force rate limit.
    """
    next_url = request.args.get("next") or ""
    return render_template(_LOGIN_TEMPLATE, error=None, next_url=next_url)


@bp.route("/login", methods=["POST"])
@limiter.limit(
    LOGIN_RATE_LIMITS,
    deduct_when=lambda response: response.status_code != HTTPStatus.FOUND,
    on_breach=lambda limit: log.warning(
        "auth.brute_force_attempt",
        ip=get_remote_address(),
        limit=str(limit.limit),
        path="/login",
    ),
)
def login_post() -> ResponseReturnValue:
    """Validate credentials submitted by the login form (POST only).

    Rate-limited per IP via flask-limiter (cf. ``LOGIN_RATE_LIMITS``). Successful logins
    (302 redirect) do not count against the budget so a user who fat-fingers their
    password 4 times can still log in on the 5th try without burning through their hour
    quota.
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
def logout() -> ResponseReturnValue:
    """Invalidate every existing session for this user and redirect to /login.

    Rotates ``users.session_nonce`` BEFORE clearing the Flask session, so that any
    cookie captured prior to logout (including the long-lived ``remember_token``)
    becomes unverifiable on the next request.
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
def login_rate_limited(_e: Exception) -> ResponseReturnValue:
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

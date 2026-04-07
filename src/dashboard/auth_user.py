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

from datetime import timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import (
    Blueprint,
    Flask,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
)

import dashboard.db as db
from dashboard.config import Config

REMEMBER_DAYS = 30

login_manager = LoginManager()
login_manager.login_view = "auth_user.login"
login_manager.session_protection = "strong"

bp = Blueprint("auth_user", __name__)

_hasher = PasswordHasher()


class CurrentUser(UserMixin):
    """Flask-Login wrapper for a row from the ``users`` table."""

    def __init__(self, row: dict[str, Any]):
        """Wrap a DB row into a Flask-Login compatible user object."""
        self.id = row["id"]
        self.name = row["name"]
        self.color = row.get("color", "")
        self.is_admin = bool(row.get("is_admin", False))

    def get_id(self) -> str:
        """Return the user id (Flask-Login interface)."""
        return str(self.id)


@login_manager.user_loader
def _load_user(user_id: str) -> CurrentUser | None:
    """Look up a user by id, called by Flask-Login on every request."""
    conn = db.get_connection()
    try:
        row = db.load_queries().usr_get_by_id(conn, id=user_id)
    finally:
        conn.close()
    return CurrentUser(row) if row else None


@login_manager.unauthorized_handler
def _unauthorized() -> Any:
    """Redirect anonymous requests to the login page with a ``next`` arg."""
    next_url = request.full_path if request.method == "GET" else None
    if next_url and next_url.endswith("?"):
        next_url = next_url[:-1]
    return redirect(url_for("auth_user.login", next=next_url))


def admin_required() -> None:
    """Abort with 403 if the current user is not an admin.

    To call from inside a ``@login_required`` view. Respects the Flask
    ``LOGIN_DISABLED`` config flag (used by tests) by becoming a no-op.
    """
    from flask_login import current_user

    if current_app.config.get("LOGIN_DISABLED"):
        return
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


def init_login_manager(app: Flask) -> None:
    """Wire Flask-Login on the app and register the auth blueprint.

    Raises:
        RuntimeError: when ``KENBOARD_AUTH_ENFORCED`` is true but
            ``KENBOARD_SECRET_KEY`` is missing from the environment.
    """
    if not Config.KENBOARD_SECRET_KEY:
        # Allow boot when auth is not enforced (dev / tests). When enforced,
        # the absence of a secret means cookie sessions can't be signed
        # and login would silently break — fail fast instead.
        if Config.KENBOARD_AUTH_ENFORCED:
            raise RuntimeError(
                "KENBOARD_SECRET_KEY must be set in .env when "
                "KENBOARD_AUTH_ENFORCED=true"
            )
        app.secret_key = "dev-only-insecure-key-do-not-use-in-prod"
    else:
        app.secret_key = Config.KENBOARD_SECRET_KEY

    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=REMEMBER_DAYS)
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"

    login_manager.init_app(app)
    app.register_blueprint(bp)


@bp.route("/login", methods=["GET", "POST"])
def login() -> Any:
    """Render the login form (GET) or validate credentials (POST)."""
    error = None
    next_url = request.args.get("next") or request.form.get("next") or ""
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        password = request.form.get("password") or ""
        user = _verify_credentials(name, password)
        if user is not None:
            login_user(user, remember=True, duration=timedelta(days=REMEMBER_DAYS))
            target = next_url if _is_safe_url(next_url) else url_for("pages.index")
            return redirect(target)
        error = "Identifiants invalides"
    return render_template("login.html", error=error, next_url=next_url)


@bp.route("/logout", methods=["POST"])
def logout() -> Any:
    """Clear the session cookie and redirect to the login page."""
    logout_user()
    return redirect(url_for("auth_user.login"))


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

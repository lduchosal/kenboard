"""Session core — ``CurrentUser``, the user loader and the nonce rotation.

Split out of ``auth_user.py`` (ken #808). The ``@login_manager.user_loader`` and
``@login_manager.unauthorized_handler`` registrations happen at import, triggered by
``init_login_manager``. See ``doc/auth-user.md``.
"""

from __future__ import annotations

import secrets
from typing import Any

from flask import make_response, redirect, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import UserMixin

from dashboard import db
from dashboard.auth_user import LOGIN_VIEW_ENDPOINT, login_manager
from dashboard.logging import get_logger
from dashboard.onboarding import (
    cat_id_from_path,
    derive_base_url,
    onboarding_text,
    wants_machine_response,
)

log = get_logger("auth_user")


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

        Flask-Login stores this string in the session cookie. The user loader splits it
        back into ``(id, nonce)`` and refuses any value whose nonce doesn't match the
        current row in DB. That's how we invalidate cookies after /logout (cf. ken #54):
        rotating ``users.session_nonce`` makes the embedded nonce stale.
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

    ``packed_id`` is the value previously returned by ``CurrentUser.get_id``, namely
    ``"<uuid>:<nonce>"``. We split it, fetch the user, and refuse if the nonce doesn't
    match what's currently in DB. That's what makes /logout effective despite Flask's
    signed-cookie sessions.
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
def _unauthorized() -> ResponseReturnValue:
    """Redirect browsers to login; serve an onboarding runbook to agents.

    Browser callers (``Accept`` includes ``text/html``) get the original 302 → /login
    redirect so the cookie flow stays unchanged. CLI tools and LLM agents instead
    receive a 401 with a plain-text body explaining how to ``pip install kenboard`` and
    ``ken init <category-id>`` (#117). The category id, when present in the URL, is
    interpolated into the init command so the agent can copy-paste it.

    The ``?onboard`` query parameter forces the machine response regardless of the
    ``Accept`` header. This is what the copy-onboard-link button generates, so that
    agents using WebFetch (which sends ``Accept: text/html``) still receive the runbook
    instead of the login page.
    """
    if wants_machine_response(request) or "onboard" in request.args:
        cat_id = cat_id_from_path(request.path)
        response = make_response(onboarding_text(cat_id, derive_base_url()), 401)
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        response.headers["WWW-Authenticate"] = 'Bearer realm="kenboard"'
        return response
    next_url = request.full_path if request.method == "GET" else None
    if next_url and next_url.endswith("?"):
        next_url = next_url[:-1]
    return redirect(url_for(LOGIN_VIEW_ENDPOINT, next=next_url))

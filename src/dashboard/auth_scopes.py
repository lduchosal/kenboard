"""Per-user category/project scopes (#197) — permission checks for routes.

Split out of ``auth_user.py`` (ken #804). ``current_user_can`` /
``current_user_can_project`` are the route-facing checks; the ``_user_scope_*`` helpers
read ``user_category_scopes``. See ``doc/permissions.md`` for the spec.
"""

from __future__ import annotations

from flask import g
from flask_login import current_user

from dashboard import db
from dashboard.auth_api_key import _project_scope_for_key, _scope_satisfies
from dashboard.auth_user import _is_login_disabled


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


def _api_key_id(principal: str | None) -> str | None:
    """Return the api_key id of a ``key:<id>[:user:<owner>]`` principal, else ``None``.

    ``"admin"`` (the static admin key) and cookie sessions (``"user:<id>"``) are not
    per-project api_keys and yield ``None``.
    """
    if principal is None or not principal.startswith("key:"):
        return None
    return principal.split(":")[1]


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

    Rules (#197, #1187):
    - Tests with ``LOGIN_DISABLED=True`` → always allowed (unit suite bypass).
    - Per-project api_key → never: its scopes are per project, it holds none on a
      category. The middleware only vouches for the project the request *targets*,
      not for a category named in the body (moving a project to another board).
    - Static admin key → always allowed.
    - ``current_user.is_admin`` → always allowed (bypass scopes).
    - Otherwise, check ``user_category_scopes`` for the user.

    Args:
        category_id: Id of the category to test.
        action: Either ``"read"`` or ``"write"``.
    """
    if _is_login_disabled():
        return True
    principal = g.get("api_auth_principal")
    if _api_key_id(principal) is not None:
        return False
    if _is_api_key_principal(principal):
        return True
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin:
        return True
    scope = _user_scope_for_category(current_user.id, category_id)
    return _scope_allows(scope, action)


def current_user_can_project(project_id: str, action: str) -> bool:
    """Same as :func:`current_user_can` but resolves the category from a project.

    A per-project api_key is checked against its own scope on ``project_id`` (#1187):
    the middleware validated the project the request targets, but a route may act on a
    second one — the destination of a cross-project task move.
    """
    if _is_login_disabled():
        return True
    principal = g.get("api_auth_principal")
    key_id = _api_key_id(principal)
    if key_id is not None:
        actual = _project_scope_for_key(key_id, project_id)
        return actual is not None and _scope_satisfies(actual, action)
    if _is_api_key_principal(principal):
        return True
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin:
        return True
    scope = _user_scope_for_project(current_user.id, project_id)
    return _scope_allows(scope, action)


def visible_project_ids() -> set[str] | None:
    """Return the project ids the caller may read, or ``None`` when unrestricted.

    For cross-project listings (#1185) that cannot be gated by a single
    :func:`current_user_can_project` call. ``None`` means "do not filter": test mode,
    admins, and bearer-token callers — the API middleware only lets a scoped api_key
    reach such a listing with an explicit ``?project=`` it holds a scope on. An empty
    set means "nothing".
    """
    if _is_login_disabled():
        return None
    if _is_api_key_principal(g.get("api_auth_principal")):
        return None
    if not current_user.is_authenticated:
        return set()
    if current_user.is_admin:
        return None
    conn = db.get_connection()
    try:
        rows = db.load_queries().proj_list_for_user(conn, user_id=current_user.id)
        return {r["id"] for r in rows}
    finally:
        conn.close()

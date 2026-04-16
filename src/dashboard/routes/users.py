"""User API routes."""

import uuid
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import Blueprint, g, jsonify, request
from flask_login import current_user

import dashboard.db as db
from dashboard.auth_user import _is_login_disabled, api_admin_required, limiter
from dashboard.logging import get_logger
from dashboard.models.user import (
    PasswordChange,
    PasswordReset,
    User,
    UserCreate,
    UserScopeUpdate,
    UserUpdate,
)

bp = Blueprint("users", __name__, url_prefix="/api/v1/users")

log = get_logger("users")

NOT_FOUND_ERROR = {"error": "Not found"}

_hasher = PasswordHasher()


def _hash_password(password: str) -> str:
    """Hash a password using argon2."""
    return _hasher.hash(password)


def _row_with_scopes(conn: Any, queries: Any, row: dict[str, Any]) -> dict[str, Any]:
    """Attach ``scopes`` (list of category_id/scope dicts) to a user row."""
    scopes = list(queries.usr_scopes_get(conn, user_id=row["id"]))
    return row | {"scopes": scopes}


@bp.route("", methods=["GET"])
def list_users() -> Any:
    """List all users with their category scopes (#197)."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        rows = list(queries.usr_get_all(conn))
        enriched = [_row_with_scopes(conn, queries, row) for row in rows]
        return jsonify([User(**row).model_dump(mode="json") for row in enriched])
    finally:
        conn.close()


@bp.route("", methods=["POST"])
@limiter.limit("10 per hour")
def create_user() -> Any:
    """Create a new user."""
    data = UserCreate(**request.get_json())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        if queries.usr_get_by_name(conn, name=data.name):
            return jsonify({"error": "Name already exists"}), 409
        user_id = str(uuid.uuid4())
        password_hash = _hash_password(data.password) if data.password else ""
        queries.usr_create(
            conn,
            id=user_id,
            name=data.name,
            email=data.email,
            color=data.color,
            password_hash=password_hash,
            is_admin=int(data.is_admin),
        )
        row = queries.usr_get_by_id(conn, id=user_id)
        log.info(
            "admin.user_created",
            user_id=user_id,
            user_name=data.name,
            principal=g.get("api_auth_principal"),
        )
        return (
            jsonify(
                User(**_row_with_scopes(conn, queries, row)).model_dump(mode="json")
            ),
            201,
        )
    finally:
        conn.close()


@bp.route("/<user_id>", methods=["PATCH"])
def update_user(user_id: str) -> Any:
    """Update a user (name, color, is_admin only — passwords go elsewhere)."""
    data = UserUpdate(**request.get_json())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.usr_get_by_id(conn, id=user_id)
        if not existing:
            return jsonify(NOT_FOUND_ERROR), 404
        new_name = data.name or existing["name"]
        # Refuse rename collision with another user
        if data.name and data.name != existing["name"]:
            collision = queries.usr_get_by_name(conn, name=data.name)
            if collision and collision["id"] != user_id:
                return jsonify({"error": "Name already exists"}), 409
        is_admin_val = (
            int(data.is_admin) if data.is_admin is not None else existing["is_admin"]
        )
        queries.usr_update(
            conn,
            id=user_id,
            name=new_name,
            color=data.color or existing["color"],
            is_admin=is_admin_val,
        )
        row = queries.usr_get_by_id(conn, id=user_id)
        log.info(
            "admin.user_updated",
            user_id=user_id,
            principal=g.get("api_auth_principal"),
        )
        return jsonify(
            User(**_row_with_scopes(conn, queries, row)).model_dump(mode="json")
        )
    finally:
        conn.close()


@bp.route("/<user_id>/password", methods=["POST"])
def change_password(user_id: str) -> Any:
    """Change one's own password (#53).

    Requires a Flask-Login session that matches ``user_id`` and a valid
    ``old_password``. Bots with admin API keys should use
    ``/reset-password`` instead — they don't have a "current user".
    """
    # Tests with LOGIN_DISABLED=True skip ownership / authentication checks
    # so the unit suite can exercise the route without juggling sessions.
    # #199: the helper refuses the bypass in production even if the flag is set.
    if not _is_login_disabled():
        if not current_user.is_authenticated:
            return jsonify({"error": "login required"}), 401
        if str(current_user.id) != user_id:
            return jsonify({"error": "you can only change your own password"}), 403
    data = PasswordChange(**(request.get_json() or {}))
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        row = queries.usr_get_password_hash(conn, id=user_id)
        if not row:
            return jsonify(NOT_FOUND_ERROR), 404
        existing_hash = row.get("password_hash") or ""
        if not existing_hash:
            return jsonify({"error": "no password set"}), 400
        try:
            _hasher.verify(existing_hash, data.old_password)
        except VerifyMismatchError:
            return jsonify({"error": "wrong old password"}), 401
        queries.usr_update_password(
            conn, id=user_id, password_hash=_hash_password(data.new_password)
        )
        return "", 204
    finally:
        conn.close()


@bp.route("/<user_id>/reset-password", methods=["POST"])
@limiter.limit("5 per hour")
def reset_password(user_id: str) -> Any:
    """Admin reset of another user's password (#53).

    Caller must be an admin (cookie session with ``is_admin=True`` or the
    static ``KENBOARD_ADMIN_KEY``). The old password is **not** required —
    this is the recovery path when a user forgets theirs.
    """
    api_admin_required()
    data = PasswordReset(**(request.get_json() or {}))
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.usr_get_by_id(conn, id=user_id)
        if not existing:
            return jsonify(NOT_FOUND_ERROR), 404
        queries.usr_update_password(
            conn, id=user_id, password_hash=_hash_password(data.new_password)
        )
        return "", 204
    finally:
        conn.close()


@bp.route("/<user_id>/scopes", methods=["PUT"])
def update_user_scopes(user_id: str) -> Any:
    """Replace a user's category scopes atomically (#197).

    Admin only. The request body ``{"scopes": [...]}`` fully replaces the
    user's existing scopes: any scope not in the new list is removed, and
    any new scope is inserted. The clear + insert pair runs inside a
    single transaction so a partial failure leaves the DB untouched.

    Raises:
        Exception: any error from the DB driver during the transaction,
            re-raised after rolling back so no partial state is left.
    """
    api_admin_required()
    data = UserScopeUpdate(**(request.get_json() or {}))
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.usr_get_by_id(conn, id=user_id)
        if not existing:
            return jsonify(NOT_FOUND_ERROR), 404
        # Atomic replacement: clear then re-add inside one transaction.
        # The connection has autocommit=True, so wrap the two statements
        # in an explicit transaction block.
        conn.begin()
        try:
            queries.usr_scopes_clear(conn, user_id=user_id)
            for entry in data.scopes:
                queries.usr_scopes_add(
                    conn,
                    user_id=user_id,
                    category_id=entry.category_id,
                    scope=entry.scope,
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        row = queries.usr_get_by_id(conn, id=user_id)
        log.info(
            "admin.user_scopes_updated",
            user_id=user_id,
            n_scopes=len(data.scopes),
            principal=g.get("api_auth_principal"),
        )
        return jsonify(
            User(**_row_with_scopes(conn, queries, row)).model_dump(mode="json")
        )
    finally:
        conn.close()


@bp.route("/<user_id>", methods=["DELETE"])
def delete_user(user_id: str) -> Any:
    """Delete a user."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        queries.usr_delete(conn, id=user_id)
        log.info(
            "admin.user_deleted",
            user_id=user_id,
            principal=g.get("api_auth_principal"),
        )
        return "", 204
    finally:
        conn.close()

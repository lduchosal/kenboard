"""Category API routes."""

from typing import Any

from flask import Blueprint, g, jsonify, request
from flask_login import current_user

import dashboard.db as db
from dashboard.auth_user import (
    _is_api_key_principal,
    _is_login_disabled,
    api_admin_required,
    current_user_can,
)
from dashboard.models.category import Category, CategoryCreate, CategoryUpdate

bp = Blueprint("categories", __name__, url_prefix="/api/v1/categories")


def _should_filter_for_current_user() -> bool:
    """True when list endpoints should be filtered to the current user's scopes.

    Returns False for admin cookie sessions, admin API keys, test runs
    (``LOGIN_DISABLED``), and any API-key principal (API keys have their
    own project-level scoping enforced in ``auth.py``).
    """
    if _is_login_disabled():
        return False
    # Bearer-token callers are already scoped by auth.py, don't double-filter.
    if _is_api_key_principal(g.get("api_auth_principal")):
        return False
    if not current_user.is_authenticated:
        return False
    return not current_user.is_admin


@bp.route("", methods=["GET"])
def list_categories() -> Any:
    """List all categories (filtered to the user's scopes for non-admins)."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        if _should_filter_for_current_user():
            rows = list(queries.cat_list_for_user(conn, user_id=current_user.id))
        else:
            rows = list(queries.cat_get_all(conn))
        return jsonify([Category(**row).model_dump() for row in rows])
    finally:
        conn.close()


@bp.route("", methods=["POST"])
def create_category() -> Any:
    """Create a new category (admin only — non-admins cannot create boards).

    Automatically creates a first project "Project <name>" inside the new category so
    the board is immediately usable (#175).
    """
    api_admin_required()
    data = CategoryCreate(**request.get_json())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        import uuid

        max_pos = queries.cat_max_position(conn)
        cat_id = str(uuid.uuid4())
        queries.cat_create(
            conn,
            id=cat_id,
            name=data.name,
            color=data.color,
            position=max_pos + 1,
        )
        # Auto-create a first project (#175)
        proj_id = str(uuid.uuid4())
        acronym = data.name[:4].upper() if data.name else "PROJ"
        queries.proj_create(
            conn,
            id=proj_id,
            cat_id=cat_id,
            name=f"Project {data.name}",
            acronym=acronym,
            status="active",
            position=0,
            default_who="",
        )
        row = queries.cat_get_by_id(conn, id=cat_id)
        return jsonify(Category(**row).model_dump()), 201
    finally:
        conn.close()


@bp.route("/<cat_id>", methods=["PATCH"])
def update_category(cat_id: str) -> Any:
    """Update a category (requires write scope on the category)."""
    if not current_user_can(cat_id, "write"):
        return jsonify({"error": "forbidden"}), 403
    data = CategoryUpdate(**request.get_json())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.cat_get_by_id(conn, id=cat_id)
        if not existing:
            return jsonify({"error": "Not found"}), 404
        queries.cat_update(
            conn,
            id=cat_id,
            name=data.name or existing["name"],
            color=data.color or existing["color"],
        )
        # Reorder projects if requested
        if data.project_order:
            for i, proj_id in enumerate(data.project_order):
                queries.proj_update_position(conn, id=proj_id, position=i)
        row = queries.cat_get_by_id(conn, id=cat_id)
        return jsonify(Category(**row).model_dump())
    finally:
        conn.close()


@bp.route("/<cat_id>", methods=["DELETE"])
def delete_category(cat_id: str) -> Any:
    """Delete a category (admin only — destructive, board-wide)."""
    api_admin_required()
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        queries.cat_delete(conn, id=cat_id)
        return "", 204
    finally:
        conn.close()


@bp.route("/reorder", methods=["POST"])
def reorder_categories() -> Any:
    """Reorder categories (admin only — changes global layout)."""
    api_admin_required()
    data = request.get_json()
    old_idx = data["from"]
    new_idx = data["to"]
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        rows = list(queries.cat_get_all(conn))
        ids = [r["id"] for r in rows]
        moved = ids.pop(old_idx)
        ids.insert(new_idx, moved)
        for i, cat_id in enumerate(ids):
            queries.cat_update_position(conn, id=cat_id, position=i)
        return jsonify({"ok": True})
    finally:
        conn.close()

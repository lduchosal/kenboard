"""Category API routes."""

from typing import Any

from flask import Blueprint, jsonify, request

import dashboard.db as db
from dashboard.models.category import Category, CategoryCreate, CategoryUpdate

bp = Blueprint("categories", __name__, url_prefix="/api/v1/categories")


@bp.route("", methods=["GET"])
def list_categories() -> Any:
    """List all categories."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        rows = list(queries.cat_get_all(conn))
        return jsonify([Category(**row).model_dump() for row in rows])
    finally:
        conn.close()


@bp.route("", methods=["POST"])
def create_category() -> Any:
    """Create a new category."""
    data = CategoryCreate(**request.get_json())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        max_pos = queries.cat_max_position(conn)
        cat_id = data.name.lower().replace(" ", "-")
        queries.cat_create(
            conn,
            id=cat_id,
            name=data.name,
            color=data.color,
            position=max_pos + 1,
        )
        row = queries.cat_get_by_id(conn, id=cat_id)
        return jsonify(Category(**row).model_dump()), 201
    finally:
        conn.close()


@bp.route("/<cat_id>", methods=["PATCH"])
def update_category(cat_id: str) -> Any:
    """Update a category."""
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
    """Delete a category."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        queries.cat_delete(conn, id=cat_id)
        return "", 204
    finally:
        conn.close()


@bp.route("/reorder", methods=["POST"])
def reorder_categories() -> Any:
    """Reorder categories."""
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

"""User API routes."""

import uuid
from typing import Any

from argon2 import PasswordHasher
from flask import Blueprint, jsonify, request

import dashboard.db as db
from dashboard.models.user import User, UserCreate, UserUpdate

bp = Blueprint("users", __name__, url_prefix="/api/v1/users")

_hasher = PasswordHasher()


def _hash_password(password: str) -> str:
    """Hash a password using argon2."""
    return _hasher.hash(password)


@bp.route("", methods=["GET"])
def list_users() -> Any:
    """List all users."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        rows = list(queries.usr_get_all(conn))
        return jsonify([User(**row).model_dump(mode="json") for row in rows])
    finally:
        conn.close()


@bp.route("", methods=["POST"])
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
            color=data.color,
            password_hash=password_hash,
            is_admin=int(data.is_admin),
        )
        row = queries.usr_get_by_id(conn, id=user_id)
        return jsonify(User(**row).model_dump(mode="json")), 201
    finally:
        conn.close()


@bp.route("/<user_id>", methods=["PATCH"])
def update_user(user_id: str) -> Any:
    """Update a user."""
    data = UserUpdate(**request.get_json())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.usr_get_by_id(conn, id=user_id)
        if not existing:
            return jsonify({"error": "Not found"}), 404
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
        if data.password:
            queries.usr_update_password(
                conn, id=user_id, password_hash=_hash_password(data.password)
            )
        row = queries.usr_get_by_id(conn, id=user_id)
        return jsonify(User(**row).model_dump(mode="json"))
    finally:
        conn.close()


@bp.route("/<user_id>", methods=["DELETE"])
def delete_user(user_id: str) -> Any:
    """Delete a user."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        queries.usr_delete(conn, id=user_id)
        return "", 204
    finally:
        conn.close()

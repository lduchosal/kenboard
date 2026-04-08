"""API key management routes (``/api/v1/keys``).

These endpoints are reserved to ``KENBOARD_ADMIN_KEY`` (the static key from
``.env``) or to a logged-in Flask-Login session. The auth middleware
(``dashboard.auth``) enforces this on every request.

Creation returns the plain-text key **once**; all subsequent reads only
expose metadata (label, scopes, timestamps).
"""

import secrets
import uuid
from typing import Any

from flask import Blueprint, jsonify, request

import dashboard.db as db
from dashboard.auth import _hash_key
from dashboard.models.api_key import (
    ApiKey,
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyUpdate,
)

bp = Blueprint("keys", __name__, url_prefix="/api/v1/keys")

KEY_PREFIX = "kb_"


def _generate_key() -> str:
    """Generate a fresh bearer key with the kenboard prefix."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


def _row_with_scopes(conn: Any, queries: Any, row: dict[str, Any]) -> dict[str, Any]:
    """Attach the project scopes list to an api_key row dict."""
    scopes = list(queries.key_scopes_get(conn, api_key_id=row["id"]))
    out = row.copy()
    out["scopes"] = [
        {"project_id": s["project_id"], "scope": s["scope"]} for s in scopes
    ]
    return out


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    """Serialize an api_key row (with scopes attached) via Pydantic."""
    return ApiKey(**row).model_dump(mode="json")


@bp.route("", methods=["GET"])
def list_keys() -> Any:
    """List all api_keys (without the plain-text key, ever)."""
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        rows = list(queries.key_get_all(conn))
        return jsonify([_serialize(_row_with_scopes(conn, queries, r)) for r in rows])
    finally:
        conn.close()


@bp.route("", methods=["POST"])
def create_key() -> Any:
    """Create a new api_key.

    Returns the plain-text key ONCE in the response.
    """
    data = ApiKeyCreate(**request.get_json())
    plain = _generate_key()
    key_hash = _hash_key(plain)
    key_id = str(uuid.uuid4())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        queries.key_create(
            conn,
            id=key_id,
            key_hash=key_hash,
            label=data.label,
            expires_at=data.expires_at,
        )
        for s in data.scopes:
            queries.key_scopes_add(
                conn,
                api_key_id=key_id,
                project_id=s.project_id,
                scope=s.scope,
            )
        row = queries.key_get_by_id(conn, id=key_id)
        merged = _row_with_scopes(conn, queries, row)
        merged["key"] = plain
        return jsonify(ApiKeyCreated(**merged).model_dump(mode="json")), 201
    finally:
        conn.close()


@bp.route("/<key_id>", methods=["PATCH"])
def update_key(key_id: str) -> Any:
    """Update label, expires_at, and/or scopes of an api_key."""
    data = ApiKeyUpdate(**request.get_json())
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.key_get_by_id(conn, id=key_id)
        if not existing:
            return jsonify({"error": "Not found"}), 404
        new_label = data.label if data.label is not None else existing["label"]
        # expires_at: model field is `datetime | None`. We can't tell apart
        # "not provided" vs "explicitly cleared". For simplicity, only update
        # expires_at if it differs from the existing value (None ≡ no change).
        # Use a separate `--clear-expires` future flag if we need it.
        new_expires = (
            data.expires_at if data.expires_at is not None else existing["expires_at"]
        )
        queries.key_update_label_expiry(
            conn, id=key_id, label=new_label, expires_at=new_expires
        )
        if data.scopes is not None:
            queries.key_scopes_clear(conn, api_key_id=key_id)
            for s in data.scopes:
                queries.key_scopes_add(
                    conn,
                    api_key_id=key_id,
                    project_id=s.project_id,
                    scope=s.scope,
                )
        row = queries.key_get_by_id(conn, id=key_id)
        return jsonify(_serialize(_row_with_scopes(conn, queries, row)))
    finally:
        conn.close()


@bp.route("/<key_id>", methods=["DELETE"])
def revoke_key(key_id: str) -> Any:
    """Revoke an api_key (sets revoked_at = NOW()).

    Idempotent.
    """
    conn = db.get_connection()
    queries = db.load_queries()
    try:
        existing = queries.key_get_by_id(conn, id=key_id)
        if not existing:
            return jsonify({"error": "Not found"}), 404
        queries.key_revoke(conn, id=key_id)
        return "", 204
    finally:
        conn.close()

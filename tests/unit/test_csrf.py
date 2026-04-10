"""CSRF protection on cookie-authenticated /api/v1/* requests.

The middleware (``dashboard.auth._enforce``) requires unsafe HTTP methods
to be Same-Origin when the caller is authenticated by cookie. Bearer
tokens skip the check.

These tests run with ``LOGIN_DISABLED=False`` so the middleware actually
runs.
"""

from __future__ import annotations

import json

import pytest
from argon2 import PasswordHasher


@pytest.fixture()
def csrf_app(app):
    """Re-enable the auth middleware on the shared app fixture."""
    prev = app.config.get("LOGIN_DISABLED", False)
    app.config["LOGIN_DISABLED"] = False
    yield app
    app.config["LOGIN_DISABLED"] = prev


@pytest.fixture()
def csrf_client(csrf_app):
    """Test client wired to the auth-enabled app."""
    return csrf_app.test_client()


@pytest.fixture()
def logged_in_user(db, queries):
    """Create a user 'csrf_test' with password 'csrfpass123'."""
    h = PasswordHasher().hash("csrfpass123")
    queries.usr_create(
        db,
        id="user-csrf",
        name="csrf_test",
        email=None,
        color="#888",
        password_hash=h,
        is_admin=1,
    )
    return queries.usr_get_by_id(db, id="user-csrf")


@pytest.fixture()
def authed_client(csrf_client, logged_in_user):
    """Test client with an active session cookie for ``csrf_test``."""
    csrf_client.post(
        "/login",
        data={"name": "csrf_test", "password": "csrfpass123"},
        follow_redirects=False,
    )
    return csrf_client


class TestCsrfCookieAuth:
    """Cookie-authenticated requests must be Same-Origin on unsafe methods."""

    def test_post_without_origin_is_rejected(self, authed_client, db):
        r = authed_client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "x", "color": "#000000"}),
            content_type="application/json",
        )
        assert r.status_code == 403
        assert "CSRF" in r.get_json()["error"]

    def test_post_with_foreign_origin_is_rejected(self, authed_client, db):
        r = authed_client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "x", "color": "#000000"}),
            content_type="application/json",
            headers={"Origin": "https://evil.example"},
        )
        assert r.status_code == 403

    def test_post_with_same_origin_is_allowed(self, authed_client, db):
        # The Flask test client uses ``localhost`` as the host by default.
        r = authed_client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "ok", "color": "#000000"}),
            content_type="application/json",
            headers={"Origin": "http://localhost"},
        )
        assert r.status_code == 201

    def test_post_with_same_origin_referer_only_is_allowed(self, authed_client, db):
        r = authed_client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "ok2", "color": "#000000"}),
            content_type="application/json",
            headers={"Referer": "http://localhost/admin/keys"},
        )
        assert r.status_code == 201

    def test_get_does_not_require_origin(self, authed_client, db):
        r = authed_client.get("/api/v1/categories")
        assert r.status_code == 200

    def test_delete_without_origin_is_rejected(self, authed_client, db):
        r = authed_client.delete("/api/v1/categories/anything")
        assert r.status_code == 403

    def test_patch_without_origin_is_rejected(self, authed_client, db):
        r = authed_client.patch(
            "/api/v1/categories/x",
            data=json.dumps({"name": "y"}),
            content_type="application/json",
        )
        assert r.status_code == 403


class TestCsrfBearerAuth:
    """Bearer-token requests skip CSRF: tokens are not auto-attached."""

    def test_bearer_post_without_origin_is_allowed(self, csrf_client, csrf_app, db):
        from dashboard.config import Config

        prev = Config.KENBOARD_ADMIN_KEY
        Config.KENBOARD_ADMIN_KEY = "csrf-bearer-test-key"
        try:
            r = csrf_client.post(
                "/api/v1/categories",
                data=json.dumps({"name": "via-bearer", "color": "#000000"}),
                content_type="application/json",
                headers={"Authorization": "Bearer csrf-bearer-test-key"},
            )
            assert r.status_code == 201
        finally:
            Config.KENBOARD_ADMIN_KEY = prev

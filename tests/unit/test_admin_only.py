"""Admin-only enforcement on cookie-authenticated /api/v1/* requests.

The middleware (``dashboard.auth._enforce``) refuses cookie-authenticated
non-admin users on the admin-only endpoints (``/api/v1/users``,
``/api/v1/keys``, ``/api/v1/categories``, ``/api/v1/projects`` GET/POST).
This protects against:

- self-promotion via ``PATCH /api/v1/users/<self> {is_admin: true}``
- creation of new admins via ``POST /api/v1/users``
- deletion / modification of other users
- listing / creating projects without admin rights

These tests run with ``LOGIN_DISABLED=False`` so the middleware actually
runs.
"""

from __future__ import annotations

import json

import pytest
from argon2 import PasswordHasher

SAME_ORIGIN = {"Origin": "http://localhost"}


@pytest.fixture()
def auth_app(app):
    """Re-enable the auth middleware on the shared app fixture."""
    prev = app.config.get("LOGIN_DISABLED", False)
    app.config["LOGIN_DISABLED"] = False
    yield app
    app.config["LOGIN_DISABLED"] = prev


@pytest.fixture()
def auth_client(auth_app):
    """Test client wired to the auth-enabled app."""
    return auth_app.test_client()


@pytest.fixture()
def admin_user(db, queries):
    """Create an admin user 'adm' with password 'adminpw123'."""
    h = PasswordHasher().hash("adminpw123")
    queries.usr_create(
        db,
        id="user-adm",
        name="adm",
        color="#888",
        password_hash=h,
        is_admin=1,
    )
    return queries.usr_get_by_id(db, id="user-adm")


@pytest.fixture()
def normal_user(db, queries):
    """Create a non-admin user 'norm' with password 'normpw123'."""
    h = PasswordHasher().hash("normpw123")
    queries.usr_create(
        db,
        id="user-norm",
        name="norm",
        color="#888",
        password_hash=h,
        is_admin=0,
    )
    return queries.usr_get_by_id(db, id="user-norm")


@pytest.fixture()
def normal_client(auth_client, normal_user):
    """Test client logged in as the non-admin user."""
    auth_client.post(
        "/login",
        data={"name": "norm", "password": "normpw123"},
        follow_redirects=False,
    )
    return auth_client


@pytest.fixture()
def admin_client(auth_client, admin_user):
    """Test client logged in as the admin user."""
    auth_client.post(
        "/login",
        data={"name": "adm", "password": "adminpw123"},
        follow_redirects=False,
    )
    return auth_client


class TestAdminOnlyAsNormalUser:
    """A non-admin cookie session must NOT reach admin-only endpoints."""

    def test_get_users_rejected(self, normal_client, db):
        r = normal_client.get("/api/v1/users")
        assert r.status_code == 403

    def test_post_users_rejected(self, normal_client, db):
        r = normal_client.post(
            "/api/v1/users",
            data=json.dumps(
                {
                    "name": "new",
                    "color": "#000",
                    "password": "x",
                    "is_admin": True,
                }
            ),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403

    def test_patch_self_to_admin_rejected(self, normal_client, db):
        r = normal_client.patch(
            "/api/v1/users/user-norm",
            data=json.dumps({"is_admin": True}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403

    def test_patch_other_user_rejected(self, normal_client, admin_user, db):
        r = normal_client.patch(
            "/api/v1/users/user-adm",
            data=json.dumps({"name": "hijacked"}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403

    def test_delete_other_user_rejected(self, normal_client, admin_user, db):
        r = normal_client.delete(
            "/api/v1/users/user-adm",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403

    def test_get_keys_rejected(self, normal_client, db):
        r = normal_client.get("/api/v1/keys")
        assert r.status_code == 403

    def test_post_keys_rejected(self, normal_client, db):
        r = normal_client.post(
            "/api/v1/keys",
            data=json.dumps({"label": "x", "scopes": []}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403

    def test_get_categories_rejected(self, normal_client, db):
        r = normal_client.get("/api/v1/categories")
        assert r.status_code == 403

    def test_post_categories_rejected(self, normal_client, db):
        r = normal_client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "x", "color": "#000000"}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403

    def test_get_projects_rejected(self, normal_client, db):
        r = normal_client.get("/api/v1/projects")
        assert r.status_code == 403

    def test_post_projects_rejected(self, normal_client, db):
        r = normal_client.post(
            "/api/v1/projects",
            data=json.dumps(
                {
                    "cat": "x",
                    "name": "y",
                    "acronym": "PWN",
                    "status": "active",
                    "default_who": "",
                }
            ),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403


class TestAdminOnlyAsAdminUser:
    """An admin cookie session must still be allowed on admin-only endpoints."""

    def test_get_users_allowed(self, admin_client, db):
        r = admin_client.get("/api/v1/users")
        assert r.status_code == 200

    def test_get_keys_allowed(self, admin_client, db):
        r = admin_client.get("/api/v1/keys")
        assert r.status_code == 200

    def test_get_categories_allowed(self, admin_client, db):
        r = admin_client.get("/api/v1/categories")
        assert r.status_code == 200

    def test_post_categories_allowed(self, admin_client, db):
        r = admin_client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "ok", "color": "#000000"}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 201

    def test_patch_user_allowed(self, admin_client, normal_user, db):
        """Regression #131: admin must be able to PATCH another user."""
        r = admin_client.patch(
            "/api/v1/users/user-norm",
            data=json.dumps({"color": "#abcdef"}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 200, r.get_data(as_text=True)

    def test_delete_user_allowed(self, admin_client, normal_user, db):
        """Regression #131: admin must be able to DELETE another user."""
        r = admin_client.delete(
            "/api/v1/users/user-norm",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 204, r.get_data(as_text=True)

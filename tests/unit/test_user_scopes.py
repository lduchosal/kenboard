"""Per-user category scope enforcement (#197).

Covers the cookie-authenticated path only. API-key scoping is already
covered by ``test_api_keys.py`` and stays at the project level (not
touched by this feature).
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
    """Create an admin user 'adm'."""
    h = PasswordHasher().hash("adminpw123")
    queries.usr_create(
        db,
        id="user-adm",
        name="adm",
        email=None,
        color="#888",
        password_hash=h,
        is_admin=1,
    )
    return queries.usr_get_by_id(db, id="user-adm")


@pytest.fixture()
def normal_user(db, queries):
    """Create a non-admin user 'norm'."""
    h = PasswordHasher().hash("normpw123")
    queries.usr_create(
        db,
        id="user-norm",
        name="norm",
        email=None,
        color="#888",
        password_hash=h,
        is_admin=0,
    )
    return queries.usr_get_by_id(db, id="user-norm")


@pytest.fixture()
def seed_two_categories(db, queries):
    """Insert two categories and a project in each."""
    queries.cat_create(db, id="cat-a", name="Alpha", color="#ffaaaa", position=0)
    queries.cat_create(db, id="cat-b", name="Beta", color="#aaffaa", position=1)
    queries.proj_create(
        db,
        id="proj-a",
        cat_id="cat-a",
        name="ProjA",
        acronym="A",
        status="active",
        position=0,
        default_who="",
    )
    queries.proj_create(
        db,
        id="proj-b",
        cat_id="cat-b",
        name="ProjB",
        acronym="B",
        status="active",
        position=0,
        default_who="",
    )
    return {"cat_a": "cat-a", "cat_b": "cat-b", "proj_a": "proj-a", "proj_b": "proj-b"}


def _login(client, name, password):
    return client.post(
        "/login",
        data={"name": name, "password": password},
        follow_redirects=False,
    )


# -- Helpers ------------------------------------------------------------------


def _grant(queries, db, user_id, category_id, scope):
    queries.usr_scopes_add(db, user_id=user_id, category_id=category_id, scope=scope)


# -- List filtering -----------------------------------------------------------


class TestListFiltering:
    """Non-admin users only see categories / projects they're scoped on."""

    def test_non_admin_without_any_scope_sees_empty_list(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _login(auth_client, "norm", "normpw123")
        r = auth_client.get("/api/v1/categories", headers=SAME_ORIGIN)
        assert r.status_code == 200
        assert r.get_json() == []

    def test_non_admin_with_read_on_a_sees_only_a(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "read")
        _login(auth_client, "norm", "normpw123")
        r = auth_client.get("/api/v1/categories", headers=SAME_ORIGIN)
        assert r.status_code == 200
        ids = [c["id"] for c in r.get_json()]
        assert ids == ["cat-a"]

    def test_admin_sees_all_categories(
        self, auth_client, db, queries, admin_user, seed_two_categories
    ):
        _login(auth_client, "adm", "adminpw123")
        r = auth_client.get("/api/v1/categories", headers=SAME_ORIGIN)
        assert r.status_code == 200
        ids = sorted(c["id"] for c in r.get_json())
        assert ids == ["cat-a", "cat-b"]

    def test_non_admin_projects_without_scope_is_empty(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _login(auth_client, "norm", "normpw123")
        r = auth_client.get("/api/v1/projects", headers=SAME_ORIGIN)
        assert r.status_code == 200
        assert r.get_json() == []

    def test_non_admin_projects_filtered_by_cat_scope(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "read")
        _login(auth_client, "norm", "normpw123")
        r = auth_client.get("/api/v1/projects", headers=SAME_ORIGIN)
        assert r.status_code == 200
        ids = [p["id"] for p in r.get_json()]
        assert ids == ["proj-a"]


# -- Direct access checks -----------------------------------------------------


class TestReadEnforcement:
    """GET on a specific resource checks read scope."""

    def test_projects_by_cat_forbidden_without_scope(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _login(auth_client, "norm", "normpw123")
        r = auth_client.get("/api/v1/projects?cat=cat-a", headers=SAME_ORIGIN)
        assert r.status_code == 403

    def test_projects_by_cat_allowed_with_read(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "read")
        _login(auth_client, "norm", "normpw123")
        r = auth_client.get("/api/v1/projects?cat=cat-a", headers=SAME_ORIGIN)
        assert r.status_code == 200

    def test_tasks_forbidden_without_scope(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _login(auth_client, "norm", "normpw123")
        r = auth_client.get("/api/v1/tasks?project=proj-a", headers=SAME_ORIGIN)
        assert r.status_code == 403

    def test_tasks_allowed_with_read(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "read")
        _login(auth_client, "norm", "normpw123")
        r = auth_client.get("/api/v1/tasks?project=proj-a", headers=SAME_ORIGIN)
        assert r.status_code == 200


class TestWriteEnforcement:
    """PATCH / POST / DELETE check write scope (read is not enough)."""

    def test_read_cannot_patch_category(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "read")
        _login(auth_client, "norm", "normpw123")
        r = auth_client.patch(
            "/api/v1/categories/cat-a",
            data=json.dumps({"name": "Renamed"}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403

    def test_write_can_patch_category(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "write")
        _login(auth_client, "norm", "normpw123")
        r = auth_client.patch(
            "/api/v1/categories/cat-a",
            data=json.dumps({"name": "Renamed"}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 200

    def test_non_admin_cannot_create_category_even_with_write(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        """Creating a new board is admin-only — no existing category scope applies."""
        _grant(queries, db, "user-norm", "cat-a", "write")
        _login(auth_client, "norm", "normpw123")
        r = auth_client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "New", "color": "#111111"}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403

    def test_non_admin_cannot_delete_category(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "write")
        _login(auth_client, "norm", "normpw123")
        r = auth_client.delete("/api/v1/categories/cat-a", headers=SAME_ORIGIN)
        assert r.status_code == 403

    def test_admin_can_delete_category(
        self, auth_client, db, queries, admin_user, seed_two_categories
    ):
        _login(auth_client, "adm", "adminpw123")
        r = auth_client.delete("/api/v1/categories/cat-a", headers=SAME_ORIGIN)
        assert r.status_code == 204


# -- Cross-category move ------------------------------------------------------


class TestCrossCategoryMove:
    """Moving a project to another category needs write on both."""

    def test_move_requires_write_on_destination(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "write")
        _grant(queries, db, "user-norm", "cat-b", "read")
        _login(auth_client, "norm", "normpw123")
        r = auth_client.patch(
            "/api/v1/projects/proj-a",
            data=json.dumps({"cat": "cat-b"}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403

    def test_move_allowed_with_write_on_both(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "write")
        _grant(queries, db, "user-norm", "cat-b", "write")
        _login(auth_client, "norm", "normpw123")
        r = auth_client.patch(
            "/api/v1/projects/proj-a",
            data=json.dumps({"cat": "cat-b"}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 200


# -- Scope mutation endpoint --------------------------------------------------


class TestScopesEndpoint:
    """PUT /api/v1/users/<id>/scopes is admin-only and atomic."""

    def test_non_admin_cannot_put_scopes(
        self, auth_client, db, queries, normal_user, seed_two_categories
    ):
        _login(auth_client, "norm", "normpw123")
        r = auth_client.put(
            f"/api/v1/users/{normal_user['id']}/scopes",
            data=json.dumps({"scopes": []}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 403

    def test_admin_can_replace_scopes(
        self, auth_client, db, queries, admin_user, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "read")
        _login(auth_client, "adm", "adminpw123")
        r = auth_client.put(
            f"/api/v1/users/{normal_user['id']}/scopes",
            data=json.dumps(
                {
                    "scopes": [
                        {"category_id": "cat-b", "scope": "write"},
                    ]
                }
            ),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["scopes"] == [{"category_id": "cat-b", "scope": "write"}]
        # The previous read on cat-a was replaced, not kept.
        rows = list(queries.usr_scopes_get(db, user_id="user-norm"))
        assert len(rows) == 1
        assert rows[0]["category_id"] == "cat-b"

    def test_admin_sets_empty_scopes_removes_all(
        self, auth_client, db, queries, admin_user, normal_user, seed_two_categories
    ):
        _grant(queries, db, "user-norm", "cat-a", "write")
        _login(auth_client, "adm", "adminpw123")
        r = auth_client.put(
            f"/api/v1/users/{normal_user['id']}/scopes",
            data=json.dumps({"scopes": []}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert r.status_code == 200
        rows = list(queries.usr_scopes_get(db, user_id="user-norm"))
        assert rows == []


# -- API-key regression -------------------------------------------------------


class TestApiKeyPathUnchanged:
    """Adding user scopes must not affect API-key authentication."""

    def test_admin_key_still_bypasses(
        self, auth_client, db, queries, seed_two_categories, monkeypatch
    ):
        # Route the admin static key through the header — auth.py accepts it
        # when present and matching Config.KENBOARD_ADMIN_KEY.
        from dashboard.config import Config

        monkeypatch.setattr(Config, "KENBOARD_ADMIN_KEY", "STATIC-ADMIN")
        r = auth_client.get(
            "/api/v1/categories",
            headers={"Authorization": "Bearer STATIC-ADMIN", **SAME_ORIGIN},
        )
        assert r.status_code == 200
        ids = sorted(c["id"] for c in r.get_json())
        assert ids == ["cat-a", "cat-b"]

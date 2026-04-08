"""Unit tests for /api/v1/keys CRUD and the auth middleware behaviour."""

import json

import pytest

from dashboard.auth import _hash_key, _scope_satisfies
from dashboard.config import Config


@pytest.fixture()
def admin_key(monkeypatch):
    """Set a known admin key in Config and return it."""
    monkeypatch.setattr(Config, "KENBOARD_ADMIN_KEY", "kb_admin_static_test")
    return "kb_admin_static_test"


@pytest.fixture()
def project(client, db, queries):
    """Create a category and a project, return the project_id."""
    queries.cat_create(db, id="cat-1", name="Tech", color="#0969da", position=0)
    queries.proj_create(
        db,
        id="proj-1",
        cat_id="cat-1",
        name="Demo",
        acronym="DEMO",
        status="active",
        position=0,
        default_who="",
    )
    return "proj-1"


# -- Helpers ------------------------------------------------------------------


class TestScopeSatisfies:
    """The scope ordering helper."""

    def test_admin_grants_write(self):
        assert _scope_satisfies("admin", "write") is True

    def test_write_grants_read(self):
        assert _scope_satisfies("write", "read") is True

    def test_read_does_not_grant_write(self):
        assert _scope_satisfies("read", "write") is False

    def test_unknown_scope_denies(self):
        assert _scope_satisfies("none", "read") is False


class TestHashKey:
    """Sha256 hash helper."""

    def test_deterministic(self):
        assert _hash_key("k") == _hash_key("k")

    def test_different_keys_different_hashes(self):
        assert _hash_key("a") != _hash_key("b")

    def test_length(self):
        assert len(_hash_key("anything")) == 64


# -- /api/v1/keys CRUD --------------------------------------------------------


class TestKeysCRUD:
    """Create / list / update / revoke api_keys."""

    def test_list_empty(self, client, db):
        r = client.get("/api/v1/keys")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_create_returns_key_once(self, client, db):
        r = client.post(
            "/api/v1/keys",
            data=json.dumps({"label": "ci", "scopes": []}),
            content_type="application/json",
        )
        assert r.status_code == 201
        body = r.get_json()
        assert body["label"] == "ci"
        assert body["key"].startswith("kb_")
        assert len(body["key"]) > 10
        assert "key_hash" not in body

    def test_create_with_scopes(self, client, db, project):
        r = client.post(
            "/api/v1/keys",
            data=json.dumps(
                {
                    "label": "scoped",
                    "scopes": [{"project_id": project, "scope": "write"}],
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 201
        body = r.get_json()
        assert len(body["scopes"]) == 1
        assert body["scopes"][0]["project_id"] == project
        assert body["scopes"][0]["scope"] == "write"

    def test_list_after_create_strips_key(self, client, db):
        client.post(
            "/api/v1/keys",
            data=json.dumps({"label": "x", "scopes": []}),
            content_type="application/json",
        )
        r = client.get("/api/v1/keys")
        assert r.status_code == 200
        rows = r.get_json()
        assert len(rows) == 1
        assert "key" not in rows[0]
        assert "key_hash" not in rows[0]

    def test_update_label(self, client, db):
        created = client.post(
            "/api/v1/keys",
            data=json.dumps({"label": "old", "scopes": []}),
            content_type="application/json",
        ).get_json()
        r = client.patch(
            f"/api/v1/keys/{created['id']}",
            data=json.dumps({"label": "new"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.get_json()["label"] == "new"

    def test_update_scopes_replaces(self, client, db, project):
        created = client.post(
            "/api/v1/keys",
            data=json.dumps(
                {
                    "label": "k",
                    "scopes": [{"project_id": project, "scope": "read"}],
                }
            ),
            content_type="application/json",
        ).get_json()
        r = client.patch(
            f"/api/v1/keys/{created['id']}",
            data=json.dumps({"scopes": [{"project_id": project, "scope": "admin"}]}),
            content_type="application/json",
        )
        assert r.status_code == 200
        scopes = r.get_json()["scopes"]
        assert len(scopes) == 1
        assert scopes[0]["scope"] == "admin"

    def test_revoke_sets_revoked_at(self, client, db, queries):
        created = client.post(
            "/api/v1/keys",
            data=json.dumps({"label": "rev", "scopes": []}),
            content_type="application/json",
        ).get_json()
        r = client.delete(f"/api/v1/keys/{created['id']}")
        assert r.status_code == 204
        # Verify in DB
        row = queries.key_get_by_id(db, id=created["id"])
        assert row["revoked_at"] is not None

    def test_update_not_found(self, client, db):
        r = client.patch(
            "/api/v1/keys/missing",
            data=json.dumps({"label": "x"}),
            content_type="application/json",
        )
        assert r.status_code == 404

    def test_revoke_not_found(self, client, db):
        r = client.delete("/api/v1/keys/missing")
        assert r.status_code == 404


# -- Middleware enforcement ---------------------------------------------------


@pytest.fixture()
def enforced_app(app):
    """Re-enable the API auth middleware for one test (LOGIN_DISABLED=False)."""
    prev = app.config.get("LOGIN_DISABLED", False)
    app.config["LOGIN_DISABLED"] = False
    yield app
    app.config["LOGIN_DISABLED"] = prev


@pytest.fixture()
def enforced_client(enforced_app):
    """Test client wired to the auth-enforcing app."""
    return enforced_app.test_client()


@pytest.fixture()
def make_api_key(db, queries):
    """Create an api_key row directly via SQL and return ``(id, plain_key)``.

    Used by enforced-mode tests because POST /api/v1/keys is itself
    middleware-protected (admin-only) and the session-scoped app shared
    between ``client`` and ``enforced_client`` makes the HTTP setup path
    awkward.
    """
    import secrets
    import uuid

    from dashboard.auth import _hash_key

    def _make(scopes: list[dict[str, str]] | None = None) -> tuple[str, str]:
        plain = "kb_" + secrets.token_urlsafe(32)
        key_id = str(uuid.uuid4())
        queries.key_create(
            db, id=key_id, key_hash=_hash_key(plain), label="test", expires_at=None
        )
        for s in scopes or []:
            queries.key_scopes_add(
                db, api_key_id=key_id, project_id=s["project_id"], scope=s["scope"]
            )
        return key_id, plain

    return _make


class TestMiddlewareEnforced:
    """The auth middleware is always enforced when LOGIN_DISABLED is False."""

    def test_no_token_blocked(self, enforced_client, client, db, project):
        # Note: ``client`` is needed to keep the same DB fixture chain.
        r = enforced_client.get(f"/api/v1/tasks?project={project}")
        assert r.status_code == 401

    def test_admin_key_passes_everywhere(
        self, enforced_client, client, db, project, admin_key
    ):
        r = enforced_client.get(
            f"/api/v1/tasks?project={project}",
            headers={"Authorization": f"Bearer {admin_key}"},
        )
        assert r.status_code == 200
        r = enforced_client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {admin_key}"}
        )
        assert r.status_code == 200

    def test_admin_endpoint_rejects_normal_key(self, enforced_client, db, make_api_key):
        _, plain_key = make_api_key()
        r = enforced_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {plain_key}"},
        )
        assert r.status_code == 403

    def test_invalid_token_blocked(self, enforced_client, db, project):
        r = enforced_client.get(
            f"/api/v1/tasks?project={project}",
            headers={"Authorization": "Bearer kb_garbage"},
        )
        assert r.status_code == 401

    def test_revoked_key_blocked(
        self, enforced_client, db, project, queries, make_api_key
    ):
        key_id, plain_key = make_api_key(
            scopes=[{"project_id": project, "scope": "read"}]
        )
        queries.key_revoke(db, id=key_id)
        r = enforced_client.get(
            f"/api/v1/tasks?project={project}",
            headers={"Authorization": f"Bearer {plain_key}"},
        )
        assert r.status_code == 401

    def test_read_scope_can_get_but_not_post(
        self, enforced_client, db, project, make_api_key
    ):
        _, plain_key = make_api_key(scopes=[{"project_id": project, "scope": "read"}])
        # GET with read scope → OK
        r = enforced_client.get(
            f"/api/v1/tasks?project={project}",
            headers={"Authorization": f"Bearer {plain_key}"},
        )
        assert r.status_code == 200
        # POST with read scope → 403
        r = enforced_client.post(
            "/api/v1/tasks",
            data=json.dumps({"project_id": project, "title": "X"}),
            content_type="application/json",
            headers={"Authorization": f"Bearer {plain_key}"},
        )
        assert r.status_code == 403

    def test_write_scope_can_post(self, enforced_client, db, project, make_api_key):
        _, plain_key = make_api_key(scopes=[{"project_id": project, "scope": "write"}])
        r = enforced_client.post(
            "/api/v1/tasks",
            data=json.dumps({"project_id": project, "title": "X"}),
            content_type="application/json",
            headers={"Authorization": f"Bearer {plain_key}"},
        )
        assert r.status_code == 201

    def test_wrong_project_scope_blocked(
        self, enforced_client, db, project, queries, make_api_key
    ):
        # Create a second project
        queries.cat_create(db, id="cat-2", name="Other", color="#bf8700", position=1)
        queries.proj_create(
            db,
            id="proj-2",
            cat_id="cat-2",
            name="Other",
            acronym="OTH",
            status="active",
            position=0,
            default_who="",
        )
        _, plain_key = make_api_key(scopes=[{"project_id": "proj-2", "scope": "read"}])
        # Try to read proj-1 with proj-2 scope → 403
        r = enforced_client.get(
            f"/api/v1/tasks?project={project}",
            headers={"Authorization": f"Bearer {plain_key}"},
        )
        assert r.status_code == 403

    def test_last_used_at_is_updated(
        self, enforced_client, db, project, queries, make_api_key
    ):
        key_id, plain_key = make_api_key(
            scopes=[{"project_id": project, "scope": "read"}]
        )
        row_before = queries.key_get_by_id(db, id=key_id)
        assert row_before["last_used_at"] is None
        enforced_client.get(
            f"/api/v1/tasks?project={project}",
            headers={"Authorization": f"Bearer {plain_key}"},
        )
        row_after = queries.key_get_by_id(db, id=key_id)
        assert row_after["last_used_at"] is not None

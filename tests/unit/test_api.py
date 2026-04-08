"""Test Flask API routes."""

import json


class TestCategoryAPI:
    """Test category API endpoints."""

    def test_list_empty(self, client, db):
        resp = client.get("/api/v1/categories")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_create(self, client, db):
        resp = client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "Tech", "color": "var(--accent)"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Tech"
        assert data["color"] == "var(--accent)"
        assert data["position"] == 0

    def test_create_and_list(self, client, db):
        client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "A", "color": "#ff0000"}),
            content_type="application/json",
        )
        client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "B", "color": "#0000ff"}),
            content_type="application/json",
        )
        resp = client.get("/api/v1/categories")
        data = resp.get_json()
        assert len(data) == 2

    def test_create_rejects_css_injection(self, client, db):
        for bad in [
            "red",  # CSS named color, no longer allowed
            "red;background:url('//evil/?x')",
            "#xyz123",  # not hex
            "var(--accent);background:url('//evil')",
            "javascript:alert(1)",
        ]:
            resp = client.post(
                "/api/v1/categories",
                data=json.dumps({"name": "X", "color": bad}),
                content_type="application/json",
            )
            assert resp.status_code == 422, f"expected 422 for color={bad!r}"

    def test_update(self, client, db, queries):
        queries.cat_create(db, id="upd", name="Old", color="red", position=0)
        resp = client.patch(
            "/api/v1/categories/upd",
            data=json.dumps({"name": "New"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "New"

    def test_update_not_found(self, client, db):
        resp = client.patch(
            "/api/v1/categories/nonexistent",
            data=json.dumps({"name": "X"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_delete(self, client, db, queries):
        queries.cat_create(db, id="del", name="Del", color="red", position=0)
        resp = client.delete("/api/v1/categories/del")
        assert resp.status_code == 204

    def test_reorder(self, client, db, queries):
        queries.cat_create(db, id="a", name="A", color="r", position=0)
        queries.cat_create(db, id="b", name="B", color="r", position=1)
        queries.cat_create(db, id="c", name="C", color="r", position=2)
        resp = client.post(
            "/api/v1/categories/reorder",
            data=json.dumps({"from": 0, "to": 2}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        cats = client.get("/api/v1/categories").get_json()
        ids = [c["id"] for c in cats]
        assert ids == ["b", "c", "a"]

    def test_create_invalid_missing_name(self, client, db):
        resp = client.post(
            "/api/v1/categories",
            data=json.dumps({"color": "red"}),
            content_type="application/json",
        )
        assert resp.status_code == 422


class TestProjectAPI:
    """Test project API endpoints."""

    def test_create(self, client, db, queries):
        queries.cat_create(db, id="cat", name="Cat", color="r", position=0)
        resp = client.post(
            "/api/v1/projects",
            data=json.dumps({"name": "My Project", "acronym": "PROJ", "cat": "cat"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["acronym"] == "PROJ"
        assert data["status"] == "active"

    def test_list_by_cat(self, client, db, queries):
        queries.cat_create(db, id="cat", name="Cat", color="r", position=0)
        queries.proj_create(
            db,
            id="p1",
            cat_id="cat",
            name="P1",
            acronym="PP",
            status="active",
            position=0,
            default_who="",
        )
        resp = client.get("/api/v1/projects?cat=cat")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1

    def test_create_rejects_html_in_name(self, client, db, queries):
        queries.cat_create(db, id="cat", name="Cat", color="r", position=0)
        resp = client.post(
            "/api/v1/projects",
            data=json.dumps(
                {
                    "name": "<img src=x onerror=alert(1)>",
                    "acronym": "PROJ",
                    "cat": "cat",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_create_rejects_script_close_in_name(self, client, db, queries):
        queries.cat_create(db, id="cat", name="Cat", color="r", position=0)
        resp = client.post(
            "/api/v1/projects",
            data=json.dumps(
                {
                    "name": "</script><script>alert(1)</script>",
                    "acronym": "PROJ",
                    "cat": "cat",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_delete_with_tasks_fails(self, client, db, queries, seed_task):
        resp = client.delete("/api/v1/projects/test-proj")
        assert resp.status_code == 400

    def test_delete_empty_project(self, client, db, queries, seed_project):
        resp = client.delete("/api/v1/projects/test-proj")
        assert resp.status_code == 204

    def test_patch_project_reorders_siblings(self, client, db, queries):
        """#71: PATCH /projects/<id> with project_order rewrites positions."""
        queries.cat_create(db, id="cat", name="Cat", color="r", position=0)
        queries.proj_create(
            db,
            id="p-a",
            cat_id="cat",
            name="A",
            acronym="A",
            status="active",
            position=0,
            default_who="",
        )
        queries.proj_create(
            db,
            id="p-b",
            cat_id="cat",
            name="B",
            acronym="B",
            status="active",
            position=1,
            default_who="",
        )
        queries.proj_create(
            db,
            id="p-c",
            cat_id="cat",
            name="C",
            acronym="C",
            status="active",
            position=2,
            default_who="",
        )
        resp = client.patch(
            "/api/v1/projects/p-a",
            data=json.dumps({"project_order": ["p-c", "p-b", "p-a"]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        rows = list(queries.proj_get_by_cat(db, cat_id="cat"))
        assert [r["id"] for r in rows] == ["p-c", "p-b", "p-a"]


class TestCategoryProjectReorder:
    """#71: PATCH /categories/<id> reorders the projects it owns."""

    def test_patch_category_reorders_its_projects(self, client, db, queries):
        queries.cat_create(db, id="cat", name="Cat", color="r", position=0)
        queries.proj_create(
            db,
            id="p-a",
            cat_id="cat",
            name="A",
            acronym="A",
            status="active",
            position=0,
            default_who="",
        )
        queries.proj_create(
            db,
            id="p-b",
            cat_id="cat",
            name="B",
            acronym="B",
            status="active",
            position=1,
            default_who="",
        )
        resp = client.patch(
            "/api/v1/categories/cat",
            data=json.dumps({"project_order": ["p-b", "p-a"]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        rows = list(queries.proj_get_by_cat(db, cat_id="cat"))
        assert [r["id"] for r in rows] == ["p-b", "p-a"]

    def test_patch_category_ignores_camelcase_alias(self, client, db, queries):
        """Sending the legacy camelCase ``projectOrder`` is silently dropped.

        This is the failure mode that #71 fixed in app.js: Pydantic v2
        ignores unknown fields, so the reorder was lost without any error.
        The test pins the contract: the canonical field is snake_case.
        """
        queries.cat_create(db, id="cat", name="Cat", color="r", position=0)
        queries.proj_create(
            db,
            id="p-a",
            cat_id="cat",
            name="A",
            acronym="A",
            status="active",
            position=0,
            default_who="",
        )
        queries.proj_create(
            db,
            id="p-b",
            cat_id="cat",
            name="B",
            acronym="B",
            status="active",
            position=1,
            default_who="",
        )
        resp = client.patch(
            "/api/v1/categories/cat",
            data=json.dumps({"projectOrder": ["p-b", "p-a"]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        # Order unchanged → confirms camelCase is silently ignored.
        rows = list(queries.proj_get_by_cat(db, cat_id="cat"))
        assert [r["id"] for r in rows] == ["p-a", "p-b"]


class TestTaskAPI:
    """Test task API endpoints."""

    def test_list_requires_project(self, client, db):
        resp = client.get("/api/v1/tasks")
        assert resp.status_code == 400

    def test_create(self, client, db, queries, seed_project):
        resp = client.post(
            "/api/v1/tasks",
            data=json.dumps(
                {"project_id": "test-proj", "title": "New Task", "status": "todo"}
            ),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "New Task"
        assert data["id"] > 0

    def test_update_status(self, client, db, queries, seed_task):
        task_id = seed_task["id"]
        resp = client.patch(
            f"/api/v1/tasks/{task_id}",
            data=json.dumps({"status": "doing", "position": 0}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "doing"

    def test_create_rejects_html_in_title(self, client, db, queries, seed_project):
        resp = client.post(
            "/api/v1/tasks",
            data=json.dumps(
                {
                    "project_id": "test-proj",
                    "title": "<img src=x onerror=alert(1)>",
                    "status": "todo",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_update_rejects_html_in_title(self, client, db, queries, seed_task):
        task_id = seed_task["id"]
        resp = client.patch(
            f"/api/v1/tasks/{task_id}",
            data=json.dumps({"title": "ok <evil>"}),
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_delete(self, client, db, queries, seed_task):
        task_id = seed_task["id"]
        resp = client.delete(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 204

    def test_list_by_project(self, client, db, queries, seed_task):
        resp = client.get("/api/v1/tasks?project=test-proj")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Task"


class TestUserAPI:
    """Test user API endpoints."""

    def test_list_empty(self, client, db):
        resp = client.get("/api/v1/users")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_create(self, client, db):
        resp = client.post(
            "/api/v1/users",
            data=json.dumps(
                {
                    "name": "Q",
                    "color": "#0969da",
                    "password": "secret",
                    "is_admin": True,
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Q"
        assert data["color"] == "#0969da"
        assert data["is_admin"] is True
        assert "password" not in data
        assert "password_hash" not in data

    def test_create_without_password(self, client, db):
        resp = client.post(
            "/api/v1/users",
            data=json.dumps({"name": "Alice", "color": "#8250df"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.get_json()["is_admin"] is False

    def test_create_duplicate_name(self, client, db):
        client.post(
            "/api/v1/users",
            data=json.dumps({"name": "Bob", "color": "#bf8700"}),
            content_type="application/json",
        )
        resp = client.post(
            "/api/v1/users",
            data=json.dumps({"name": "Bob", "color": "#000000"}),
            content_type="application/json",
        )
        assert resp.status_code == 409

    def test_password_is_hashed(self, client, db, queries):
        client.post(
            "/api/v1/users",
            data=json.dumps(
                {"name": "Claire", "color": "#1a7f37", "password": "topsecret"}
            ),
            content_type="application/json",
        )
        row = queries.usr_get_by_name(db, name="Claire")
        assert row is not None
        assert row["password_hash"] != ""
        assert row["password_hash"] != "topsecret"
        # Argon2 hash starts with $argon2
        assert row["password_hash"].startswith("$argon2")

    def test_update_color(self, client, db):
        created = client.post(
            "/api/v1/users",
            data=json.dumps({"name": "Dave", "color": "#000000"}),
            content_type="application/json",
        ).get_json()
        resp = client.patch(
            f"/api/v1/users/{created['id']}",
            data=json.dumps({"color": "#ffffff"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["color"] == "#ffffff"

    def test_patch_ignores_password_field(self, client, db, queries):
        """#53: PATCH /api/v1/users/<id> must NOT change the password.

        Password changes go through the dedicated routes ``/password`` (self-service)
        and ``/reset-password`` (admin) so that the old password is verified and the
        surface for mass-assignment attacks is closed.
        """
        created = client.post(
            "/api/v1/users",
            data=json.dumps(
                {"name": "Eve", "color": "#abcdef", "password": "oldsecret"}
            ),
            content_type="application/json",
        ).get_json()
        old_hash = queries.usr_get_by_name(db, name="Eve")["password_hash"]
        # Sneak `password` through PATCH — extra fields are dropped silently.
        resp = client.patch(
            f"/api/v1/users/{created['id']}",
            data=json.dumps({"name": "Eve2", "password": "newsecret"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        new_hash = queries.usr_get_by_name(db, name="Eve2")["password_hash"]
        assert new_hash == old_hash

    def test_update_not_found(self, client, db):
        resp = client.patch(
            "/api/v1/users/nonexistent",
            data=json.dumps({"name": "X"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_update_rename_collision(self, client, db):
        a = client.post(
            "/api/v1/users",
            data=json.dumps({"name": "Frank", "color": "#000"}),
            content_type="application/json",
        ).get_json()
        client.post(
            "/api/v1/users",
            data=json.dumps({"name": "Grace", "color": "#000"}),
            content_type="application/json",
        )
        resp = client.patch(
            f"/api/v1/users/{a['id']}",
            data=json.dumps({"name": "Grace"}),
            content_type="application/json",
        )
        assert resp.status_code == 409

    def test_delete(self, client, db):
        created = client.post(
            "/api/v1/users",
            data=json.dumps({"name": "Heidi", "color": "#fff"}),
            content_type="application/json",
        ).get_json()
        resp = client.delete(f"/api/v1/users/{created['id']}")
        assert resp.status_code == 204
        listing = client.get("/api/v1/users").get_json()
        assert all(u["id"] != created["id"] for u in listing)


class TestPasswordChange:
    """#53: dedicated routes for password changes.

    LOGIN_DISABLED=True (test default) bypasses the ownership/admin
    checks so we can exercise the route logic without juggling sessions.
    The session-bound branches (owner check, admin check) are covered by
    e2e tests in ``tests/e2e/test_auth_user.py``.
    """

    def _create_user(self, client, name="Pwd", password="oldsecret123"):
        return client.post(
            "/api/v1/users",
            data=json.dumps({"name": name, "color": "#abcdef", "password": password}),
            content_type="application/json",
        ).get_json()

    def test_change_password_with_correct_old(self, client, db, queries):
        u = self._create_user(client, name="ChgOk")
        resp = client.post(
            f"/api/v1/users/{u['id']}/password",
            data=json.dumps(
                {"old_password": "oldsecret123", "new_password": "newsecret456"}
            ),
            content_type="application/json",
        )
        assert resp.status_code == 204
        # The new password verifies against the stored hash
        from argon2 import PasswordHasher

        row = queries.usr_get_by_name(db, name="ChgOk")
        PasswordHasher().verify(row["password_hash"], "newsecret456")

    def test_change_password_with_wrong_old(self, client, db):
        u = self._create_user(client, name="ChgKO")
        resp = client.post(
            f"/api/v1/users/{u['id']}/password",
            data=json.dumps(
                {"old_password": "wrongone", "new_password": "newsecret456"}
            ),
            content_type="application/json",
        )
        assert resp.status_code == 401
        assert "wrong old password" in resp.get_json()["error"]

    def test_change_password_user_without_existing(self, client, db):
        # Create a user without a password set, then try to "change" it.
        u = client.post(
            "/api/v1/users",
            data=json.dumps({"name": "NoPwd", "color": "#abcdef"}),
            content_type="application/json",
        ).get_json()
        resp = client.post(
            f"/api/v1/users/{u['id']}/password",
            data=json.dumps(
                {"old_password": "anything", "new_password": "newsecret456"}
            ),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "no password set" in resp.get_json()["error"]

    def test_change_password_not_found(self, client, db):
        resp = client.post(
            "/api/v1/users/missing-id/password",
            data=json.dumps({"old_password": "x", "new_password": "newsecret456"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_change_password_too_short(self, client, db):
        u = self._create_user(client, name="Short")
        resp = client.post(
            f"/api/v1/users/{u['id']}/password",
            data=json.dumps({"old_password": "oldsecret123", "new_password": "short"}),
            content_type="application/json",
        )
        # Pydantic min_length=8 → 422
        assert resp.status_code == 422


class TestPasswordReset:
    """#53: admin-only password reset (no old password required)."""

    def test_reset_changes_hash(self, client, db, queries):
        u = client.post(
            "/api/v1/users",
            data=json.dumps(
                {"name": "Reset", "color": "#abcdef", "password": "originalpw"}
            ),
            content_type="application/json",
        ).get_json()
        old_hash = queries.usr_get_by_name(db, name="Reset")["password_hash"]
        resp = client.post(
            f"/api/v1/users/{u['id']}/reset-password",
            data=json.dumps({"new_password": "freshpassword"}),
            content_type="application/json",
        )
        assert resp.status_code == 204
        new_hash = queries.usr_get_by_name(db, name="Reset")["password_hash"]
        assert new_hash != old_hash
        from argon2 import PasswordHasher

        PasswordHasher().verify(new_hash, "freshpassword")

    def test_reset_not_found(self, client, db):
        resp = client.post(
            "/api/v1/users/missing-id/reset-password",
            data=json.dumps({"new_password": "freshpassword"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_reset_password_too_short(self, client, db):
        u = client.post(
            "/api/v1/users",
            data=json.dumps(
                {"name": "ResetShort", "color": "#abcdef", "password": "originalpw"}
            ),
            content_type="application/json",
        ).get_json()
        resp = client.post(
            f"/api/v1/users/{u['id']}/reset-password",
            data=json.dumps({"new_password": "short"}),
            content_type="application/json",
        )
        assert resp.status_code == 422


class TestSecurityHeaders:
    """Hardening headers must be present on every response."""

    def test_headers_set(self, client, db):
        resp = client.get("/api/v1/categories")
        h = resp.headers
        csp = h["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp
        assert "base-uri 'none'" in csp
        assert h["X-Frame-Options"] == "DENY"
        assert h["X-Content-Type-Options"] == "nosniff"
        assert h["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert h["Permissions-Policy"] == "()"
        assert h["Cross-Origin-Opener-Policy"] == "same-origin"
        assert h["Cross-Origin-Resource-Policy"] == "same-origin"
        assert h["Server"] == "kenboard"
        # HSTS only over HTTPS — test client speaks HTTP.
        assert "Strict-Transport-Security" not in h


class TestCookieHardening:
    """Session cookies must carry HttpOnly + SameSite + (conditionally) Secure."""

    def test_session_cookie_flags(self, app):
        assert app.config["SESSION_COOKIE_HTTPONLY"] is True
        assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
        assert app.config["REMEMBER_COOKIE_HTTPONLY"] is True
        assert app.config["REMEMBER_COOKIE_SAMESITE"] == "Lax"

    def test_secure_flags_off_in_dev(self, app):
        # Test config has KENBOARD_HTTPS unset → Secure must NOT be forced.
        assert app.config.get("SESSION_COOKIE_SECURE") is not True
        assert app.config.get("REMEMBER_COOKIE_SECURE") is not True


class TestCORSFallback:
    """When KENBOARD_CORS_ORIGINS is empty, no CORS headers leak."""

    def test_no_cors_header_with_random_origin(self, client, db):
        resp = client.get(
            "/api/v1/categories",
            headers={"Origin": "https://attacker.example"},
        )
        assert "Access-Control-Allow-Origin" not in resp.headers


class TestMarkdownSanitization:
    """#52: marked.parse() output is sanitized via DOMPurify before innerHTML.

    The sanitization itself runs client-side (we trust the DOMPurify library), so these
    tests only verify the wiring: the asset is served, base.html loads it, and app.js
    calls DOMPurify.sanitize on every rendered task description.
    """

    def test_dompurify_asset_is_served(self, client):
        resp = client.get("/dompurify.min.js")
        assert resp.status_code == 200
        # Confirm we got the real Cure53 release, not a stub.
        body = resp.data.decode("utf-8", errors="replace")
        assert "DOMPurify" in body
        assert "Cure53" in body

    def test_base_template_loads_dompurify(self, client, db):
        # `/` extends base.html (login.html does not). LOGIN_DISABLED=True
        # in the test app lets us reach it without auth.
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"dompurify.min.js" in resp.data

    def test_app_js_calls_dompurify_sanitize(self, client):
        resp = client.get("/app.js")
        assert resp.status_code == 200
        assert b"DOMPurify.sanitize" in resp.data

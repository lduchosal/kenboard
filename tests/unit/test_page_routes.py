"""Unit tests for page routes (pages.py) — safety net before refactoring (#227).

These tests verify that each page route returns 200 and renders the
expected data. They run with LOGIN_DISABLED=True (the default in the
test app) so auth is not exercised here — that is covered by
test_admin_only.py and test_auth_user.py.
"""

import pytest


@pytest.fixture(autouse=True)
def _ensure_login_disabled(app):
    """Ensure LOGIN_DISABLED is True for all page route tests.

    Other test modules (test_admin_only, test_user_scopes) toggle this
    flag on the session-scoped app. Restore it so page routes don't
    redirect to /login.
    """
    prev = app.config.get("LOGIN_DISABLED")
    app.config["LOGIN_DISABLED"] = True
    yield
    app.config["LOGIN_DISABLED"] = prev


class TestIndexPage:
    """GET / — dashboard index."""

    def test_returns_200(self, client, db):
        """Index page returns 200 on empty board."""
        resp = client.get("/")
        assert resp.status_code == 200

    def test_contains_version(self, client, db):
        """Index page contains the KEN title."""
        resp = client.get("/")
        html = resp.data.decode()
        assert "KEN" in html

    def test_shows_doing_tasks(self, client, db, queries):
        """Doing tasks appear in the index overview."""
        queries.cat_create(
            db, id="idx-cat", name="IndexCat", color="var(--accent)", position=0
        )
        queries.proj_create(
            db,
            id="idx-proj",
            cat_id="idx-cat",
            name="IndexProj",
            acronym="IDX",
            status="active",
            position=0,
            default_who="",
        )
        queries.task_create(
            db,
            project_id="idx-proj",
            title="Doing task visible",
            description="",
            status="doing",
            who="Q",
            due_date=None,
            position=0,
        )
        queries.task_create(
            db,
            project_id="idx-proj",
            title="Done task hidden",
            description="",
            status="done",
            who="Q",
            due_date=None,
            position=1,
        )
        resp = client.get("/")
        html = resp.data.decode()
        assert "Doing task visible" in html

    def test_empty_board(self, client, db):
        """Empty board does not crash."""
        resp = client.get("/")
        assert resp.status_code == 200


class TestCategoryPage:
    """GET /cat/<cat_id>.html — category detail."""

    def test_returns_200(self, client, db, queries):
        """Category page returns 200."""
        queries.cat_create(
            db, id="cat-page", name="CatPage", color="var(--accent)", position=0
        )
        queries.proj_create(
            db,
            id="cat-proj",
            cat_id="cat-page",
            name="CatProj",
            acronym="CP",
            status="active",
            position=0,
            default_who="",
        )
        resp = client.get("/cat/cat-page.html")
        assert resp.status_code == 200

    def test_shows_category_name(self, client, db, queries):
        """Category name appears in the rendered page."""
        queries.cat_create(
            db, id="cat-name", name="MyCatName", color="var(--green)", position=0
        )
        queries.proj_create(
            db,
            id="cat-name-proj",
            cat_id="cat-name",
            name="P1",
            acronym="P1",
            status="active",
            position=0,
            default_who="",
        )
        resp = client.get("/cat/cat-name.html")
        html = resp.data.decode()
        assert "MyCatName" in html

    def test_shows_project_tasks(self, client, db, queries):
        """Tasks of the category's projects appear in the page."""
        queries.cat_create(
            db, id="cat-tasks", name="CatTasks", color="var(--accent)", position=0
        )
        queries.proj_create(
            db,
            id="cat-tasks-proj",
            cat_id="cat-tasks",
            name="TaskProj",
            acronym="TP",
            status="active",
            position=0,
            default_who="",
        )
        queries.task_create(
            db,
            project_id="cat-tasks-proj",
            title="Task in category",
            description="desc",
            status="todo",
            who="Q",
            due_date=None,
            position=0,
        )
        resp = client.get("/cat/cat-tasks.html")
        html = resp.data.decode()
        assert "Task in category" in html

    def test_unknown_category_404(self, client, db):
        """Unknown category id returns 404."""
        resp = client.get("/cat/nonexistent.html")
        assert resp.status_code == 404

    def test_other_category_tasks_not_shown(self, client, db, queries):
        """Tasks from another category do not leak into the page."""
        queries.cat_create(
            db, id="cat-a", name="CatA", color="var(--accent)", position=0
        )
        queries.cat_create(
            db, id="cat-b", name="CatB", color="var(--green)", position=1
        )
        queries.proj_create(
            db,
            id="proj-a",
            cat_id="cat-a",
            name="ProjA",
            acronym="PA",
            status="active",
            position=0,
            default_who="",
        )
        queries.proj_create(
            db,
            id="proj-b",
            cat_id="cat-b",
            name="ProjB",
            acronym="PB",
            status="active",
            position=0,
            default_who="",
        )
        queries.task_create(
            db,
            project_id="proj-b",
            title="Task in CatB only",
            description="",
            status="todo",
            who="Q",
            due_date=None,
            position=0,
        )
        resp = client.get("/cat/cat-a.html")
        html = resp.data.decode()
        assert "Task in CatB only" not in html


class TestAdminBoardPage:
    """GET /admin/board — category/project management."""

    def test_returns_200(self, client, db):
        """Admin board page returns 200."""
        resp = client.get("/admin/board")
        assert resp.status_code == 200

    def test_shows_categories(self, client, db, queries):
        """Categories appear in the admin board page."""
        queries.cat_create(
            db, id="ab-cat", name="BoardCat", color="var(--accent)", position=0
        )
        resp = client.get("/admin/board")
        html = resp.data.decode()
        assert "BoardCat" in html

    def test_shows_projects(self, client, db, queries):
        """Projects appear in the admin board page."""
        queries.cat_create(
            db, id="ab-cat2", name="BC2", color="var(--accent)", position=0
        )
        queries.proj_create(
            db,
            id="ab-proj",
            cat_id="ab-cat2",
            name="BoardProj",
            acronym="BP",
            status="active",
            position=0,
            default_who="",
        )
        resp = client.get("/admin/board")
        html = resp.data.decode()
        assert "BoardProj" in html


class TestAdminUsersPage:
    """GET /admin/users — user management."""

    def test_returns_200(self, client, db):
        """Admin users page returns 200."""
        resp = client.get("/admin/users")
        assert resp.status_code == 200

    def test_shows_users(self, client, db, queries):
        """Users appear in the admin users page."""
        queries.usr_create(
            db,
            id="au-user",
            name="TestPageUser",
            email=None,
            color="#f00",
            password_hash="x",
            is_admin=0,
        )
        resp = client.get("/admin/users")
        html = resp.data.decode()
        assert "TestPageUser" in html


class TestAdminKeysPage:
    """GET /admin/keys — API key management."""

    def test_returns_200(self, client, db):
        """Admin keys page returns 200."""
        resp = client.get("/admin/keys")
        assert resp.status_code == 200

    def test_shows_api_keys(self, client, db, queries):
        """API keys appear in the admin keys page."""
        queries.cat_create(
            db, id="ak-cat", name="KeysCat", color="var(--accent)", position=0
        )
        queries.proj_create(
            db,
            id="ak-proj",
            cat_id="ak-cat",
            name="KeysProj",
            acronym="KP",
            status="active",
            position=0,
            default_who="",
        )
        import hashlib

        key_hash = hashlib.sha256(b"test-key-for-page").hexdigest()
        queries.key_create(
            db,
            id="ak-key",
            user_id=None,
            key_type=None,
            key_hash=key_hash,
            label="TestPageKey",
            expires_at=None,
        )
        resp = client.get("/admin/keys")
        html = resp.data.decode()
        assert "TestPageKey" in html

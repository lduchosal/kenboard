"""Unit tests for page routes (pages.py) — safety net before refactoring (#227).

These tests verify that each page route returns 200 and renders the expected data. They
run with LOGIN_DISABLED=True (the default in the test app) so auth is not exercised here
— that is covered by test_admin_only.py and test_auth_user.py.
"""

import pytest


@pytest.fixture(autouse=True)
def _ensure_login_disabled(app):
    """Ensure LOGIN_DISABLED is True for all page route tests.

    Other test modules (test_admin_only, test_user_scopes) toggle this flag on the
    session-scoped app. Restore it so page routes don't redirect to /login.
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

    def test_dashboard_shows_tasks_per_board_pie(
        self, client, db, queries, seed_task
    ):
        """Dashboard shows a per-board pie chart (ken #620, replaces #540).

        Each visible category becomes one pie slice sized by total task count, with a
        matching legend entry. The wiki-section bar chart it replaces is gone (the
        section-detail view stays scoped to the category page #533/#572).
        """
        html = client.get("/").data.decode()
        assert "Tâches par board" in html
        # The slice + legend reference the category by name; seed_category is "Test".
        assert ">Test<" in html
        # The SVG carries one path per slice with the category colour.
        assert 'class="board-pie-svg"' in html
        assert "<path d=" in html
        # The legacy bar-chart title must no longer appear on the home.
        assert "Tâches par section wiki — par catégorie" not in html

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
            attachement=None,
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
            attachement=None,
            position=1,
        )
        resp = client.get("/")
        html = resp.data.decode()
        assert "Doing task visible" in html

    def test_empty_board(self, client, db):
        """Empty board does not crash."""
        resp = client.get("/")
        assert resp.status_code == 200

    def test_taskers_attributes_token_to_owner(self, client, db, queries):
        """The taskers chart shows the token owner, never the raw key principal."""
        cur = db.cursor()
        cur.execute(
            "INSERT INTO users (id, name, color) VALUES (%s, %s, %s)",
            ("wk-user", "Wanda", "var(--purple)"),
        )
        queries.cat_create(
            db, id="wk-cat", name="WkCat", color="var(--accent)", position=0
        )
        queries.proj_create(
            db,
            id="wk-proj",
            cat_id="wk-cat",
            name="WkProj",
            acronym="WK",
            status="active",
            position=0,
            default_who="",
        )
        cur.execute(
            "INSERT INTO activities (project_id, user_name, action, target_id) "
            "VALUES (%s, %s, 'create', '1')",
            ("wk-proj", "key:k1:user:wk-user"),
        )
        html = client.get("/").data.decode()
        assert "Taskers (7 derniers jours)" in html
        assert "Wanda" in html
        assert "key:k1:user:wk-user" not in html


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

    def test_wiki_chart_scoped_to_category(self, client, db, queries):
        """Wiki section chart shows the current category's classifications only (#533,
        #572).

        A classification in another category must not appear on this page.
        """
        # Category A with a task classified to backend/api
        queries.cat_create(
            db, id="wcat-a", name="WCatA", color="var(--accent)", position=0
        )
        queries.proj_create(
            db,
            id="wproj-a",
            cat_id="wcat-a",
            name="PA",
            acronym="PA",
            status="active",
            position=0,
            default_who="",
        )
        queries.task_create(
            db,
            project_id="wproj-a",
            title="A",
            description="",
            status="todo",
            who="",
            due_date=None,
            attachement=None,
            position=0,
        )
        cur = db.cursor()
        cur.execute("SELECT LAST_INSERT_ID()")
        task_a = cur.fetchone()["LAST_INSERT_ID()"]
        queries.wiki_classify(
            db, task_id=task_a, section_path="backend/api", classified_by="t"
        )

        # Category B with a task classified to frontend/ux — must not leak
        queries.cat_create(
            db, id="wcat-b", name="WCatB", color="var(--purple)", position=0
        )
        queries.proj_create(
            db,
            id="wproj-b",
            cat_id="wcat-b",
            name="PB",
            acronym="PB",
            status="active",
            position=0,
            default_who="",
        )
        queries.task_create(
            db,
            project_id="wproj-b",
            title="B",
            description="",
            status="todo",
            who="",
            due_date=None,
            attachement=None,
            position=0,
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        task_b = cur.fetchone()["LAST_INSERT_ID()"]
        queries.wiki_classify(
            db, task_id=task_b, section_path="frontend/ux", classified_by="t"
        )

        # Visit category A: backend/api shows up, frontend/ux must not.
        html = client.get("/cat/wcat-a.html").data.decode()
        assert "Tâches par section wiki" in html
        assert "backend/api" in html
        assert "frontend/ux" not in html

        # Visit category B: the reverse.
        html_b = client.get("/cat/wcat-b.html").data.decode()
        assert "frontend/ux" in html_b
        assert "backend/api" not in html_b

    def test_wiki_chart_splits_per_project_within_category(self, client, db, queries):
        """Within one category, each project gets its own card (#572).

        Aggregating sections across all projects of a cat mixes métiers (e.g. finance +
        server boards live under the same KEN cat), so the chart must draw one card per
        project and never sum their bars.
        """
        queries.cat_create(
            db, id="pcat", name="PCat", color="var(--accent)", position=0
        )
        # Two projects in the same category, each with its own classification.
        queries.proj_create(
            db,
            id="pfin",
            cat_id="pcat",
            name="Finance",
            acronym="FIN",
            status="active",
            position=0,
            default_who="",
        )
        queries.proj_create(
            db,
            id="psrv",
            cat_id="pcat",
            name="Server",
            acronym="SRV",
            status="active",
            position=1,
            default_who="",
        )
        cur = db.cursor()
        for proj_id, section in (
            ("pfin", "backend/billing"),
            ("psrv", "ops/monitoring"),
        ):
            queries.task_create(
                db,
                project_id=proj_id,
                title=f"T-{proj_id}",
                description="",
                status="todo",
                who="",
                due_date=None,
                attachement=None,
                position=0,
            )
            cur.execute("SELECT LAST_INSERT_ID()")
            tid = cur.fetchone()["LAST_INSERT_ID()"]
            queries.wiki_classify(
                db, task_id=tid, section_path=section, classified_by="t"
            )

        html = client.get("/cat/pcat.html").data.decode()
        # Per-project header (not the per-category one from the dashboard).
        assert "Tâches par section wiki — par projet" in html
        # Each project must appear as its own card with its own section.
        assert "FIN / Finance" in html
        assert "SRV / Server" in html
        assert "backend/billing" in html
        assert "ops/monitoring" in html

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
            attachement=None,
            position=0,
        )
        resp = client.get("/cat/cat-tasks.html")
        html = resp.data.decode()
        assert "Task in category" in html

    def test_category_page_uses_batched_queries(self, client, db, queries):
        """#338: /cat/<id>.html must NOT call task_get_by_project /
        burndown_get_by_project once per project.

        Replaces the N+1 fan-out with one ``task_get_by_category`` + one
        ``burndown_get_for_category_projects``. We assert the new queries exist and that
        the page renders correctly with tasks from multiple projects in the same
        category.
        """
        # Sanity: batched queries are registered.
        assert hasattr(queries, "task_get_by_category")
        assert hasattr(queries, "burndown_get_for_category_projects")

        queries.cat_create(
            db, id="cat-batch", name="CatBatch", color="var(--accent)", position=0
        )
        for i in range(3):
            pid = f"proj-batch-{i}"
            queries.proj_create(
                db,
                id=pid,
                cat_id="cat-batch",
                name=f"Proj{i}",
                acronym=f"P{i}",
                status="active",
                position=i,
                default_who="",
            )
            queries.task_create(
                db,
                project_id=pid,
                title=f"Task in proj {i}",
                description="",
                status="todo",
                who="Q",
                due_date=None,
                attachement=None,
                position=0,
            )

        # The batched task query returns every task across all 3 projects
        # in one round-trip.
        rows = list(queries.task_get_by_category(db, category_id="cat-batch"))
        assert len(rows) == 3
        assert {r["project_id"] for r in rows} == {
            "proj-batch-0",
            "proj-batch-1",
            "proj-batch-2",
        }

        # The page renders 200 and each project's task is visible —
        # regression-guard against a Python grouping bug or a return to
        # per-project fan-out.
        resp = client.get("/cat/cat-batch.html")
        assert resp.status_code == 200
        html = resp.data.decode()
        for i in range(3):
            assert f"Task in proj {i}" in html

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
            attachement=None,
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


class TestAidePage:
    """GET /aide — help page (#510)."""

    def test_returns_200(self, client, db):
        """Help page returns 200."""
        resp = client.get("/aide")
        assert resp.status_code == 200

    def test_has_both_sections(self, client, db):
        """Help page renders both the bots and the extension sections."""
        html = client.get("/aide").data.decode()
        assert "Le ken pour les agents" in html
        assert "Le ken pour le navigateur" in html
        assert "pip install kenboard" in html
        assert "github.com/lduchosal/kenboard/releases" in html

"""Server-side wiki classification routes (#376b).

Exercises /api/v1/wiki/* — the endpoints ``ken wiki groom`` calls.
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture(autouse=True)
def _ensure_login_disabled(app):
    """Ensure LOGIN_DISABLED is True for all wiki route tests.

    Other test modules (test_admin_only, test_auth_user) toggle this flag on the
    session-scoped app. Restore it so /api/v1/wiki/* doesn't 401.
    """
    prev = app.config.get("LOGIN_DISABLED")
    app.config["LOGIN_DISABLED"] = True
    yield
    app.config["LOGIN_DISABLED"] = prev


@pytest.fixture()
def project(client, db, queries):
    """Seed a category + project + 3 tasks (different states)."""
    queries.cat_create(db, id="cat-w", name="Cat", color="var(--accent)", position=0)
    queries.proj_create(
        db,
        id="proj-w",
        cat_id="cat-w",
        name="Proj",
        acronym="PROJ",
        status="active",
        position=0,
        default_who="",
    )
    cur = db.cursor()
    task_ids = []
    for i, title in enumerate(["First", "Second", "Third"]):
        cur.execute(
            "INSERT INTO tasks (project_id, title, description, status, who, "
            "due_date, position) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            ("proj-w", title, "", "todo", "Q", None, i),
        )
        task_ids.append(cur.lastrowid)
    return {"project_id": "proj-w", "tasks": task_ids}


class TestListUnclassified:
    def test_returns_all_unclassified(self, client, db, project):
        r = client.get("/api/v1/wiki/unclassified")
        assert r.status_code == 200
        ids = {t["id"] for t in r.get_json()}
        assert set(project["tasks"]) <= ids

    def test_classified_task_does_not_appear(self, client, db, project):
        client.post(
            "/api/v1/wiki/classify",
            data=json.dumps(
                {"task_id": project["tasks"][0], "section_path": "backend"}
            ),
            content_type="application/json",
        )
        r = client.get("/api/v1/wiki/unclassified")
        ids = {t["id"] for t in r.get_json()}
        assert project["tasks"][0] not in ids
        assert project["tasks"][1] in ids

    def test_project_filter(self, client, db, project):
        r = client.get(f"/api/v1/wiki/unclassified?project={project['project_id']}")
        assert r.status_code == 200
        # All seeded tasks belong to the same project — filter shouldn't drop them
        ids = {t["id"] for t in r.get_json()}
        assert set(project["tasks"]) <= ids


class TestClassify:
    def test_upsert_returns_row(self, client, db, project):
        r = client.post(
            "/api/v1/wiki/classify",
            data=json.dumps(
                {"task_id": project["tasks"][0], "section_path": "frontend/ui"}
            ),
            content_type="application/json",
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["task_id"] == project["tasks"][0]
        assert body["section_path"] == "frontend/ui"

    def test_classify_then_re_classify(self, client, db, project):
        tid = project["tasks"][0]
        client.post(
            "/api/v1/wiki/classify",
            data=json.dumps({"task_id": tid, "section_path": "a"}),
            content_type="application/json",
        )
        r = client.post(
            "/api/v1/wiki/classify",
            data=json.dumps({"task_id": tid, "section_path": "b"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.get_json()["section_path"] == "b"

    def test_missing_task_id_400(self, client, db):
        r = client.post(
            "/api/v1/wiki/classify",
            data=json.dumps({"section_path": "x"}),
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_missing_section_path_400(self, client, db, project):
        r = client.post(
            "/api/v1/wiki/classify",
            data=json.dumps({"task_id": project["tasks"][0]}),
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_unknown_task_id_404(self, client, db):
        r = client.post(
            "/api/v1/wiki/classify",
            data=json.dumps({"task_id": 99999999, "section_path": "x"}),
            content_type="application/json",
        )
        assert r.status_code == 404


class TestGetClassification:
    def test_returns_classification(self, client, db, project):
        client.post(
            "/api/v1/wiki/classify",
            data=json.dumps(
                {"task_id": project["tasks"][0], "section_path": "backend/api"}
            ),
            content_type="application/json",
        )
        r = client.get(f"/api/v1/wiki/classify/{project['tasks'][0]}")
        assert r.status_code == 200
        assert r.get_json()["section_path"] == "backend/api"

    def test_unclassified_returns_404(self, client, db, project):
        r = client.get(f"/api/v1/wiki/classify/{project['tasks'][0]}")
        assert r.status_code == 404

    def test_unknown_task_returns_404(self, client, db):
        r = client.get("/api/v1/wiki/classify/99999999")
        assert r.status_code == 404


class TestListAll:
    """``GET /api/v1/wiki/all`` — consumed by ``ken wiki sync`` (#376c)."""

    def test_empty_when_no_classifications(self, client, db, project):
        r = client.get("/api/v1/wiki/all")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_returns_classified_rows_joined_with_task(self, client, db, project):
        tid = project["tasks"][0]
        client.post(
            "/api/v1/wiki/classify",
            data=json.dumps({"task_id": tid, "section_path": "backend/api"}),
            content_type="application/json",
        )
        r = client.get("/api/v1/wiki/all")
        assert r.status_code == 200
        rows = r.get_json()
        assert len(rows) == 1
        row = rows[0]
        assert row["task_id"] == tid
        assert row["section_path"] == "backend/api"
        assert row["title"] == "First"
        assert row["status"] == "todo"
        assert row["project_id"] == project["project_id"]
        assert row["classified_at"] is not None

    def test_project_filter(self, client, db, project):
        tid = project["tasks"][0]
        client.post(
            "/api/v1/wiki/classify",
            data=json.dumps({"task_id": tid, "section_path": "x"}),
            content_type="application/json",
        )
        r = client.get(f"/api/v1/wiki/all?project={project['project_id']}")
        assert r.status_code == 200
        rows = r.get_json()
        assert len(rows) == 1
        assert rows[0]["task_id"] == tid


class TestClearClassification:
    def test_clear_removes(self, client, db, project):
        tid = project["tasks"][0]
        client.post(
            "/api/v1/wiki/classify",
            data=json.dumps({"task_id": tid, "section_path": "x"}),
            content_type="application/json",
        )
        r = client.delete(f"/api/v1/wiki/classify/{tid}")
        assert r.status_code == 204
        r2 = client.get(f"/api/v1/wiki/classify/{tid}")
        assert r2.status_code == 404


class TestMissingTableErrorIsFriendly:
    """When migration 0021 wasn't applied, every wiki route used to 500 with a raw
    ``ProgrammingError(1146)``.

    The blueprint-level handler should turn that into an actionable 503 (#472).
    """

    def _patch_queries_to_raise(self, monkeypatch, exc):
        """Replace ``db.load_queries`` with a stub whose wiki query raises."""
        import dashboard.db as db_mod

        class _Stub:
            def wiki_get_unclassified_tasks(self, _conn):
                raise exc

        monkeypatch.setattr(db_mod, "load_queries", lambda: _Stub())

    def test_missing_table_becomes_503_with_migrate_hint(self, client, monkeypatch):
        import pymysql.err

        self._patch_queries_to_raise(
            monkeypatch,
            pymysql.err.ProgrammingError(
                1146, "Table 'dashboard.task_wiki_classifications' doesn't exist"
            ),
        )
        r = client.get("/api/v1/wiki/unclassified")
        assert r.status_code == 503
        body = r.get_json()
        assert body["error_class"] == "MigrationPending"
        assert "kenboard migrate" in body["error"]

    def test_non_1146_programming_error_is_re_raised(self):
        """Other SQL errors must NOT be swallowed — only 1146 gets the hint.

        We check the handler directly (rather than via ``client.get``) because Flask's
        testing mode re-raises any unhandled exception, masking the 500 path. The
        contract we actually care about is "handler must re-raise for codes != 1146 so
        the global 500 handler can do its thing".
        """
        import pymysql.err

        from dashboard.routes.wiki import _handle_missing_wiki_table

        exc = pymysql.err.ProgrammingError(1064, "syntax error")
        with pytest.raises(pymysql.err.ProgrammingError) as ei:
            _handle_missing_wiki_table(exc)
        assert ei.value is exc

"""Unit tests for the auth middleware's project_id resolution (ken #806)."""

from dashboard.auth_resolve import _int_suffix, _resolve_project_id, _task_project_id


class TestIntSuffix:
    """``_int_suffix`` parses the trailing ``/<int>`` path segment."""

    def test_parses_trailing_int(self):
        assert _int_suffix("/api/v1/tasks/42") == 42

    def test_rejects_non_int(self):
        assert _int_suffix("/api/v1/tasks/abc") is None

    def test_rejects_empty_path(self):
        assert _int_suffix("") is None


class TestTaskProjectId:
    """``_task_project_id`` looks the owning project up in the DB."""

    def test_none_task_id_short_circuits(self):
        assert _task_project_id(None) is None

    def test_unknown_task_returns_none(self, app, db):
        assert _task_project_id(99999999) is None


class TestResolveProjectId:
    """Dispatch by URL prefix + method (the auth scope check input)."""

    def test_projects_patch_takes_url_id(self, app):
        with app.test_request_context("/api/v1/projects/p-1", method="PATCH"):
            assert _resolve_project_id("PATCH", "/api/v1/projects/p-1") == "p-1"

    def test_projects_get_is_not_scoped(self, app):
        with app.test_request_context("/api/v1/projects/p-1"):
            assert _resolve_project_id("GET", "/api/v1/projects/p-1") is None

    def test_unknown_path_returns_none(self, app):
        with app.test_request_context("/api/v1/users"):
            assert _resolve_project_id("GET", "/api/v1/users") is None

    def test_tasks_delete_resolves_via_db(self, app, db):
        with app.test_request_context("/api/v1/tasks/424242", method="DELETE"):
            assert _resolve_project_id("DELETE", "/api/v1/tasks/424242") is None

    def test_wiki_classify_post_requires_int_task_id(self, app):
        with app.test_request_context(
            "/api/v1/wiki/classify", method="POST", json={"task_id": "nope"}
        ):
            assert _resolve_project_id("POST", "/api/v1/wiki/classify") is None

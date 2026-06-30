"""Tests for the server-side performance monitoring module (#214)."""

import time
from unittest.mock import MagicMock

import pytest
from flask import Flask, g, request

import dashboard.perf as perf
from dashboard.perf import (
    PerfCollector,
    _check_thresholds,
    _task_title,
    _task_title_prefix,
)


def _summary(**overrides):
    """Build a full perf summary dict, overridable per test."""
    base = {
        "method": "GET",
        "route": "/cat/<cat_id>.html",
        "total_ms": 120.0,
        "query_count": 5,
        "sql_total_ms": 40.0,
        "template_name": "category.html",
        "template_ms": 8.0,
        "response_kb": 100.0,
        "queries_detail": [("cat_get_all", 5.0), ("task_get_by_project", 3.0)],
    }
    base.update(overrides)
    return base


@pytest.fixture()
def _clear_cooldowns():
    """Isolate the module-level cooldown map between tests."""
    perf._cooldowns.clear()
    yield
    perf._cooldowns.clear()


class TestPerfCollector:
    """Test the per-request metric accumulator."""

    def test_empty_collector(self):
        c = PerfCollector()
        assert c.query_count == 0
        assert c.sql_total_ms == 0.0
        assert c.template_name is None
        assert c.template_ms == 0.0

    def test_record_queries(self):
        c = PerfCollector()
        c.record_query("cat_get_all", 5.0)
        c.record_query("proj_get_all", 3.0)
        c.record_query("task_get_by_project", 2.0)
        assert c.query_count == 3
        assert c.sql_total_ms == 10.0

    def test_template_timing(self):
        c = PerfCollector()
        c.start_template()
        time.sleep(0.01)
        c.end_template("category.html")
        assert c.template_name == "category.html"
        assert c.template_ms > 0

    def test_summary(self):
        c = PerfCollector()
        c.record_query("cat_get_all", 5.0)
        c.record_query("proj_get_all", 3.5)
        s = c.summary(total_ms=100.0, response_kb=42.0, route="/", method="GET")
        assert s["method"] == "GET"
        assert s["route"] == "/"
        assert s["total_ms"] == 100.0
        assert s["query_count"] == 2
        assert s["sql_total_ms"] == 8.5
        assert s["response_kb"] == 42.0
        assert len(s["queries_detail"]) == 2


class TestThresholds:
    """Test threshold violation detection."""

    def test_no_violation(self):
        summary = {
            "total_ms": 100,
            "query_count": 5,
            "sql_total_ms": 50,
            "response_kb": 100,
        }
        assert _check_thresholds(summary) == []

    def test_budget_exceeded(self, monkeypatch):
        monkeypatch.setattr("dashboard.perf.Config.PERF_BUDGET_MS", 200)
        summary = {
            "total_ms": 350,
            "query_count": 5,
            "sql_total_ms": 50,
            "response_kb": 100,
        }
        violations = _check_thresholds(summary)
        assert len(violations) == 1
        assert "budget" in violations[0]

    def test_queries_exceeded(self, monkeypatch):
        monkeypatch.setattr("dashboard.perf.Config.PERF_MAX_QUERIES", 10)
        summary = {
            "total_ms": 100,
            "query_count": 25,
            "sql_total_ms": 50,
            "response_kb": 100,
        }
        violations = _check_thresholds(summary)
        assert len(violations) == 1
        assert "queries" in violations[0]

    def test_sql_exceeded(self, monkeypatch):
        monkeypatch.setattr("dashboard.perf.Config.PERF_MAX_SQL_MS", 100)
        summary = {
            "total_ms": 200,
            "query_count": 5,
            "sql_total_ms": 150,
            "response_kb": 100,
        }
        violations = _check_thresholds(summary)
        assert len(violations) == 1
        assert "SQL" in violations[0]

    def test_response_size_exceeded(self, monkeypatch):
        monkeypatch.setattr("dashboard.perf.Config.PERF_MAX_RESPONSE_KB", 256)
        summary = {
            "total_ms": 100,
            "query_count": 5,
            "sql_total_ms": 50,
            "response_kb": 600,
        }
        violations = _check_thresholds(summary)
        assert len(violations) == 1
        assert "response" in violations[0]

    def test_multiple_violations(self, monkeypatch):
        monkeypatch.setattr("dashboard.perf.Config.PERF_BUDGET_MS", 200)
        monkeypatch.setattr("dashboard.perf.Config.PERF_MAX_QUERIES", 10)
        summary = {
            "total_ms": 500,
            "query_count": 30,
            "sql_total_ms": 50,
            "response_kb": 100,
        }
        violations = _check_thresholds(summary)
        assert len(violations) == 2


class TestTaskTitle:
    """Test task title generation and dedup prefix."""

    def test_title_format(self):
        title = _task_title("GET", "/cat/<cat_id>.html", ["budget 450ms > 200ms"])
        assert title == "PERF / GET /cat/<cat_id>.html / budget 450ms > 200ms"

    def test_title_prefix(self):
        prefix = _task_title_prefix("GET", "/cat/<cat_id>.html")
        assert prefix == "PERF / GET /cat/<cat_id>.html /"

    def test_title_starts_with_prefix(self):
        title = _task_title("GET", "/", ["queries 30 > 20", "SQL 200ms > 100ms"])
        prefix = _task_title_prefix("GET", "/")
        assert title.startswith(prefix)


class TestPerfIntegration:
    """Test perf hooks within a Flask request."""

    def test_perf_collector_set_on_request(self, app, client):
        with app.test_request_context("/"):
            # Simulate what before_request does
            g.perf = PerfCollector()
            g.perf.record_query("cat_get_all", 5.0)
            assert g.perf.query_count == 1

    def test_api_request_has_perf_logging(self, client):
        # Auth returns 401, but perf still logs (visible in captured logs)
        resp = client.get("/api/v1/categories")
        assert resp.status_code in (200, 401)

    def test_static_skipped(self, client):
        resp = client.get("/style.css")
        assert resp.status_code == 200


class TestCooldown:
    """Test the cooldown gate around task creation."""

    def test_route_key(self):
        assert perf._route_key("GET", "/cat/<id>") == "GET /cat/<id>"

    def test_first_call_allowed_then_blocked(self, monkeypatch, _clear_cooldowns):
        monkeypatch.setattr("dashboard.perf.Config.PERF_COOLDOWN_S", 3600)
        assert perf._can_create_task("GET /") is True
        # Second call within the cooldown window is blocked.
        assert perf._can_create_task("GET /") is False

    def test_zero_cooldown_always_allows(self, monkeypatch, _clear_cooldowns):
        monkeypatch.setattr("dashboard.perf.Config.PERF_COOLDOWN_S", 0)
        assert perf._can_create_task("GET /x") is True
        assert perf._can_create_task("GET /x") is True


class TestBuildDescription:
    """Test the markdown task-description builder."""

    def test_contains_metrics_and_queries(self):
        violations = ["budget 650ms > 500ms", "queries 25 > 20"]
        desc = perf._build_description(_summary(total_ms=650.0), violations)
        assert "GET /cat/<cat_id>.html" in desc
        assert "650.0ms" in desc
        assert "## Violations" in desc
        assert "- budget 650ms > 500ms" in desc
        assert "## Detail des queries" in desc
        assert "`cat_get_all` : 5.0ms" in desc
        assert "#214" in desc

    def test_template_name_fallback(self):
        desc = perf._build_description(_summary(template_name=None), ["x"])
        assert "N/A" in desc


class TestCreatePerfTask:
    """Test ``_create_perf_task`` with the DB layer mocked out."""

    def _patch_db(self, monkeypatch, queries):
        conn = MagicMock()
        monkeypatch.setattr("dashboard.perf.db.get_connection", lambda: conn)
        monkeypatch.setattr("dashboard.perf.db.load_queries", lambda: queries)
        return conn

    def test_no_project_id_short_circuits(self, monkeypatch, _clear_cooldowns):
        monkeypatch.setattr("dashboard.perf.Config.PERF_PROJECT_ID", "")
        get_conn = MagicMock()
        monkeypatch.setattr("dashboard.perf.db.get_connection", get_conn)
        perf._create_perf_task(_summary(), ["v"])
        get_conn.assert_not_called()

    def test_cooldown_blocks_creation(self, monkeypatch, _clear_cooldowns):
        monkeypatch.setattr("dashboard.perf.Config.PERF_PROJECT_ID", "proj")
        monkeypatch.setattr("dashboard.perf.Config.PERF_COOLDOWN_S", 3600)
        s = _summary()
        perf._cooldowns[perf._route_key(s["method"], s["route"])] = time.time()
        get_conn = MagicMock()
        monkeypatch.setattr("dashboard.perf.db.get_connection", get_conn)
        perf._create_perf_task(s, ["v"])
        get_conn.assert_not_called()

    def test_existing_task_skips_create(self, monkeypatch, _clear_cooldowns):
        monkeypatch.setattr("dashboard.perf.Config.PERF_PROJECT_ID", "proj")
        monkeypatch.setattr("dashboard.perf.Config.PERF_COOLDOWN_S", 0)
        queries = MagicMock()
        queries.perf_find_open_task.return_value = {"id": 5, "title": "PERF / GET ..."}
        conn = self._patch_db(monkeypatch, queries)
        perf._create_perf_task(_summary(), ["v"])
        queries.task_create.assert_not_called()
        conn.close.assert_called_once()

    def test_creates_task(self, monkeypatch, _clear_cooldowns):
        monkeypatch.setattr("dashboard.perf.Config.PERF_PROJECT_ID", "proj")
        monkeypatch.setattr("dashboard.perf.Config.PERF_COOLDOWN_S", 0)
        monkeypatch.setattr("dashboard.perf.Config.PERF_TASK_WHO", "Claude")
        queries = MagicMock()
        queries.perf_find_open_task.return_value = None
        queries.task_max_position.return_value = 3
        conn = self._patch_db(monkeypatch, queries)
        perf._create_perf_task(_summary(), ["budget 650ms > 500ms"])
        queries.task_create.assert_called_once()
        kwargs = queries.task_create.call_args.kwargs
        assert kwargs["project_id"] == "proj"
        assert kwargs["status"] == "todo"
        assert kwargs["who"] == "Claude"
        assert kwargs["position"] == 4
        assert kwargs["title"].startswith("PERF / GET /cat/<cat_id>.html /")
        conn.close.assert_called_once()

    def test_exception_releases_cooldown(self, monkeypatch, _clear_cooldowns):
        monkeypatch.setattr("dashboard.perf.Config.PERF_PROJECT_ID", "proj")
        monkeypatch.setattr("dashboard.perf.Config.PERF_COOLDOWN_S", 3600)
        queries = MagicMock()
        queries.perf_find_open_task.side_effect = RuntimeError("boom")
        conn = self._patch_db(monkeypatch, queries)
        s = _summary()
        perf._create_perf_task(s, ["v"])
        # The cooldown slot is released so a later request can retry.
        assert perf._route_key(s["method"], s["route"]) not in perf._cooldowns
        conn.close.assert_called_once()


class TestRequestSummary:
    """Test ``_build_request_summary`` in a request context."""

    def test_returns_none_without_start_time(self):
        app = Flask(__name__)
        with app.test_request_context("/"):
            assert perf._build_request_summary(MagicMock()) is None

    def test_full_summary(self):
        app = Flask(__name__)
        with app.test_request_context("/", method="GET"):
            request._start_time = time.time() - 0.05
            g.perf = PerfCollector()
            g.perf.record_query("cat_get_all", 4.0)
            resp = MagicMock()
            resp.get_data.return_value = b"x" * 2048
            summary = perf._build_request_summary(resp)
            assert summary is not None
            assert summary["method"] == "GET"
            assert summary["route"] == "/"
            assert summary["query_count"] == 1
            assert summary["response_kb"] == 2.0


class TestLogAndEvaluate:
    """Test ``_log_and_evaluate`` task-creation branch."""

    def test_no_violation_no_task(self, monkeypatch):
        created = MagicMock()
        monkeypatch.setattr("dashboard.perf._create_perf_task", created)
        perf._log_and_evaluate(_summary())
        created.assert_not_called()

    def test_violation_creates_task(self, monkeypatch):
        monkeypatch.setattr("dashboard.perf.Config.PERF_BUDGET_MS", 100)
        created = MagicMock()
        monkeypatch.setattr("dashboard.perf._create_perf_task", created)
        perf._log_and_evaluate(_summary(total_ms=500.0))
        created.assert_called_once()


class TestHooks:
    """Test the Flask request/template hooks."""

    def test_before_sets_collector(self):
        app = Flask(__name__)
        with app.test_request_context("/"):
            perf._perf_before()
            assert isinstance(g.perf, PerfCollector)

    def test_before_skips_static(self):
        app = Flask(__name__)
        with app.test_request_context("/static/app.js"):
            perf._perf_before()
            assert not hasattr(g, "perf")

    def test_template_hooks_record_timing(self):
        app = Flask(__name__)
        with app.test_request_context("/"):
            g.perf = PerfCollector()
            perf._perf_before_template(app)
            time.sleep(0.005)
            tmpl = MagicMock()
            tmpl.name = "category.html"
            perf._perf_after_template(app, template=tmpl)
            assert g.perf.template_name == "category.html"
            assert g.perf.template_ms > 0

    def test_template_hooks_noop_outside_context(self):
        # No request context: both hooks must no-op without raising.
        perf._perf_before_template(MagicMock())
        perf._perf_after_template(MagicMock(), template=MagicMock())

    def test_after_template_without_collector(self):
        app = Flask(__name__)
        with app.test_request_context("/"):
            tmpl = MagicMock()
            tmpl.name = "x"
            perf._perf_after_template(app, template=tmpl)  # no g.perf -> no-op

    def test_after_returns_response_without_collector(self):
        app = Flask(__name__)
        with app.test_request_context("/"):
            resp = MagicMock()
            assert perf._perf_after(resp) is resp

    def test_after_returns_response_without_start_time(self):
        app = Flask(__name__)
        with app.test_request_context("/"):
            g.perf = PerfCollector()
            resp = MagicMock()
            assert perf._perf_after(resp) is resp

    def test_after_evaluates_full_request(self, monkeypatch):
        monkeypatch.setattr("dashboard.perf._create_perf_task", MagicMock())
        app = Flask(__name__)
        with app.test_request_context("/", method="GET"):
            request._start_time = time.time()
            g.perf = PerfCollector()
            resp = MagicMock()
            resp.get_data.return_value = b"hello"
            assert perf._perf_after(resp) is resp


class TestInitPerf:
    """Test ``init_perf`` wiring on the Flask app."""

    def test_disabled_registers_nothing(self, monkeypatch):
        monkeypatch.setattr("dashboard.perf.Config.PERF_ENABLED", False)
        app = Flask(__name__)
        perf.init_perf(app)
        assert perf._perf_before not in app.before_request_funcs.get(None, [])

    def test_enabled_registers_hooks(self, monkeypatch):
        monkeypatch.setattr("dashboard.perf.Config.PERF_ENABLED", True)
        app = Flask(__name__)
        perf.init_perf(app)
        assert perf._perf_before in app.before_request_funcs.get(None, [])
        assert perf._perf_after in app.after_request_funcs.get(None, [])

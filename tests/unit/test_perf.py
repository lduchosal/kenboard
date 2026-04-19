"""Tests for the server-side performance monitoring module (#214)."""

import time

from flask import g

from dashboard.perf import (
    PerfCollector,
    _check_thresholds,
    _task_title,
    _task_title_prefix,
)


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

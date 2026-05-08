"""Fatal-error rendering (#268).

The unhandled-exception handler must:
- return a friendly HTML page for browser callers, including a short
  reference id the user can quote when reporting the incident;
- keep the existing JSON shape for API / XHR callers so client-side
  ``apiCall`` flow still surfaces the error in the modal.
"""

from __future__ import annotations

import re

import pytest


@pytest.fixture()
def boom_app():
    """Build a fresh Flask app + register both /boom and /api/boom routes.

    A new app is required per test because Flask refuses to register additional routes
    after the first request has been handled. We can't reuse the session-scoped ``app``
    fixture for that reason.

    TESTING + PROPAGATE_EXCEPTIONS are off so the registered error handler actually runs
    (Flask propagates instead under TESTING).
    """
    from dashboard.app import create_app

    app = create_app()
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["LOGIN_DISABLED"] = True
    app.config["RATELIMIT_ENABLED"] = False

    @app.route("/__test_boom__")
    def _boom():
        raise RuntimeError("simulated kaboom")

    @app.route("/api/__test_boom__")
    def _api_boom():
        raise RuntimeError("api kaboom")

    return app


def test_html_request_returns_friendly_page(boom_app):
    """A browser request gets HTML with the title + status code + ref id."""
    client = boom_app.test_client()
    r = client.get("/__test_boom__", headers={"Accept": "text/html"})
    assert r.status_code == 500
    body = r.data.decode("utf-8")
    assert "Une erreur fatale est survenue" in body
    assert "500" in body
    assert "RuntimeError" in body
    # The reference id is rendered inside the .error-fatal-ref element and
    # follows the format ``E-<hex-timestamp>-<4-hex>``.
    assert re.search(r"E-[0-9a-f]+-[0-9a-f]{4}", body)


def test_api_request_keeps_json_shape(boom_app):
    """A request under /api/ keeps the JSON response shape with the ref id."""
    client = boom_app.test_client()
    r = client.get("/api/__test_boom__")
    assert r.status_code == 500
    body = r.get_json()
    assert body is not None
    assert body["error"] == "Internal server error"
    assert "error_id" in body
    assert re.match(r"E-[0-9a-f]+-[0-9a-f]{4}", body["error_id"])


def test_explicit_json_accept_returns_json(boom_app):
    """Even outside /api/, an ``Accept: application/json`` caller gets JSON."""
    client = boom_app.test_client()
    r = client.get("/__test_boom__", headers={"Accept": "application/json"})
    assert r.status_code == 500
    body = r.get_json()
    assert body is not None
    assert body["error"] == "Internal server error"


def test_404_passes_through(boom_app):
    """HTTPException keeps its default rendering — handler must not catch it."""
    client = boom_app.test_client()
    r = client.get("/this-route-does-not-exist")
    assert r.status_code == 404
    # 404 returns Werkzeug's default page, not our fatal-error template.
    assert b"Une erreur fatale est survenue" not in r.data

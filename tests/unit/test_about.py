"""/about page: public summary for everyone, runtime details for admins (#1165)."""

from __future__ import annotations

import platform

import pytest
from argon2 import PasswordHasher

from dashboard import __version__, about


class TestParseRequirement:
    """``Requires-Dist`` strings are split into name / spec / extra."""

    def test_core(self):
        assert about.parse_requirement("flask>=3.1") == {
            "name": "flask",
            "spec": ">=3.1",
            "extra": None,
        }

    def test_with_extra_marker(self):
        dep = about.parse_requirement('gunicorn>=21.0; extra == "prod"')
        assert dep == {"name": "gunicorn", "spec": ">=21.0", "extra": "prod"}

    def test_with_package_extras(self):
        dep = about.parse_requirement("pymysql[rsa]>=1.1")
        assert dep["name"] == "pymysql"
        assert dep["spec"] == ">=1.1"

    def test_unpinned(self):
        assert about.parse_requirement("markdown")["spec"] == ""


class TestDependencies:
    """Declared deps come back with their installed versions, core first."""

    def test_lists_core_deps_installed(self):
        deps = {d["name"].lower(): d for d in about.dependencies()}
        assert deps["flask"]["installed"]
        assert deps["flask"]["extra"] is None

    def test_core_before_extras(self):
        extras = [d["extra"] is not None for d in about.dependencies()]
        assert extras == sorted(extras)


class TestAboutPageAdmin:
    """With LOGIN_DISABLED (test mode = admin), every section renders."""

    def test_returns_200(self, client, db):
        assert client.get("/about").status_code == 200

    def test_public_and_admin_sections(self, client, db):
        html = client.get("/about").data.decode()
        assert f"kenboard {__version__}" in html
        assert "github.com/lduchosal/kenboard" in html
        assert "Environnement d'ex&eacute;cution" in html
        assert platform.python_version() in html
        assert "<code>flask</code>" in html

    def test_header_links_about(self, client, db):
        assert 'href="/about"' in client.get("/help").data.decode()


@pytest.fixture
def user_client(app, db, queries):
    """Logged-in non-admin client (Flask-Login re-enabled)."""
    prev = app.config.get("LOGIN_DISABLED", False)
    app.config["LOGIN_DISABLED"] = False
    queries.usr_create(
        db,
        id="user-about",
        name="about_user",
        email=None,
        color="#888",
        password_hash=PasswordHasher().hash("aboutpw12345"),
        is_admin=0,
    )
    client = app.test_client()
    resp = client.post(
        "/login", data={"name": "about_user", "password": "aboutpw12345"}
    )
    assert resp.status_code == 302
    yield client
    app.config["LOGIN_DISABLED"] = prev


class TestAboutPageNonAdmin:
    """A regular user sees the project summary but no runtime details."""

    def test_hides_admin_section(self, user_client):
        resp = user_client.get("/about")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert f"kenboard {__version__}" in html
        assert "Environnement d" not in html
        assert "<code>flask</code>" not in html
        assert "Ex&eacute;cutable" not in html

    def test_anonymous_redirected_to_login(self, app, db):
        prev = app.config.get("LOGIN_DISABLED", False)
        app.config["LOGIN_DISABLED"] = False
        try:
            resp = app.test_client().get("/about")
        finally:
            app.config["LOGIN_DISABLED"] = prev
        assert resp.status_code == 302
        assert "/login" in resp.location

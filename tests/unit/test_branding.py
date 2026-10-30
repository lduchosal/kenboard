"""Configurable branding: KENBOARD_TITLE / LOGO / LOGO_ALT / FAVICON (#1159).

Defaults must render exactly the historical Kenboard branding; overrides must reach the
authentication pages, the header, the ``<title>``, the favicon links and the email
subjects.
"""

from unittest.mock import patch

import pytest
from argon2 import PasswordHasher

from dashboard.branding import brand_context, page_title
from dashboard.config import Config


@pytest.fixture
def custom_brand(monkeypatch):
    """Override every branding variable with a fake company."""
    monkeypatch.setattr(Config, "KENBOARD_TITLE", "Acme")
    monkeypatch.setattr(Config, "KENBOARD_SHORT_TITLE", "ACM")
    monkeypatch.setattr(Config, "KENBOARD_LOGO", "/branding/acme.png")
    monkeypatch.setattr(Config, "KENBOARD_LOGO_ALT", "Acme SA")
    monkeypatch.setattr(Config, "KENBOARD_FAVICON", "/branding/acme.ico")


@pytest.fixture
def auth_client(app):
    """Test client with login_required re-enabled (auth pages reachable)."""
    prev = app.config.get("LOGIN_DISABLED", False)
    app.config["LOGIN_DISABLED"] = False
    yield app.test_client()
    app.config["LOGIN_DISABLED"] = prev


class TestPageTitle:
    """``page_title`` composes the HTML <title>."""

    def test_default_brand_alone(self):
        assert page_title() == "KEN"

    def test_default_with_parts(self):
        assert page_title("Admin", "Users") == "KEN / Admin / Users"

    def test_empty_parts_skipped(self):
        assert page_title("", "Aide") == "KEN / Aide"

    @pytest.mark.usefixtures("custom_brand")
    def test_override(self):
        assert page_title("Aide") == "ACM / Aide"


class TestBrandContext:
    """``brand_context`` exposes the config to the templates."""

    def test_defaults(self):
        assert brand_context() == {
            "brand": {
                "title": "Kenboard",
                "logo": "/static/logo.svg",
                "logo_alt": "Kenboard",
                "favicon": "",
            }
        }

    @pytest.mark.usefixtures("custom_brand")
    def test_override(self):
        assert brand_context()["brand"]["logo"] == "/branding/acme.png"


AUTH_PAGES = ["/login", "/register", "/forgot-password", "/reset-password/bogus"]


class TestAuthPages:
    """Logo, alt, title and favicon on the four authentication pages."""

    @pytest.mark.parametrize("url", AUTH_PAGES)
    def test_defaults(self, auth_client, url):
        html = auth_client.get(url).data.decode()
        assert '<img src="/static/logo.svg" alt="Kenboard"' in html
        assert "<title>Kenboard &mdash;" in html
        assert 'href="/static/favicon-32.png"' in html

    @pytest.mark.usefixtures("custom_brand")
    @pytest.mark.parametrize("url", AUTH_PAGES)
    def test_override(self, auth_client, url):
        html = auth_client.get(url).data.decode()
        assert '<img src="/branding/acme.png" alt="Acme SA"' in html
        assert "<title>Acme &mdash;" in html
        assert '<link rel="icon" href="/branding/acme.ico">' in html
        assert "favicon-32.png" not in html
        assert "Kenboard" not in html

    @pytest.mark.usefixtures("custom_brand")
    def test_login_heading_override(self, auth_client):
        html = auth_client.get("/login").data.decode()
        assert '<h1 class="login-title">ACME</h1>' in html


class TestBoardPages:
    """Header and <title> of the authenticated pages."""

    @pytest.fixture(autouse=True)
    def _ensure_login_disabled(self, app):
        """Other modules toggle LOGIN_DISABLED on the session app (cf.

        test_page_routes).
        """
        prev = app.config.get("LOGIN_DISABLED")
        app.config["LOGIN_DISABLED"] = True
        yield
        app.config["LOGIN_DISABLED"] = prev

    def test_index_defaults(self, client):
        html = client.get("/").data.decode()
        assert "<title>KEN</title>" in html
        assert "<h1>KENBOARD</h1>" in html

    @pytest.mark.usefixtures("custom_brand")
    def test_index_override(self, client):
        html = client.get("/").data.decode()
        assert "<title>ACM</title>" in html
        assert "<h1>ACME</h1>" in html
        assert '<link rel="icon" href="/branding/acme.ico">' in html

    @pytest.mark.usefixtures("custom_brand")
    def test_aide_override(self, client):
        html = client.get("/aide").data.decode()
        assert "<title>ACM / Aide</title>" in html


class TestEmailSubject:
    """Email subjects carry the configured brand."""

    @pytest.mark.usefixtures("custom_brand")
    @patch("dashboard.email.send_email", return_value=True)
    def test_reset_subject(self, mock_send, auth_client, queries, db):
        queries.usr_create(
            db,
            id="user-brand",
            name="branduser",
            email="brand@test.com",
            color="#f00",
            password_hash=PasswordHasher().hash("OldPassword123!"),
            is_admin=0,
        )
        auth_client.post("/forgot-password", data={"email": "brand@test.com"})
        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs["subject"].startswith("Acme — ")

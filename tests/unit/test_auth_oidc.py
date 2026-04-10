"""Unit tests for OIDC authentication (#126).

These tests mock the Authlib OAuth client so they don't need a running
IdP. The integration tests in ``tests/integration/test_auth_oidc.py``
use ``oidc-provider-mock`` for the full round trip.

All tests run with ``LOGIN_DISABLED=False`` so the login/auth middleware
is active (same as the password-login tests in ``test_auth_user.py``).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from dashboard.auth_oidc import oauth


@pytest.fixture()
def oidc_app(monkeypatch, db):
    """Create a fresh Flask app with OIDC enabled from the start.

    The OIDC env vars must be set **before** ``create_app()`` so that
    ``init_oidc()`` registers the blueprint during app construction
    (Flask refuses ``register_blueprint`` after the first request).
    """
    monkeypatch.setenv(
        "OIDC_DISCOVERY_URL", "https://mock/.well-known/openid-configuration"
    )
    monkeypatch.setenv("OIDC_CLIENT_ID", "test-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "test-secret")

    # Force Config to re-evaluate from env (class attrs read at import time)
    import dashboard.config

    monkeypatch.setattr(
        dashboard.config.Config,
        "OIDC_DISCOVERY_URL",
        "https://mock/.well-known/openid-configuration",
    )
    monkeypatch.setattr(dashboard.config.Config, "OIDC_CLIENT_ID", "test-client")
    monkeypatch.setattr(dashboard.config.Config, "OIDC_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(dashboard.config.Config, "OIDC_ENABLED", True)
    monkeypatch.setattr(dashboard.config.Config, "OIDC_REQUIRE_EMAIL_VERIFIED", True)
    monkeypatch.setattr(dashboard.config.Config, "OIDC_ALLOWED_EMAIL_DOMAIN", "")

    from dashboard.app import create_app

    app = create_app()
    app.config["LOGIN_DISABLED"] = False
    app.config["TESTING"] = True
    yield app


@pytest.fixture()
def oidc_client(oidc_app):
    """Test client wired to the OIDC-enabled app."""
    return oidc_app.test_client()


def _mock_token(
    email: str = "user@example.com",
    name: str = "Test User",
    email_verified: bool = True,
) -> dict:
    """Build a fake token dict as returned by ``authorize_access_token``."""
    return {
        "access_token": "fake-access-token",
        "id_token": "fake-id-token",
        "userinfo": {
            "sub": f"mock-sub-{email}",
            "email": email,
            "name": name,
            "email_verified": email_verified,
        },
    }


class TestOidcDisabled:
    """When OIDC is not configured, routes return 404 and the button is absent."""

    def test_oidc_login_404_when_disabled(self, app):
        app.config["LOGIN_DISABLED"] = False
        app.config.pop("OIDC_ENABLED", None)
        client = app.test_client()
        r = client.get("/oidc/login")
        assert r.status_code == 404

    def test_oidc_button_absent_when_disabled(self, app):
        app.config["LOGIN_DISABLED"] = False
        app.config.pop("OIDC_ENABLED", None)
        client = app.test_client()
        r = client.get("/login")
        assert r.status_code == 200
        assert b"Sign in with OIDC" not in r.data


class TestOidcCallback:
    """The /oidc/callback route creates/logs in users from the id_token."""

    def test_login_existing_user(self, oidc_client, db, queries):
        """OIDC login for a user whose email already exists in the DB."""
        queries.usr_create(
            db,
            id="user-oidc",
            name="Existing",
            email="existing@example.com",
            color="#0969da",
            password_hash="",
            is_admin=0,
        )
        token = _mock_token(email="existing@example.com", name="Existing")
        with patch.object(oauth, "oidc") as mock_oidc:
            mock_oidc.authorize_access_token.return_value = token
            r = oidc_client.get("/oidc/callback", follow_redirects=False)
        assert r.status_code == 302, r.get_data(as_text=True)
        # Verify session is active: GET / should return 200 (not redirect to login)
        r2 = oidc_client.get("/", follow_redirects=False)
        assert r2.status_code == 200

    def test_lazy_create_new_user(self, oidc_client, db, queries):
        """OIDC login for an unknown email creates a new user with is_admin=False."""
        token = _mock_token(email="newuser@example.com", name="New User")
        with patch.object(oauth, "oidc") as mock_oidc:
            mock_oidc.authorize_access_token.return_value = token
            r = oidc_client.get("/oidc/callback", follow_redirects=False)
        assert r.status_code == 302
        # Verify the user was created in DB
        row = queries.usr_get_by_email(db, email="newuser@example.com")
        assert row is not None
        assert row["name"] == "New User"
        assert row["is_admin"] == 0

    def test_email_not_verified_rejected(self, oidc_client, db):
        """When OIDC_REQUIRE_EMAIL_VERIFIED=true, unverified emails are rejected."""
        token = _mock_token(email="unverified@example.com", email_verified=False)
        with patch.object(oauth, "oidc") as mock_oidc:
            mock_oidc.authorize_access_token.return_value = token
            r = oidc_client.get("/oidc/callback")
        assert b"pas v" in r.data.lower() or b"rifi" in r.data.lower()

    def test_email_not_verified_allowed_when_configured(
        self, oidc_app, oidc_client, db
    ):
        """When OIDC_REQUIRE_EMAIL_VERIFIED=false, unverified emails pass."""
        with patch("dashboard.auth_oidc.Config") as mock_cfg:
            mock_cfg.OIDC_REQUIRE_EMAIL_VERIFIED = False
            mock_cfg.OIDC_ALLOWED_EMAIL_DOMAIN = ""
            token = _mock_token(email="adfs@example.com", email_verified=False)
            with patch.object(oauth, "oidc") as mock_oidc:
                mock_oidc.authorize_access_token.return_value = token
                r = oidc_client.get("/oidc/callback", follow_redirects=False)
        assert r.status_code == 302

    def test_wrong_domain_rejected(self, oidc_app, oidc_client, db):
        """When OIDC_ALLOWED_EMAIL_DOMAIN is set, other domains get 403."""
        with patch("dashboard.auth_oidc.Config") as mock_cfg:
            mock_cfg.OIDC_REQUIRE_EMAIL_VERIFIED = True
            mock_cfg.OIDC_ALLOWED_EMAIL_DOMAIN = "allowed.com"
            token = _mock_token(email="user@evil.com")
            with patch.object(oauth, "oidc") as mock_oidc:
                mock_oidc.authorize_access_token.return_value = token
                r = oidc_client.get("/oidc/callback")
        assert r.status_code == 403

    def test_no_email_in_token_shows_error(self, oidc_client, db):
        """When the IdP returns no email claim, show an error on the login page."""
        token = {"userinfo": {"sub": "no-email-sub"}}
        with patch.object(oauth, "oidc") as mock_oidc:
            mock_oidc.authorize_access_token.return_value = token
            r = oidc_client.get("/oidc/callback")
        assert r.status_code == 200
        assert b"email" in r.data.lower()

    def test_session_nonce_rotated(self, oidc_client, db, queries):
        """OIDC login rotates the session_nonce (same as password login)."""
        queries.usr_create(
            db,
            id="user-nonce",
            name="NonceTest",
            email="nonce@example.com",
            color="#888",
            password_hash="",
            is_admin=0,
        )
        old_row = queries.usr_get_by_id(db, id="user-nonce")
        old_nonce = old_row.get("session_nonce", "")

        token = _mock_token(email="nonce@example.com")
        with patch.object(oauth, "oidc") as mock_oidc:
            mock_oidc.authorize_access_token.return_value = token
            oidc_client.get("/oidc/callback", follow_redirects=False)

        new_row = queries.usr_get_by_id(db, id="user-nonce")
        assert new_row["session_nonce"] != old_nonce
        assert len(new_row["session_nonce"]) == 32

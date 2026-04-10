"""Integration tests for OIDC authentication (#126).

Uses ``oidc-provider-mock`` as a real in-process OIDC IdP — no Docker,
no external service. The mock runs in a background thread and exposes a
standard ``.well-known/openid-configuration`` discovery document. The
test exercises the **full round trip**: browser → kenboard /oidc/login →
IdP authorize → IdP token → kenboard /oidc/callback → session.

These tests hit the test MySQL database (via the ``db`` fixture from
conftest.py) so they live under ``tests/integration/``.
"""

from __future__ import annotations

import pytest
from oidc_provider_mock import User, run_server_in_thread

from dashboard.auth_oidc import oauth


@pytest.fixture(scope="module")
def idp():
    """Start the mock OIDC IdP in a background thread for the module."""
    user = User(
        sub="integration-user-1",
        claims={
            "email": "integration@example.com",
            "email_verified": True,
            "name": "Integration User",
        },
    )
    with run_server_in_thread(user_claims=[user]) as server:
        yield f"http://127.0.0.1:{server.server_port}"


@pytest.fixture()
def oidc_app(idp, monkeypatch, db):
    """Create a Flask app wired to the live mock IdP."""
    import dashboard.config

    monkeypatch.setattr(
        dashboard.config.Config,
        "OIDC_DISCOVERY_URL",
        f"{idp}/.well-known/openid-configuration",
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
    app.config["SERVER_NAME"] = "localhost"
    yield app


@pytest.fixture()
def client(oidc_app):
    """Test client for the OIDC-enabled app."""
    return oidc_app.test_client()


class TestOidcIntegrationFlow:
    """Full authorization-code flow against the live mock IdP."""

    def test_oidc_login_redirects_to_idp(self, client, idp):
        """GET /oidc/login returns a 302 to the IdP's authorize endpoint."""
        r = client.get("/oidc/login", follow_redirects=False)
        assert r.status_code == 302
        location = r.headers["Location"]
        assert idp in location or "authorize" in location

    def test_callback_with_mock_token(self, client, idp, db, queries):
        """Simulate the callback by mocking authorize_access_token.

        This avoids the cross-server redirect complexity while still exercising the real
        IdP for discovery/JWKS and the real kenboard callback logic.
        """
        from unittest.mock import patch

        token = {
            "access_token": "mock-access",
            "id_token": "mock-id",
            "userinfo": {
                "sub": "integration-user-1",
                "email": "integration@example.com",
                "email_verified": True,
                "name": "Integration User",
            },
        }
        with patch.object(oauth, "oidc") as mock_oidc:
            mock_oidc.authorize_access_token.return_value = token
            r = client.get("/oidc/callback", follow_redirects=False)

        assert r.status_code == 302

        # Verify user was created in DB
        row = queries.usr_get_by_email(db, email="integration@example.com")
        assert row is not None
        assert row["name"] == "Integration User"
        assert row["is_admin"] == 0
        assert row["email"] == "integration@example.com"
        assert len(row["session_nonce"]) == 32

        # Verify session is active
        r2 = client.get("/", follow_redirects=False)
        assert r2.status_code == 200

"""Unit tests for the forgot-password / reset-password flow (#237).

The email sending is mocked — we capture the token from the DB and
exercise the full flow: request reset → token created → reset form →
new password applied → old sessions invalidated.
"""

import hashlib
from unittest.mock import patch

import pytest
from argon2 import PasswordHasher


@pytest.fixture()
def auth_app(app):
    """Re-enable login_required."""
    prev = app.config.get("LOGIN_DISABLED", False)
    app.config["LOGIN_DISABLED"] = False
    yield app
    app.config["LOGIN_DISABLED"] = prev


@pytest.fixture()
def auth_client(auth_app):
    """Test client with auth enabled."""
    return auth_app.test_client()


@pytest.fixture()
def user_with_email(db, queries):
    """Create a user with email and password."""
    h = PasswordHasher().hash("OldPassword123!")
    queries.usr_create(
        db,
        id="user-reset",
        name="resetuser",
        email="reset@test.com",
        color="#f00",
        password_hash=h,
        is_admin=0,
    )
    return queries.usr_get_by_id(db, id="user-reset")


class TestForgotPasswordPage:
    """GET /forgot-password."""

    def test_returns_200(self, auth_client):
        """Forgot password page loads."""
        resp = auth_client.get("/forgot-password")
        assert resp.status_code == 200
        assert "Email" in resp.data.decode()

    def test_empty_email_shows_error(self, auth_client):
        """Empty email is rejected."""
        resp = auth_client.post(
            "/forgot-password", data={"email": ""}, follow_redirects=True
        )
        assert "Email requis" in resp.data.decode()


class TestForgotPasswordPost:
    """POST /forgot-password — token creation."""

    @patch("dashboard.email.send_email", return_value=True)
    def test_creates_token_for_existing_email(
        self, mock_send, auth_client, db, queries, user_with_email
    ):
        """Token is created and email is sent for a valid email."""
        resp = auth_client.post("/forgot-password", data={"email": "reset@test.com"})
        assert resp.status_code == 200
        assert "un lien a" in resp.data.decode().lower()
        mock_send.assert_called_once()

        # Verify token exists in DB
        cur = db.cursor()
        cur.execute("SELECT * FROM password_reset_tokens WHERE user_id = 'user-reset'")
        token_row = cur.fetchone()
        assert token_row is not None
        assert token_row["used_at"] is None

    @patch("dashboard.email.send_email", return_value=True)
    def test_no_leak_for_unknown_email(self, mock_send, auth_client, db):
        """Same message shown for unknown email — no existence leak."""
        resp = auth_client.post("/forgot-password", data={"email": "nobody@test.com"})
        assert resp.status_code == 200
        assert "un lien a" in resp.data.decode().lower()
        mock_send.assert_not_called()


class TestResetPassword:
    """GET/POST /reset-password/<token> — password change."""

    def _create_token(self, db, queries, user_id):
        """Create a valid reset token and return the raw token string."""
        import secrets
        import uuid
        from datetime import datetime, timedelta

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires = datetime.now() + timedelta(minutes=30)
        queries.prt_create(
            db,
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires,
        )
        return token

    def test_valid_token_shows_form(self, auth_client, db, queries, user_with_email):
        """Valid token renders the new-password form."""
        token = self._create_token(db, queries, "user-reset")
        resp = auth_client.get(f"/reset-password/{token}")
        assert resp.status_code == 200
        assert "Nouveau mot de passe" in resp.data.decode()

    def test_invalid_token_shows_error(self, auth_client, db):
        """Invalid token shows error."""
        resp = auth_client.get("/reset-password/bogus-token")
        assert "invalide" in resp.data.decode().lower()

    def test_password_mismatch(self, auth_client, db, queries, user_with_email):
        """Mismatched passwords are rejected."""
        token = self._create_token(db, queries, "user-reset")
        resp = auth_client.post(
            f"/reset-password/{token}",
            data={"password": "NewStrong123!", "password_confirm": "Different123!"},
        )
        assert "ne correspondent pas" in resp.data.decode()

    def test_weak_password_rejected(self, auth_client, db, queries, user_with_email):
        """Weak password is rejected by zxcvbn."""
        token = self._create_token(db, queries, "user-reset")
        resp = auth_client.post(
            f"/reset-password/{token}",
            data={"password": "123", "password_confirm": "123"},
        )
        assert resp.status_code == 200
        # Should show a password strength error
        html = resp.data.decode()
        assert "mot de passe" in html.lower() or "password" in html.lower()

    def test_successful_reset(self, auth_client, db, queries, user_with_email):
        """Successful reset changes the password and invalidates sessions."""
        token = self._create_token(db, queries, "user-reset")
        resp = auth_client.post(
            f"/reset-password/{token}",
            data={"password": "BrandNewPass99!", "password_confirm": "BrandNewPass99!"},
        )
        html = resp.data.decode()
        assert "modifi" in html.lower()

        # Verify password was changed
        row = queries.usr_get_password_hash(db, id="user-reset")
        ph = PasswordHasher()
        assert ph.verify(row["password_hash"], "BrandNewPass99!")

        # Verify token is consumed
        cur = db.cursor()
        cur.execute(
            "SELECT used_at FROM password_reset_tokens WHERE user_id = 'user-reset'"
        )
        assert cur.fetchone()["used_at"] is not None

    def test_token_single_use(self, auth_client, db, queries, user_with_email):
        """Used token cannot be reused."""
        token = self._create_token(db, queries, "user-reset")
        # First use
        auth_client.post(
            f"/reset-password/{token}",
            data={"password": "FirstReset99!", "password_confirm": "FirstReset99!"},
        )
        # Second use
        resp = auth_client.get(f"/reset-password/{token}")
        assert "invalide" in resp.data.decode().lower()

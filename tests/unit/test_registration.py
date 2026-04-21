"""Unit tests for the self-registration flow (#236).

The email sending is mocked — we capture the token from the DB and
exercise the full flow: register → token created → verify email →
user + category + project + scope created.
"""

import hashlib
from unittest.mock import patch

import pytest
from argon2 import PasswordHasher

from dashboard.config import Config


@pytest.fixture()
def auth_app(app):
    """Re-enable login_required."""
    prev = app.config.get("LOGIN_DISABLED", False)
    app.config["LOGIN_DISABLED"] = False
    yield app
    app.config["LOGIN_DISABLED"] = prev


@pytest.fixture()
def register_app(auth_app):
    """Enable registration with a test domain."""
    prev_domain = Config.REGISTER_ALLOWED_DOMAIN
    Config.REGISTER_ALLOWED_DOMAIN = "test.com"
    auth_app.config["REGISTER_ALLOWED_DOMAIN"] = "test.com"
    yield auth_app
    Config.REGISTER_ALLOWED_DOMAIN = prev_domain
    if prev_domain:
        auth_app.config["REGISTER_ALLOWED_DOMAIN"] = prev_domain
    else:
        auth_app.config.pop("REGISTER_ALLOWED_DOMAIN", None)


@pytest.fixture()
def register_client(register_app):
    """Test client with registration enabled."""
    return register_app.test_client()


class TestRegisterPage:
    """GET /register."""

    def test_returns_200_when_enabled(self, register_client):
        """Register page loads when domain is configured."""
        resp = register_client.get("/register")
        assert resp.status_code == 200
        assert "test.com" in resp.data.decode()

    def test_returns_404_when_disabled(self, client):
        """Register page returns 404 when no domain configured."""
        prev = Config.REGISTER_ALLOWED_DOMAIN
        Config.REGISTER_ALLOWED_DOMAIN = ""
        try:
            resp = client.get("/register")
            assert resp.status_code == 404
        finally:
            Config.REGISTER_ALLOWED_DOMAIN = prev

    def test_login_shows_register_link(self, register_client):
        """Login page shows 'Créer un compte' when registration enabled."""
        resp = register_client.get("/login")
        assert "register" in resp.data.decode().lower()


class TestRegisterPost:
    """POST /register — email verification token creation."""

    @patch("dashboard.email.send_email", return_value=True)
    def test_valid_registration(self, mock_send, register_client, db, queries):
        """Valid email + password creates a token and sends email."""
        resp = register_client.post(
            "/register",
            data={
                "email": "new@test.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )
        assert resp.status_code == 200
        assert "rification" in resp.data.decode().lower()
        mock_send.assert_called_once()

        # Token exists in DB
        cur = db.cursor()
        cur.execute(
            "SELECT * FROM email_verification_tokens WHERE email = 'new@test.com'"
        )
        row = cur.fetchone()
        assert row is not None
        assert row["used_at"] is None

    def test_wrong_domain_rejected(self, register_client, db):
        """Email from wrong domain is rejected."""
        resp = register_client.post(
            "/register",
            data={
                "email": "user@wrong.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )
        assert "test.com" in resp.data.decode()

    def test_password_mismatch(self, register_client, db):
        """Mismatched passwords are rejected."""
        resp = register_client.post(
            "/register",
            data={
                "email": "user@test.com",
                "password": "StrongPass123!",
                "password_confirm": "Different123!",
            },
        )
        assert "ne correspondent pas" in resp.data.decode()

    def test_weak_password_rejected(self, register_client, db):
        """Weak password is rejected."""
        resp = register_client.post(
            "/register",
            data={
                "email": "user@test.com",
                "password": "123",
                "password_confirm": "123",
            },
        )
        html = resp.data.decode()
        assert "mot de passe" in html.lower() or "password" in html.lower()

    @patch("dashboard.email.send_email", return_value=True)
    def test_duplicate_email_rejected(self, mock_send, register_client, db, queries):
        """Duplicate email is rejected."""
        queries.usr_create(
            db,
            id="existing-user",
            name="existing@test.com",
            email="existing@test.com",
            color="#f00",
            password_hash="x",
            is_admin=0,
        )
        resp = register_client.post(
            "/register",
            data={
                "email": "existing@test.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )
        assert "existe" in resp.data.decode().lower()


class TestVerifyEmail:
    """GET /verify-email/<token> — account activation."""

    def _create_verification_token(self, db, queries, email, password):
        """Create a verification token and return the raw token string."""
        import secrets
        import uuid
        from datetime import datetime, timedelta

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        pw_hash = PasswordHasher().hash(password)
        expires = datetime.now() + timedelta(hours=24)
        queries.evt_create(
            db,
            id=str(uuid.uuid4()),
            email=email,
            password_hash=pw_hash,
            token_hash=token_hash,
            expires_at=expires,
        )
        return token

    def test_valid_token_creates_user(self, register_client, db, queries):
        """Valid verification creates user, category, project, and scope."""
        token = self._create_verification_token(
            db, queries, "alice@test.com", "AlicePass123!"
        )
        resp = register_client.get(f"/verify-email/{token}")
        html = resp.data.decode()
        assert "activ" in html.lower()

        # User created
        user = queries.usr_get_by_email(db, email="alice@test.com")
        assert user is not None
        assert user["is_admin"] == 0
        assert user["name"] == "alice@test.com"

        # Password works
        ph = PasswordHasher()
        assert ph.verify(user["password_hash"], "AlicePass123!")

    def test_creates_users_category(self, register_client, db, queries):
        """Verification creates the 'Users' category."""
        token = self._create_verification_token(
            db, queries, "bob@test.com", "BobPass123!"
        )
        register_client.get(f"/verify-email/{token}")

        cats = list(queries.cat_get_all(db))
        users_cat = [c for c in cats if c["name"] == "Users"]
        assert len(users_cat) == 1

    def test_creates_personal_project(self, register_client, db, queries):
        """Verification creates a project named after the email."""
        token = self._create_verification_token(
            db, queries, "carol@test.com", "CarolPass123!"
        )
        register_client.get(f"/verify-email/{token}")

        cats = list(queries.cat_get_all(db))
        users_cat = [c for c in cats if c["name"] == "Users"][0]
        projects = list(queries.proj_get_by_cat(db, cat_id=users_cat["id"]))
        project_names = [p["name"] for p in projects]
        assert "carol@test.com" in project_names

    def test_grants_write_scope(self, register_client, db, queries):
        """New user gets write scope on the Users category."""
        token = self._create_verification_token(
            db, queries, "dave@test.com", "DavePass123!"
        )
        register_client.get(f"/verify-email/{token}")

        user = queries.usr_get_by_email(db, email="dave@test.com")
        cats = list(queries.cat_get_all(db))
        users_cat = [c for c in cats if c["name"] == "Users"][0]
        scope = queries.usr_scopes_get_for_category(
            db, user_id=user["id"], category_id=users_cat["id"]
        )
        assert scope is not None
        assert scope["scope"] == "write"

    def test_reuses_existing_users_category(self, register_client, db, queries):
        """Second registration reuses the same Users category."""
        t1 = self._create_verification_token(db, queries, "eve@test.com", "EvePass123!")
        register_client.get(f"/verify-email/{t1}")

        t2 = self._create_verification_token(
            db, queries, "frank@test.com", "FrankPass123!"
        )
        register_client.get(f"/verify-email/{t2}")

        cats = list(queries.cat_get_all(db))
        users_cats = [c for c in cats if c["name"] == "Users"]
        assert len(users_cats) == 1

    def test_invalid_token_shows_error(self, register_client, db):
        """Invalid token shows error."""
        resp = register_client.get("/verify-email/bogus-token")
        assert "invalide" in resp.data.decode().lower()

    def test_token_single_use(self, register_client, db, queries):
        """Used token cannot be reused."""
        token = self._create_verification_token(
            db, queries, "gina@test.com", "GinaPass123!"
        )
        register_client.get(f"/verify-email/{token}")
        resp = register_client.get(f"/verify-email/{token}")
        html = resp.data.decode()
        # Either "invalid" or "already exists"
        assert "invalide" in html.lower() or "existe" in html.lower()

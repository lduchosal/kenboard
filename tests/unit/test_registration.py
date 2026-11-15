"""Unit tests for the self-registration flow (#236, #1188, #1189, #1194).

The email sending is mocked — we capture the token from the DB and exercise the full
flow: register (email only) → token created → open the link → choose a password → user +
personal category + project + scope created.
"""

import hashlib
from unittest.mock import patch

import pytest
from argon2 import PasswordHasher

from dashboard.config import Config


@pytest.fixture
def auth_app(app):
    """Re-enable login_required."""
    prev = app.config.get("LOGIN_DISABLED", False)
    app.config["LOGIN_DISABLED"] = False
    yield app
    app.config["LOGIN_DISABLED"] = prev


@pytest.fixture
def register_app(auth_app, monkeypatch):
    """Enable registration with a test domain."""
    monkeypatch.setattr(Config, "REGISTER_ALLOWED_DOMAIN", "test.com")
    monkeypatch.setitem(auth_app.config, "REGISTER_ALLOWED_DOMAIN", "test.com")
    return auth_app


@pytest.fixture
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

    def test_returns_404_when_disabled(self, client, monkeypatch):
        """Register page returns 404 when no domain configured."""
        monkeypatch.setattr(Config, "REGISTER_ALLOWED_DOMAIN", "")
        resp = client.get("/register")
        assert resp.status_code == 404

    def test_login_shows_register_link(self, register_client):
        """Login page shows 'Créer un compte' when registration enabled."""
        resp = register_client.get("/login")
        assert "register" in resp.data.decode().lower()


class TestRegisterPost:
    """POST /register — email verification token creation."""

    @patch("dashboard.email.send_email", return_value=True)
    def test_valid_registration(self, mock_send, register_client, db, queries):
        """A valid email creates a token (without any password) and sends email."""
        resp = register_client.post("/register", data={"email": "new@test.com"})
        assert resp.status_code == 200
        assert "rification" in resp.data.decode().lower()
        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs["to"] == "new@test.com"

        cur = db.cursor()
        cur.execute(
            "SELECT * FROM email_verification_tokens WHERE email = 'new@test.com'"
        )
        row = cur.fetchone()
        assert row is not None
        assert row["used_at"] is None
        assert row["password_hash"] == ""

    @patch("dashboard.email.send_email", return_value=True)
    def test_password_fields_are_ignored(self, mock_send, register_client, db):
        """#1194 — a password posted with the email never reaches the token."""
        register_client.post(
            "/register",
            data={
                "email": "victim@test.com",
                "password": "AttackerPass123!",
                "password_confirm": "AttackerPass123!",
            },
        )
        cur = db.cursor()
        cur.execute("SELECT password_hash FROM email_verification_tokens")
        assert cur.fetchone()["password_hash"] == ""

    @patch("dashboard.email.send_email", return_value=True)
    def test_wrong_domain_rejected(self, mock_send, register_client, db):
        """Email from wrong domain is rejected."""
        resp = register_client.post("/register", data={"email": "user@wrong.com"})
        assert "Seules les adresses" in resp.data.decode()
        mock_send.assert_not_called()

    @pytest.mark.parametrize(
        "email",
        [
            "a@evil.com (x@test.com",
            "a@evil.com, x@test.com",
            "<a@evil.com>x@test.com",
            "a@evil.com <x@test.com",
            '"x" <a@evil.com>@test.com',
            "a@evil.com>@test.com",
            "a@evil.com;x@test.com",
            "a@evil.com\n@test.com",
            "a@evil.com@test.com",
            "x@test.com\r\nBcc: a@evil.com@test.com",
            "x y@test.com",
            "x@sub.test.com",
            "x@eviltest.com",
            "@test.com",
        ],
    )
    @patch("dashboard.email.send_email", return_value=True)
    def test_forged_address_rejected(self, mock_send, register_client, db, email):
        """#1188 — only a single bare address of the allowed domain is accepted.

        Every string here ends with the allowed domain, or parses to a recipient
        outside it: none may create a token or trigger a mail.
        """
        resp = register_client.post("/register", data={"email": email})
        assert "Seules les adresses" in resp.data.decode()
        mock_send.assert_not_called()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM email_verification_tokens")
        assert cur.fetchone()["n"] == 0

    @patch("dashboard.email.send_email", return_value=True)
    def test_domain_match_is_case_insensitive(self, mock_send, register_client, db):
        """``User@TEST.com`` is the same mailbox — accepted, stored lowercased."""
        register_client.post("/register", data={"email": "User@TEST.com"})
        assert mock_send.call_args.kwargs["to"] == "user@test.com"

    @patch("dashboard.email.send_email", return_value=True)
    def test_duplicate_email_is_not_revealed(
        self, mock_send, register_client, db, queries
    ):
        """An existing account gets the same answer, no token and no mail."""
        queries.usr_create(
            db,
            id="existing-user",
            name="existing@test.com",
            email="existing@test.com",
            color="#f00",
            password_hash="x",
            is_admin=0,
        )
        fresh = register_client.post("/register", data={"email": "fresh@test.com"})
        mock_send.reset_mock()
        taken = register_client.post("/register", data={"email": "existing@test.com"})
        assert taken.data == fresh.data
        mock_send.assert_not_called()


class TestVerifyEmail:
    """/verify-email/<token> — choose a password, then account activation."""

    PASSWORD = "AlicePass123!"

    def _create_verification_token(self, db, queries, email, password_hash=""):
        """Create a verification token and return the raw token string."""
        import secrets
        import uuid

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        queries.evt_create(
            db,
            id=str(uuid.uuid4()),
            email=email,
            password_hash=password_hash,
            token_hash=token_hash,
            hours=24,
        )
        return token

    def _activate(self, client, token, password=None, confirm=None):
        """POST the password form of a verification link."""
        password = password or self.PASSWORD
        return client.post(
            f"/verify-email/{token}",
            data={"password": password, "password_confirm": confirm or password},
        )

    def test_get_shows_password_form_and_creates_nothing(
        self, register_client, db, queries
    ):
        """Opening the link (mail scanners do) must not create the account."""
        token = self._create_verification_token(db, queries, "alice@test.com")
        resp = register_client.get(f"/verify-email/{token}")
        html = resp.data.decode()
        assert f'action="/verify-email/{token}"' in html
        assert 'name="password_confirm"' in html
        assert queries.usr_get_by_email(db, email="alice@test.com") is None
        # ... and the token is still usable afterwards.
        assert "activ" in self._activate(register_client, token).data.decode().lower()

    def test_valid_token_creates_user(self, register_client, db, queries):
        """Posting a password creates the user with that password."""
        token = self._create_verification_token(db, queries, "alice@test.com")
        resp = self._activate(register_client, token)
        assert "activ" in resp.data.decode().lower()

        user = queries.usr_get_by_email(db, email="alice@test.com")
        assert user is not None
        assert user["is_admin"] == 0
        assert user["name"] == "alice@test.com"
        assert PasswordHasher().verify(user["password_hash"], self.PASSWORD)

    def test_password_stored_with_token_is_ignored(self, register_client, db, queries):
        """#1194 — a hash that travelled with the token never becomes the password.

        Covers tokens issued before the fix (and any forged one): the account gets the
        password typed by whoever opened the mailbox link.
        """
        attacker_hash = PasswordHasher().hash("AttackerPass123!")
        token = self._create_verification_token(
            db, queries, "victim@test.com", attacker_hash
        )
        self._activate(register_client, token)
        user = queries.usr_get_by_email(db, email="victim@test.com")
        assert user["password_hash"] != attacker_hash
        assert PasswordHasher().verify(user["password_hash"], self.PASSWORD)

    def test_password_mismatch(self, register_client, db, queries):
        """Mismatched passwords re-render the form; nothing is created."""
        token = self._create_verification_token(db, queries, "bob@test.com")
        resp = self._activate(register_client, token, confirm="Different123!")
        assert "ne correspondent pas" in resp.data.decode()
        assert queries.usr_get_by_email(db, email="bob@test.com") is None

    def test_weak_password_rejected(self, register_client, db, queries):
        """A weak password is rejected and the token stays valid."""
        token = self._create_verification_token(db, queries, "bob@test.com")
        resp = self._activate(register_client, token, password="123")
        html = resp.data.decode()
        assert "mot de passe" in html.lower() or "password" in html.lower()
        assert queries.usr_get_by_email(db, email="bob@test.com") is None
        assert "activ" in self._activate(register_client, token).data.decode().lower()

    def test_creates_personal_category_and_project(self, register_client, db, queries):
        """#1189 — the user gets a category of their own holding their project."""
        token = self._create_verification_token(db, queries, "carol@test.com")
        self._activate(register_client, token)

        cats = [c for c in queries.cat_get_all(db) if c["name"] == "carol@test.com"]
        assert len(cats) == 1
        projects = list(queries.proj_get_by_cat(db, cat_id=cats[0]["id"]))
        assert [p["name"] for p in projects] == ["carol@test.com"]

    def test_grants_write_scope_on_own_category_only(
        self, register_client, db, queries
    ):
        """#1189 — one scope per user, on their own category; no shared board."""
        for email in ("dave@test.com", "eve@test.com"):
            self._activate(
                register_client, self._create_verification_token(db, queries, email)
            )
        cats = {c["name"]: c["id"] for c in queries.cat_get_all(db)}
        assert "Users" not in cats
        for email, other in (
            ("dave@test.com", "eve@test.com"),
            ("eve@test.com", "dave@test.com"),
        ):
            user = queries.usr_get_by_email(db, email=email)
            scopes = list(queries.usr_scopes_get(db, user_id=user["id"]))
            assert scopes == [{"category_id": cats[email], "scope": "write"}]
            assert cats[other] not in [s["category_id"] for s in scopes]

    def test_invalid_token_shows_error(self, register_client, db):
        """Invalid token shows error, on GET and on POST."""
        assert "invalide" in register_client.get("/verify-email/bogus").data.decode()
        assert "invalide" in self._activate(register_client, "bogus").data.decode()

    def test_token_single_use(self, register_client, db, queries):
        """Used token cannot be reused."""
        token = self._create_verification_token(db, queries, "gina@test.com")
        self._activate(register_client, token)
        for resp in (
            register_client.get(f"/verify-email/{token}"),
            self._activate(register_client, token),
        ):
            assert "invalide" in resp.data.decode().lower()

    def test_email_taken_meanwhile(self, register_client, db, queries):
        """Race guard: the address got an account before the link was used."""
        token = self._create_verification_token(db, queries, "hank@test.com")
        queries.usr_create(
            db,
            id="hank",
            name="hank",
            email="hank@test.com",
            color="#f00",
            password_hash="x",
            is_admin=0,
        )
        resp = self._activate(register_client, token)
        assert "existe" in resp.data.decode().lower()
        assert queries.usr_get_by_email(db, email="hank@test.com")["id"] == "hank"

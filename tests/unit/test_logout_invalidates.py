"""Server-side session invalidation on /logout (ken #54).

Flask's default sessions are signed cookies, so the server cannot
unilaterally revoke them. We embed a per-user ``session_nonce`` in the
cookie identifier and rotate it on /logout. The user_loader refuses any
cookie whose nonce doesn't match the current row in DB → captured cookies
become unusable after logout.

These tests run with ``LOGIN_DISABLED=False`` so the user_loader actually
runs.
"""

from __future__ import annotations

import pytest
from argon2 import PasswordHasher

from dashboard.auth_user import _rotate_session_nonce


@pytest.fixture()
def auth_app(app):
    """Re-enable Flask-Login on the shared app fixture."""
    prev = app.config.get("LOGIN_DISABLED", False)
    app.config["LOGIN_DISABLED"] = False
    yield app
    app.config["LOGIN_DISABLED"] = prev


@pytest.fixture()
def auth_client(auth_app):
    """Test client wired to the auth-enabled app."""
    return auth_app.test_client()


@pytest.fixture()
def seeded_user(db, queries):
    """Insert a user 'logout_test' with password 'logoutpw123'."""
    h = PasswordHasher().hash("logoutpw123")
    queries.usr_create(
        db,
        id="user-logout",
        name="logout_test",
        color="#888",
        password_hash=h,
        is_admin=1,
    )
    return queries.usr_get_by_id(db, id="user-logout")


def _login(client, name="logout_test", password="logoutpw123"):
    """Submit the login form and return the response."""
    return client.post(
        "/login",
        data={"name": name, "password": password},
        follow_redirects=False,
    )


class TestSessionNonce:
    """The user_loader refuses cookies whose embedded nonce is stale."""

    def test_login_seeds_a_session_nonce(self, auth_client, seeded_user, db, queries):
        # Initially the seeded user has an empty nonce
        assert seeded_user["session_nonce"] == ""
        r = _login(auth_client)
        assert r.status_code == 302
        # After login, the nonce in DB is non-empty
        row = queries.usr_get_by_id(db, id="user-logout")
        assert row["session_nonce"] != ""
        assert len(row["session_nonce"]) == 32  # hex(16)

    def test_session_works_after_login(self, auth_client, seeded_user, db):
        _login(auth_client)
        r = auth_client.get("/")
        # 200 = page rendered, 302 to /login = NOT logged in
        assert r.status_code == 200

    def test_logout_rotates_the_nonce(self, auth_client, seeded_user, db, queries):
        _login(auth_client)
        before = queries.usr_get_by_id(db, id="user-logout")["session_nonce"]
        r = auth_client.post("/logout", headers={"Origin": "http://localhost"})
        assert r.status_code == 302
        after = queries.usr_get_by_id(db, id="user-logout")["session_nonce"]
        assert after != before
        assert after != ""

    def test_replay_after_logout_is_rejected(
        self, auth_client, seeded_user, db, queries
    ):
        """The captured cookie must NOT grant access after /logout."""
        _login(auth_client)
        # Capture cookies (the test client cookie jar is shared with auth_client)
        cookies_before = dict(auth_client._cookies)
        # Sanity check
        assert auth_client.get("/").status_code == 200
        # Logout — same client, sends Origin same-origin to pass CSRF
        auth_client.post("/logout", headers={"Origin": "http://localhost"})
        # Restore the pre-logout cookies into the client
        auth_client._cookies = cookies_before
        # Replaying the captured cookies should redirect to /login
        r = auth_client.get("/", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.location

    def test_re_login_keeps_existing_nonce(self, auth_client, seeded_user, db, queries):
        """Logging in again does NOT rotate the nonce — only logout does."""
        _login(auth_client)
        first = queries.usr_get_by_id(db, id="user-logout")["session_nonce"]
        # New client, log in again
        with auth_client.application.test_client() as c2:
            _login(c2)
        second = queries.usr_get_by_id(db, id="user-logout")["session_nonce"]
        assert first == second

    def test_external_nonce_rotation_invalidates_session(
        self, auth_client, seeded_user, db, queries
    ):
        """An admin (or scheduled job) can force-logout a user by rotating the nonce."""
        _login(auth_client)
        assert auth_client.get("/").status_code == 200
        # Pretend an admin rotates the nonce out-of-band
        _rotate_session_nonce("user-logout")
        # The previously-issued cookie is now stale
        r = auth_client.get("/", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.location

    def test_login_again_after_logout_works(self, auth_client, seeded_user, db):
        """After /logout, the user can still log back in normally."""
        _login(auth_client)
        auth_client.post("/logout", headers={"Origin": "http://localhost"})
        # Need a fresh client for the second login (cookies cleared)
        with auth_client.application.test_client() as c2:
            r = _login(c2)
            assert r.status_code == 302
            assert c2.get("/").status_code == 200

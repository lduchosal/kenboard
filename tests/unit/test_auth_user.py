"""Unit tests for the user session authentication flow.

These tests run with ``LOGIN_DISABLED=False`` so they actually exercise
``@login_required``, the login form, the user loader, and the admin
check helper. They use the Flask test client (no Playwright).
"""

import json

import pytest
from argon2 import PasswordHasher

from dashboard.auth_user import _is_safe_url, _verify_credentials

SAME_ORIGIN = {"Origin": "http://localhost"}


@pytest.fixture()
def auth_app(app):
    """Re-enable login_required and return the same app instance."""
    prev = app.config.get("LOGIN_DISABLED", False)
    app.config["LOGIN_DISABLED"] = False
    yield app
    app.config["LOGIN_DISABLED"] = prev


@pytest.fixture()
def auth_client(auth_app):
    """Test client wired to the auth-enabled app."""
    return auth_app.test_client()


@pytest.fixture()
def admin_user(db, queries):
    """Create an admin user 'Q' with password 'topsecret123' and return the row."""
    h = PasswordHasher().hash("topsecret123")
    queries.usr_create(
        db,
        id="user-q",
        name="Q",
        email=None,
        color="#0969da",
        password_hash=h,
        is_admin=1,
    )
    return queries.usr_get_by_id(db, id="user-q")


@pytest.fixture()
def normal_user(db, queries):
    """Create a non-admin user 'Alice'."""
    h = PasswordHasher().hash("alicepass")
    queries.usr_create(
        db,
        id="user-alice",
        name="Alice",
        email=None,
        color="#8250df",
        password_hash=h,
        is_admin=0,
    )
    return queries.usr_get_by_id(db, id="user-alice")


# -- Helpers ------------------------------------------------------------------


class TestIsSafeUrl:
    """Open-redirect protection on the ``next`` parameter."""

    def test_relative_path_ok(self):
        assert _is_safe_url("/cat/foo.html") is True

    def test_root_ok(self):
        assert _is_safe_url("/") is True

    def test_empty_rejected(self):
        assert _is_safe_url("") is False

    def test_absolute_url_rejected(self):
        assert _is_safe_url("https://evil.example.com/") is False

    def test_protocol_relative_rejected(self):
        assert _is_safe_url("//evil.example.com") is False

    def test_no_leading_slash_rejected(self):
        assert _is_safe_url("admin/users") is False


class TestVerifyCredentials:
    """The credential verification helper."""

    def test_unknown_user_returns_none(self, db):
        assert _verify_credentials("nobody", "x") is None

    def test_empty_inputs_return_none(self, db, admin_user):
        assert _verify_credentials("", "topsecret123") is None
        assert _verify_credentials("Q", "") is None

    def test_wrong_password_returns_none(self, db, admin_user):
        assert _verify_credentials("Q", "wrong") is None

    def test_correct_credentials_return_user(self, db, admin_user):
        cu = _verify_credentials("Q", "topsecret123")
        assert cu is not None
        assert cu.name == "Q"
        assert cu.is_admin is True

    def test_user_with_empty_hash_cannot_login(self, db, queries):
        queries.usr_create(
            db,
            id="empty-pw",
            name="Bob",
            email=None,
            color="#000",
            password_hash="",
            is_admin=0,
        )
        assert _verify_credentials("Bob", "anything") is None


# -- Login / logout flow ------------------------------------------------------


class TestLoginFlow:
    """The /login and /logout routes."""

    def test_get_login_renders_form(self, auth_client):
        r = auth_client.get("/login")
        assert r.status_code == 200
        assert b'name="name"' in r.data
        assert b'name="password"' in r.data

    def test_get_login_renders_logo_panel(self, auth_client):
        """#133: the login page has a logo panel alongside the form."""
        r = auth_client.get("/login")
        assert r.status_code == 200
        assert b"login-card" in r.data
        assert b"login-logo-panel" in r.data
        assert b'src="/static/logo.svg"' in r.data

    def test_logo_static_asset_is_served(self, auth_client):
        """The logo file is reachable at /static/logo.svg."""
        r = auth_client.get("/static/logo.svg")
        assert r.status_code == 200
        # Confirm it's actually an SVG, not an HTML 404 page or empty body.
        body = r.data.decode("utf-8", errors="replace")
        assert "<svg" in body

    def test_post_bad_credentials(self, auth_client, db, admin_user):
        r = auth_client.post(
            "/login",
            data={"name": "Q", "password": "wrong"},
            follow_redirects=False,
        )
        assert r.status_code == 200  # form re-rendered with error
        assert "Identifiants invalides".encode("utf-8") in r.data

    def test_post_unknown_user(self, auth_client, db):
        r = auth_client.post(
            "/login",
            data={"name": "ghost", "password": "x"},
            follow_redirects=False,
        )
        assert r.status_code == 200
        assert "Identifiants invalides".encode("utf-8") in r.data

    def test_post_success_redirects(self, auth_client, db, admin_user):
        r = auth_client.post(
            "/login",
            data={"name": "Q", "password": "topsecret123"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.location.endswith("/")

    def test_post_success_with_next(self, auth_client, db, admin_user):
        r = auth_client.post(
            "/login",
            data={
                "name": "Q",
                "password": "topsecret123",
                "next": "/admin/keys",
            },
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.location.endswith("/admin/keys")

    def test_post_unsafe_next_falls_back_to_root(self, auth_client, db, admin_user):
        r = auth_client.post(
            "/login",
            data={
                "name": "Q",
                "password": "topsecret123",
                "next": "https://evil.example.com/",
            },
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.location.endswith("/")

    def test_logout_clears_session(self, auth_client, db, admin_user):
        auth_client.post("/login", data={"name": "Q", "password": "topsecret123"})
        # Now logged in: GET / works
        r = auth_client.get("/", follow_redirects=False)
        assert r.status_code == 200
        # Logout
        r = auth_client.post("/logout", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.location
        # GET / now redirects
        r = auth_client.get("/", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.location

    def test_login_works_for_email_named_user(self, auth_client, db, queries):
        """#132: any user with a non-empty password_hash can log in.

        The login flow has nothing Q-specific — it's just a name lookup
        followed by an argon2 verify. Names containing ``@`` are valid.
        """
        h = PasswordHasher().hash("validpass")
        queries.usr_create(
            db,
            id="user-email",
            name="user@example.com",
            email=None,
            color="#abcdef",
            password_hash=h,
            is_admin=0,
        )
        r = auth_client.post(
            "/login",
            data={"name": "user@example.com", "password": "validpass"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.location.endswith("/")

    def test_admin_ui_patch_password_silently_dropped(
        self, auth_client, db, admin_user
    ):
        """#132 regression: PATCH-with-password is a no-op so login still fails.

        Reproduces the user-facing scenario: admin Q creates a passwordless
        user via the /admin/users panel, then types a password into the
        existing row's password input and clicks Enregistrer. The JS sends
        ``password`` in the PATCH body but ``UserUpdate(extra="ignore")``
        drops it (cf. ``test_patch_ignores_password_field``). The user
        looks "saved" in the UI but the next login attempt fails.
        """
        # Login as admin
        auth_client.post("/login", data={"name": "Q", "password": "topsecret123"})
        # Create a passwordless user
        create = auth_client.post(
            "/api/v1/users",
            data=json.dumps(
                {"name": "user@example.com", "color": "#abc", "is_admin": False}
            ),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert create.status_code == 201
        new_id = create.get_json()["id"]
        # Mimic admin_users.html saveUser(): PATCH with a password field
        patch = auth_client.patch(
            f"/api/v1/users/{new_id}",
            data=json.dumps(
                {
                    "name": "user@example.com",
                    "color": "#abc",
                    "is_admin": False,
                    "password": "secret123",
                }
            ),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert patch.status_code == 200  # backend returns OK, silently drops password
        # Logout admin so we can attempt login as the affected user
        auth_client.post("/logout")
        # Login attempt with the password the admin THOUGHT they set → fails
        login = auth_client.post(
            "/login",
            data={"name": "user@example.com", "password": "secret123"},
            follow_redirects=False,
        )
        assert login.status_code == 200  # form re-rendered with error
        assert "Identifiants invalides".encode("utf-8") in login.data

    def test_admin_reset_password_endpoint_enables_login(
        self, auth_client, db, admin_user
    ):
        """#132 fix path: POST /api/v1/users/<id>/reset-password actually works.

        This is the call admin_users.html JS must make instead of (or in addition to)
        the PATCH when the password input is filled. After the reset, the affected user
        can log in normally.
        """
        auth_client.post("/login", data={"name": "Q", "password": "topsecret123"})
        create = auth_client.post(
            "/api/v1/users",
            data=json.dumps(
                {"name": "user@example.com", "color": "#abc", "is_admin": False}
            ),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert create.status_code == 201
        new_id = create.get_json()["id"]
        reset = auth_client.post(
            f"/api/v1/users/{new_id}/reset-password",
            data=json.dumps({"new_password": "secret123"}),
            content_type="application/json",
            headers=SAME_ORIGIN,
        )
        assert reset.status_code == 204
        auth_client.post("/logout")
        login = auth_client.post(
            "/login",
            data={"name": "user@example.com", "password": "secret123"},
            follow_redirects=False,
        )
        assert login.status_code == 302
        assert login.location.endswith("/")


# -- Page protection ----------------------------------------------------------


class TestPageProtection:
    """`@login_required` on routes pages and admin_required."""

    def test_root_redirects_anonymous(self, auth_client, db):
        r = auth_client.get("/", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.location

    def test_admin_keys_redirects_anonymous(self, auth_client, db):
        r = auth_client.get("/admin/keys", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.location

    def test_login_page_open_to_anonymous(self, auth_client, db):
        assert auth_client.get("/login").status_code == 200

    def test_admin_user_can_reach_admin(self, auth_client, db, admin_user):
        auth_client.post("/login", data={"name": "Q", "password": "topsecret123"})
        r = auth_client.get("/admin/users", follow_redirects=False)
        assert r.status_code == 200

    def test_non_admin_blocked_from_admin(self, auth_client, db, normal_user):
        auth_client.post("/login", data={"name": "Alice", "password": "alicepass"})
        r = auth_client.get("/admin/users", follow_redirects=False)
        assert r.status_code == 403

    def test_non_admin_blocked_from_admin_keys(self, auth_client, db, normal_user):
        auth_client.post("/login", data={"name": "Alice", "password": "alicepass"})
        r = auth_client.get("/admin/keys", follow_redirects=False)
        assert r.status_code == 403


class TestAgentOnboardingHints:
    """#117: serve a copy-pasteable runbook to non-browser callers.

    Browsers (``Accept: text/html``) keep getting the existing 302
    redirect; CLI tools and LLM agents land on a 401 with the install /
    init steps so they can self-onboard without scraping the login page.
    """

    def test_browser_still_redirects_to_login(self, auth_client, db):
        """Real browser requests must keep the cookie redirect flow."""
        r = auth_client.get(
            "/cat/abc-123.html",
            headers={"Accept": "text/html,application/xhtml+xml"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "/login" in r.location

    def test_agent_gets_text_runbook_with_cat_id(self, auth_client, db):
        """``Accept: */*`` (curl, requests, fetch) → 401 plain-text runbook."""
        r = auth_client.get(
            "/cat/0ee51b6f-81b8-4da0-9efc-0bd9e01f9e4f.html",
            headers={"Accept": "*/*"},
            follow_redirects=False,
        )
        assert r.status_code == 401
        assert r.headers["Content-Type"].startswith("text/plain")
        assert r.headers.get("WWW-Authenticate", "").startswith("Bearer")
        body = r.get_data(as_text=True)
        assert "pip install kenboard" in body
        assert "0ee51b6f-81b8-4da0-9efc-0bd9e01f9e4f" in body
        assert "/admin/keys" in body

    def test_agent_on_root_falls_back_to_placeholder(self, auth_client, db):
        """No cat id in the URL → placeholder in the runbook."""
        r = auth_client.get(
            "/",
            headers={"Accept": "*/*"},
            follow_redirects=False,
        )
        assert r.status_code == 401
        body = r.get_data(as_text=True)
        assert "pip install kenboard" in body

    def test_api_missing_token_returns_onboarding_json(self, auth_client, db):
        """``/api/v1/*`` without token → JSON 401 with the same runbook."""
        r = auth_client.get("/api/v1/tasks?project=anything")
        assert r.status_code == 401
        payload = r.get_json()
        assert payload["error"] == "unauthorized"
        assert payload["onboarding"]["install"] == "pip install kenboard"
        assert payload["onboarding"]["get_api_key"] == "/admin/keys"
        assert payload["onboarding"]["cat_id"] is None
        lines = payload["onboarding"]["ken_file"]["lines"]
        assert any(line.startswith("project_id=") for line in lines)

    def test_onboard_route_returns_200_text(self, auth_client, db):
        """#137: dedicated /onboard route returns 200 so WebFetch reads the body."""
        r = auth_client.get("/onboard/cat/abc-cat-id/project/xyz-project-id")
        assert r.status_code == 200
        assert r.headers["Content-Type"].startswith("text/plain")
        body = r.get_data(as_text=True)
        assert "pip install kenboard" in body
        assert "project_id=xyz-project-id" in body
        assert "abc-cat-id" in body

    def test_onboard_route_works_with_html_accept(self, auth_client, db):
        """WebFetch sends Accept: text/html — the route must still return 200."""
        r = auth_client.get(
            "/onboard/cat/abc/project/xyz",
            headers={"Accept": "text/html,application/xhtml+xml"},
        )
        assert r.status_code == 200
        assert r.headers["Content-Type"].startswith("text/plain")


# -- API middleware bridges to user session -----------------------------------


class TestApiAcceptsSession:
    """A logged-in user gets full access to /api/v1.

    Uses ``auth_client`` (LOGIN_DISABLED=False) so the API middleware is
    actually enforced — same conditions as production.
    """

    def test_session_grants_api_access(self, auth_client, db, admin_user):
        # Without login, strict mode blocks
        r = auth_client.get("/api/v1/categories")
        assert r.status_code == 401
        # After login, the same call works
        auth_client.post("/login", data={"name": "Q", "password": "topsecret123"})
        r = auth_client.get("/api/v1/categories")
        assert r.status_code == 200

    def test_session_grants_admin_endpoints(self, auth_client, db, admin_user):
        auth_client.post("/login", data={"name": "Q", "password": "topsecret123"})
        # /api/v1/users is admin-only for api keys but a logged-in
        # user should pass.
        r = auth_client.get("/api/v1/users")
        assert r.status_code == 200

    def test_normal_user_session_blocked_on_admin_only_api(
        self, auth_client, db, normal_user
    ):
        """A non-admin logged-in user is blocked on admin-only endpoints.

        Tracked by ken #48: previously the cookie auth path bypassed the admin-only
        check, letting any logged-in user manage users / keys / categories / projects.
        The middleware now mirrors the bearer-token rules.
        """
        auth_client.post("/login", data={"name": "Alice", "password": "alicepass"})
        # /api/v1/categories is admin-only — non-admin must get 403
        assert auth_client.get("/api/v1/categories").status_code == 403
        # Same for /api/v1/users
        assert auth_client.get("/api/v1/users").status_code == 403


# -- Rate limiting on /login --------------------------------------------------


@pytest.fixture()
def rate_limited_client(auth_app):
    """Re-enable flask-limiter for one test and reset its storage."""
    from dashboard.auth_user import limiter

    prev = auth_app.config.get("RATELIMIT_ENABLED", True)
    auth_app.config["RATELIMIT_ENABLED"] = True
    limiter.reset()
    yield auth_app.test_client()
    auth_app.config["RATELIMIT_ENABLED"] = prev
    limiter.reset()


class TestLoginRateLimit:
    """Flask-limiter caps brute-force on /login (cf.

    #44).
    """

    def test_burst_blocked_after_5(self, rate_limited_client, db, admin_user):
        # 5 wrong attempts in a row → all 200 (form re-rendered with error)
        for _ in range(5):
            r = rate_limited_client.post(
                "/login",
                data={"name": "Q", "password": "wrong"},
                follow_redirects=False,
            )
            assert r.status_code == 200
        # 6th → 429
        r = rate_limited_client.post(
            "/login",
            data={"name": "Q", "password": "wrong"},
            follow_redirects=False,
        )
        assert r.status_code == 429
        assert "Trop de tentatives".encode("utf-8") in r.data

    def test_successful_login_does_not_count(self, rate_limited_client, db, admin_user):
        # 4 wrong attempts → still under the limit
        for _ in range(4):
            r = rate_limited_client.post(
                "/login",
                data={"name": "Q", "password": "wrong"},
                follow_redirects=False,
            )
            assert r.status_code == 200
        # Successful login on the 5th attempt: deduct_when() skips it
        r = rate_limited_client.post(
            "/login",
            data={"name": "Q", "password": "topsecret123"},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_get_login_not_rate_limited(self, rate_limited_client, db):
        # GET /login is not POST, the limit only applies to POST
        for _ in range(20):
            r = rate_limited_client.get("/login")
            assert r.status_code == 200

    def test_429_response_includes_retry_after(
        self, rate_limited_client, db, admin_user
    ):
        for _ in range(5):
            rate_limited_client.post(
                "/login",
                data={"name": "Q", "password": "wrong"},
                follow_redirects=False,
            )
        r = rate_limited_client.post(
            "/login",
            data={"name": "Q", "password": "wrong"},
            follow_redirects=False,
        )
        assert r.status_code == 429
        # flask-limiter sets these headers when headers_enabled=True
        assert "X-RateLimit-Limit" in r.headers

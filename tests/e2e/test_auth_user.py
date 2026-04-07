"""End-to-end tests for the user login flow.

These tests run a dedicated Flask server with ``LOGIN_DISABLED=False``
so that ``@login_required`` actually fires. The session-scoped
``live_server`` from ``conftest.py`` keeps ``LOGIN_DISABLED=True`` for
all the other e2e tests, so we spin up our own thread here.
"""

import threading
import time

import pymysql
import pytest
from argon2 import PasswordHasher
from playwright.sync_api import Page, expect

from dashboard.app import create_app
from dashboard.config import Config

AUTH_PORT = 5098


def _get_test_connection():
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_TEST_USER,
        password=Config.DB_TEST_PASSWORD,
        database=Config.DB_TEST_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


@pytest.fixture(scope="module")
def auth_server():
    """Spin up a dedicated Flask server with LOGIN_DISABLED=False."""
    import dashboard.db as db_module

    db_module.get_connection = _get_test_connection

    app = create_app()
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = False

    server = threading.Thread(
        target=lambda: app.run(port=AUTH_PORT, use_reloader=False),
        daemon=True,
    )
    server.start()
    time.sleep(1)
    return f"http://localhost:{AUTH_PORT}"


@pytest.fixture()
def seeded_admin(clean_db):
    """Create user Q (admin) with password 'topsecret123' before each test."""
    from dashboard.db import load_queries

    h = PasswordHasher().hash("topsecret123")
    conn = _get_test_connection()
    try:
        load_queries().usr_create(
            conn,
            id="user-q-e2e",
            name="Q",
            color="#0969da",
            password_hash=h,
            is_admin=1,
        )
    finally:
        conn.close()


@pytest.fixture()
def seeded_normal(clean_db):
    """Create non-admin user Alice with password 'alicepass'."""
    from dashboard.db import load_queries

    h = PasswordHasher().hash("alicepass")
    conn = _get_test_connection()
    try:
        load_queries().usr_create(
            conn,
            id="user-alice-e2e",
            name="Alice",
            color="#8250df",
            password_hash=h,
            is_admin=0,
        )
    finally:
        conn.close()


class TestLoginFlow:
    """End-to-end browser flow for login / logout / page protection."""

    def test_anonymous_redirected_to_login(self, auth_server, clean_db, page: Page):
        page.goto(auth_server + "/")
        page.wait_for_url(lambda url: "/login" in url)
        expect(page.locator("form[action='/login']")).to_be_visible()

    def test_admin_login_succeeds(self, auth_server, seeded_admin, page: Page):
        page.goto(auth_server + "/login")
        page.fill("input[name='name']", "Q")
        page.fill("input[name='password']", "topsecret123")
        page.click("button[type='submit']")
        page.wait_for_url(auth_server + "/")
        expect(page.locator("h1")).to_have_text("KENBOARD")

    def test_bad_password_shows_error(self, auth_server, seeded_admin, page: Page):
        page.goto(auth_server + "/login")
        page.fill("input[name='name']", "Q")
        page.fill("input[name='password']", "wrong")
        page.click("button[type='submit']")
        expect(page.locator(".login-error")).to_be_visible()
        expect(page.locator(".login-error")).to_contain_text("Identifiants invalides")

    def test_logout_clears_session(self, auth_server, seeded_admin, page: Page):
        # Login
        page.goto(auth_server + "/login")
        page.fill("input[name='name']", "Q")
        page.fill("input[name='password']", "topsecret123")
        page.click("button[type='submit']")
        page.wait_for_url(auth_server + "/")
        # Open avatar dropdown and submit logout form
        page.click(".avatar-btn")
        page.click(".logout-form button[type='submit']")
        page.wait_for_url(lambda url: "/login" in url)
        # New visit to / redirects again
        page.goto(auth_server + "/")
        page.wait_for_url(lambda url: "/login" in url)

    def test_admin_only_pages_block_normal_user(
        self, auth_server, seeded_normal, page: Page
    ):
        page.goto(auth_server + "/login")
        page.fill("input[name='name']", "Alice")
        page.fill("input[name='password']", "alicepass")
        page.click("button[type='submit']")
        page.wait_for_url(auth_server + "/")
        # Direct nav to /admin/users → 403
        resp = page.goto(auth_server + "/admin/users")
        assert resp is not None
        assert resp.status == 403

    def test_admin_user_reaches_admin_pages(
        self, auth_server, seeded_admin, page: Page
    ):
        page.goto(auth_server + "/login")
        page.fill("input[name='name']", "Q")
        page.fill("input[name='password']", "topsecret123")
        page.click("button[type='submit']")
        page.wait_for_url(auth_server + "/")
        resp = page.goto(auth_server + "/admin/users")
        assert resp is not None
        assert resp.status == 200
        expect(page.locator("#users-table")).to_be_visible()

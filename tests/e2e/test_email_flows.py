"""E2E tests for forgot-password and registration flows (#236, #237).

Uses a real in-memory SMTP server (aiosmtpd) to capture emails. Playwright fills the
forms, the SMTP server intercepts the email, we extract the token link, and Playwright
follows it.
"""

import re
import threading
import time
from email import message_from_bytes

import pymysql
import pytest
from argon2 import PasswordHasher
from playwright.sync_api import Page, expect

from dashboard.app import create_app
from dashboard.config import Config

EMAIL_PORT = 5097
SMTP_PORT = 10025
SMTP_MESSAGES: list[bytes] = []


# -- SMTP server that captures emails in memory ------------------------------


class _CapturingHandler:
    """Aiosmtpd handler that stores raw messages."""

    async def handle_DATA(self, server, session, envelope):
        """Store each incoming email."""
        SMTP_MESSAGES.append(envelope.content)
        return "250 OK"


def _run_smtp():
    """Run the SMTP server in its own event loop."""
    from aiosmtpd.controller import Controller

    controller = Controller(
        _CapturingHandler(),
        hostname="127.0.0.1",
        port=SMTP_PORT,
    )
    controller.start()
    # Keep the thread alive; controller runs in its own daemon thread.
    while True:
        time.sleep(60)


def _get_test_connection():
    """Create a connection to the test database."""
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_TEST_USER,
        password=Config.DB_TEST_PASSWORD,
        database=Config.DB_TEST_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def _extract_link(pattern: str) -> str:
    """Extract a URL matching pattern from the last captured email."""
    assert SMTP_MESSAGES, "No email captured"
    raw = SMTP_MESSAGES[-1]
    msg = message_from_bytes(raw)
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct in ("text/plain", "text/html"):
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")
    match = re.search(pattern, body)
    assert match, f"No link matching {pattern} in email body"
    return match.group(0)


# -- Fixtures ----------------------------------------------------------------


@pytest.fixture(scope="module")
def email_server(_setup_test_db):
    """Start a Flask server with auth + registration + SMTP pointed at aiosmtpd."""
    import dashboard.db as db_module

    db_module.get_connection = _get_test_connection

    # Start the in-memory SMTP server
    smtp_thread = threading.Thread(target=_run_smtp, daemon=True)
    smtp_thread.start()
    time.sleep(0.5)

    # Configure SMTP to point at the in-memory server
    prev_smtp = {
        "host": Config.SMTP_HOST,
        "port": Config.SMTP_PORT,
        "user": Config.SMTP_USER,
        "password": Config.SMTP_PASSWORD,
        "from": Config.SMTP_FROM,
        "tls": Config.SMTP_USE_TLS,
        "enabled": Config.SMTP_ENABLED,
        "domain": Config.REGISTER_ALLOWED_DOMAIN,
    }
    Config.SMTP_HOST = "127.0.0.1"
    Config.SMTP_PORT = SMTP_PORT
    Config.SMTP_USER = ""
    Config.SMTP_PASSWORD = ""
    Config.SMTP_FROM = "test@kenboard.test"
    Config.SMTP_USE_TLS = False
    Config.SMTP_ENABLED = True
    Config.REGISTER_ALLOWED_DOMAIN = "test.com"

    app = create_app()
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = False
    app.config["REGISTER_ALLOWED_DOMAIN"] = "test.com"
    app.config["RATELIMIT_ENABLED"] = False
    from dashboard.auth_user import limiter

    limiter.enabled = False

    server = threading.Thread(
        target=lambda: app.run(port=EMAIL_PORT, use_reloader=False),
        daemon=True,
    )
    server.start()
    time.sleep(1)

    yield f"http://localhost:{EMAIL_PORT}"

    # Restore config
    Config.SMTP_HOST = prev_smtp["host"]
    Config.SMTP_PORT = prev_smtp["port"]
    Config.SMTP_USER = prev_smtp["user"]
    Config.SMTP_PASSWORD = prev_smtp["password"]
    Config.SMTP_FROM = prev_smtp["from"]
    Config.SMTP_USE_TLS = prev_smtp["tls"]
    Config.SMTP_ENABLED = prev_smtp["enabled"]
    Config.REGISTER_ALLOWED_DOMAIN = prev_smtp["domain"]


@pytest.fixture(autouse=True)
def _clear_emails():
    """Clear captured emails before each test."""
    SMTP_MESSAGES.clear()


@pytest.fixture()
def seeded_user(clean_db):
    """Create a user with email for password reset tests."""
    from dashboard.db import load_queries

    h = PasswordHasher().hash("OldPassword123!")
    conn = _get_test_connection()
    try:
        load_queries().usr_create(
            conn,
            id="user-e2e-reset",
            name="e2euser",
            email="e2euser@test.com",
            color="#0969da",
            password_hash=h,
            is_admin=0,
        )
    finally:
        conn.close()


# -- E2E: Forgot password (#237) --------------------------------------------


class TestForgotPasswordE2E:
    """Full browser flow: forgot password → email → reset → login."""

    def test_full_reset_flow(self, page: Page, email_server, seeded_user):
        """Complete forgot-password flow via browser + real SMTP."""
        base = email_server

        # 1. Go to login, click "Mot de passe oublié"
        page.goto(f"{base}/login")
        page.click("a[href='/forgot-password']")
        expect(page.locator("h1")).to_contain_text("oubli")

        # 2. Submit email
        page.fill("input[name='email']", "e2euser@test.com")
        page.click("button[type='submit']")
        expect(page.locator(".login-success")).to_be_visible()

        # 3. Extract reset link from captured email
        time.sleep(0.5)
        reset_url = _extract_link(rf"{re.escape(base)}/reset-password/[A-Za-z0-9_-]+")

        # 4. Follow the reset link
        page.goto(reset_url)
        expect(page.locator("h1")).to_contain_text("Nouveau mot de passe")

        # 5. Submit new password
        page.fill("input[name='password']", "BrandNewE2E99!")
        page.fill("input[name='password_confirm']", "BrandNewE2E99!")
        page.click("button[type='submit']")

        # 6. Should be on login page with success message
        expect(page.locator(".login-success")).to_contain_text("modifi")

        # 7. Login with new password
        page.fill("input[name='name']", "e2euser")
        page.fill("input[name='password']", "BrandNewE2E99!")
        page.click("button[type='submit']")
        # Should redirect to index (successful login)
        page.wait_for_url(f"{base}/")


# -- E2E: Registration (#236) -----------------------------------------------


class TestRegistrationE2E:
    """Full browser flow: register → email → verify → login."""

    def test_full_registration_flow(self, page: Page, email_server, clean_db):
        """Complete registration flow via browser + real SMTP."""
        base = email_server

        # 1. Go to login, click "Créer un compte"
        page.goto(f"{base}/login")
        page.click("a[href='/register']")
        expect(page.locator("h1")).to_contain_text("compte")

        # 2. Fill registration form
        page.fill("input[name='email']", "newuser@test.com")
        page.fill("input[name='password']", "StrongE2EPass99!")
        page.fill("input[name='password_confirm']", "StrongE2EPass99!")
        page.click("button[type='submit']")
        expect(page.locator(".login-success")).to_be_visible()

        # 3. Extract verification link from captured email
        time.sleep(0.5)
        verify_url = _extract_link(rf"{re.escape(base)}/verify-email/[A-Za-z0-9_-]+")

        # 4. Follow the verification link
        page.goto(verify_url)

        # 5. Should be on login page with activation message
        expect(page.locator(".login-success")).to_contain_text("activ")

        # 6. Login with the new account
        page.fill("input[name='name']", "newuser@test.com")
        page.fill("input[name='password']", "StrongE2EPass99!")
        page.click("button[type='submit']")
        # Should redirect to index
        page.wait_for_url(f"{base}/")

    def test_wrong_domain_rejected(self, page: Page, email_server, clean_db):
        """Registration with wrong domain shows error in browser."""
        base = email_server
        page.goto(f"{base}/register")
        page.fill("input[name='email']", "user@wrong.com")
        page.fill("input[name='password']", "StrongPass123!")
        page.fill("input[name='password_confirm']", "StrongPass123!")
        page.click("button[type='submit']")
        expect(page.locator(".login-error")).to_contain_text("test.com")

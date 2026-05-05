"""E2E test fixtures — starts a live Flask server for Playwright."""

import threading
import time

import pymysql
import pymysql.cursors
import pytest
from playwright.sync_api import Page, expect

from dashboard.app import create_app
from dashboard.config import Config
from tests._schema import load_schema

SERVER_PORT = 5099

# All tests run against a local Flask thread; nothing here should ever
# legitimately take longer than a second. Default 30s Playwright timeouts
# only serve to make a real failure painfully slow to surface.
E2E_TIMEOUT_MS = 3000

expect.set_options(timeout=E2E_TIMEOUT_MS)


@pytest.fixture(autouse=True)
def _e2e_short_timeouts(page: Page) -> None:
    """Cap Playwright action and navigation timeouts at ``E2E_TIMEOUT_MS``."""
    page.set_default_timeout(E2E_TIMEOUT_MS)
    page.set_default_navigation_timeout(E2E_TIMEOUT_MS)


@pytest.fixture(scope="session")
def _setup_test_db():
    """Create test database tables."""
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_TEST_MIGRATE_USER,
        password=Config.DB_TEST_MIGRATE_PASSWORD,
        database=Config.DB_TEST_NAME,
        autocommit=True,
    )
    cur = conn.cursor()
    load_schema(cur)
    # Legacy back-fills for test DBs predating recent column additions.
    for col, tbl, defn in [
        ("email", "users", "VARCHAR(255) NULL AFTER name"),
        ("session_nonce", "users", "CHAR(32) NOT NULL DEFAULT '' AFTER is_admin"),
        ("user_id", "api_keys", "VARCHAR(36) NULL AFTER id"),
        ("key_type", "api_keys", "VARCHAR(20) NULL AFTER user_id"),
        ("last_used_ip", "api_keys", "VARCHAR(45) NULL AFTER last_used_at"),
        ("last_used_agent", "api_keys", "VARCHAR(200) NULL AFTER last_used_ip"),
        ("default_who", "projects", "VARCHAR(100) NOT NULL DEFAULT ''"),
    ]:
        cur.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            f"AND TABLE_NAME = '{tbl}' AND COLUMN_NAME = '{col}'"
        )
        if cur.fetchone()[0] == 0:
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {defn}")
    conn.close()


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


@pytest.fixture(scope="session")
def live_server(_setup_test_db):
    """Start a live Flask server in a background thread."""
    import dashboard.db as db_module

    db_module.get_connection = _get_test_connection

    app = create_app()
    app.config["TESTING"] = True
    # Bypass @login_required for the e2e suite by default. Tests that
    # cover the auth flow run their own dedicated server or login.
    app.config["LOGIN_DISABLED"] = True
    # Disable flask-limiter so the brute-force unit tests don't bleed
    # into e2e runs sharing the same module-level storage bucket.
    # flask-limiter 4.x caches ``enabled`` at init time — set it on the
    # instance directly.
    app.config["RATELIMIT_ENABLED"] = False
    from dashboard.auth_user import limiter

    limiter.enabled = False

    server = threading.Thread(
        target=lambda: app.run(port=SERVER_PORT, use_reloader=False),
        daemon=True,
    )
    server.start()
    time.sleep(1)
    return f"http://localhost:{SERVER_PORT}"


@pytest.fixture()
def clean_db():
    """Clean all data before each test."""
    conn = _get_test_connection()
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("DELETE FROM email_verification_tokens")
    cur.execute("DELETE FROM password_reset_tokens")
    cur.execute("DELETE FROM burndown_snapshots")
    cur.execute("DELETE FROM user_category_scopes")
    cur.execute("DELETE FROM api_key_projects")
    cur.execute("DELETE FROM api_keys")
    cur.execute("DELETE FROM tasks")
    cur.execute("DELETE FROM projects")
    cur.execute("DELETE FROM categories")
    cur.execute("DELETE FROM users")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.close()

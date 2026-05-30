"""Shared test fixtures."""

import pymysql
import pymysql.cursors
import pytest

from dashboard.app import create_app
from dashboard.config import Config
from dashboard.db import load_queries
from tests._schema import load_schema

# Provide a deterministic secret key for the test session so that
# init_login_manager doesn't fall back to its dev default. Set on the
# Config class itself before any app fixture runs.
Config.KENBOARD_SECRET_KEY = "test-secret-do-not-use-outside-tests"

# Set by _ensure_test_db(); False when MySQL is unreachable (e.g. Windows CI).
_mysql_available = False


def _ensure_test_db() -> None:
    """Create the test database and tables using the test admin user."""
    global _mysql_available
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_TEST_MIGRATE_USER,
        password=Config.DB_TEST_MIGRATE_PASSWORD,
        autocommit=True,
    )
    cur = conn.cursor()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{Config.DB_TEST_NAME}`"
        " CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.execute(f"USE `{Config.DB_TEST_NAME}`")
    load_schema(cur)
    # Idempotent back-fills for legacy test DBs carried over from earlier runs.
    # Each ALTER checks INFORMATION_SCHEMA before mutating; mirrors the rules
    # in CLAUDE.md for production migrations.
    _backfill_legacy_columns(cur)
    conn.close()
    _mysql_available = True


def _backfill_legacy_columns(cur: pymysql.cursors.Cursor) -> None:
    """Re-apply post-0008 schema additions on test DBs that predate them."""
    # users.session_nonce — migration 0008.
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'users' "
        "AND COLUMN_NAME = 'session_nonce'"
    )
    if cur.fetchone()[0] == 0:
        cur.execute(
            "ALTER TABLE users ADD COLUMN session_nonce CHAR(32) NOT NULL DEFAULT ''"
        )
    # users.email — migration 0012 (#126, OIDC).
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'users' "
        "AND COLUMN_NAME = 'email'"
    )
    if cur.fetchone()[0] == 0:
        cur.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL AFTER name")
        cur.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'users' "
            "AND INDEX_NAME = 'uq_users_email'"
        )
        if cur.fetchone()[0] == 0:
            cur.execute("ALTER TABLE users ADD UNIQUE INDEX uq_users_email (email)")
    # api_keys.user_id + fk_api_keys_user — migration 0010, two atomic steps.
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'api_keys' "
        "AND COLUMN_NAME = 'user_id'"
    )
    if cur.fetchone()[0] == 0:
        cur.execute("ALTER TABLE api_keys ADD COLUMN user_id VARCHAR(36) NULL AFTER id")
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'api_keys' "
        "AND CONSTRAINT_NAME = 'fk_api_keys_user' "
        "AND CONSTRAINT_TYPE = 'FOREIGN KEY'"
    )
    if cur.fetchone()[0] == 0:
        cur.execute(
            "ALTER TABLE api_keys ADD CONSTRAINT fk_api_keys_user "
            "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL"
        )
    # api_keys.key_type — migration 0014 (#159, onboarding tokens).
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'api_keys' "
        "AND COLUMN_NAME = 'key_type'"
    )
    if cur.fetchone()[0] == 0:
        cur.execute(
            "ALTER TABLE api_keys ADD COLUMN key_type VARCHAR(20) NULL AFTER user_id"
        )
    # api_keys.last_used_ip / last_used_agent — migration 0017 (#209, #210).
    for col, defn in [
        ("last_used_ip", "VARCHAR(45) NULL AFTER last_used_at"),
        ("last_used_agent", "VARCHAR(200) NULL AFTER last_used_ip"),
    ]:
        cur.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'api_keys' "
            f"AND COLUMN_NAME = '{col}'"
        )
        if cur.fetchone()[0] == 0:
            cur.execute(f"ALTER TABLE api_keys ADD COLUMN {col} {defn}")
    # projects.default_who — pre-0008 column added on a later run.
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'projects' "
        "AND COLUMN_NAME = 'default_who'"
    )
    if cur.fetchone()[0] == 0:
        cur.execute(
            "ALTER TABLE projects "
            "ADD COLUMN default_who VARCHAR(100) NOT NULL DEFAULT ''"
        )
    # tasks.attachement — migration 0022 (#541, paintbrush epic). MEDIUMTEXT
    # NULL = no attachment by default.
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'tasks' "
        "AND COLUMN_NAME = 'attachement'"
    )
    if cur.fetchone()[0] == 0:
        cur.execute("ALTER TABLE tasks ADD COLUMN attachement MEDIUMTEXT NULL")


def _get_test_connection() -> pymysql.Connection:
    """Create a connection to the test database using the test runtime user."""
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_TEST_USER,
        password=Config.DB_TEST_PASSWORD,
        database=Config.DB_TEST_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create the test database once per session.

    When MySQL is unreachable (e.g. Windows CI runners) the fixture silently succeeds so
    that pure-unit tests can still run.  Tests that actually need the database will be
    skipped via the ``db`` or ``app`` fixtures.
    """
    try:
        _ensure_test_db()
    except pymysql.err.OperationalError:
        pass


@pytest.fixture(scope="session", autouse=True)
def patch_db_connection(setup_test_db):
    """Force ``dashboard.db.get_connection`` to point at the test database for the
    entire test session, regardless of which fixtures are pulled in.

    Without this, helper modules that resolve their connection at call time (e.g.
    ``dashboard.auth``, ``dashboard.auth_user``) would hit the production database when
    a test only requests the ``db`` fixture.
    """
    if not _mysql_available:
        return
    import dashboard.db as db_module

    db_module.get_connection = _get_test_connection


@pytest.fixture(scope="session")
def app(setup_test_db):
    """Create Flask test app pointing to test database."""
    if not _mysql_available:
        pytest.skip("MySQL not available")
    import dashboard.db as db_module

    # Monkey-patch get_connection to use test DB
    db_module.get_connection = _get_test_connection

    app = create_app()
    app.config["TESTING"] = True
    # Bypass @login_required AND the API key middleware for unit tests by
    # default. Tests that exercise auth (login flow, middleware enforcement)
    # flip this back to False.
    app.config["LOGIN_DISABLED"] = True
    # Disable flask-limiter by default. The rate-limit tests re-enable it
    # explicitly via a fixture and reset state between subtests.
    # flask-limiter 4.x caches ``enabled`` as an instance attribute during
    # ``init_app``, so we must also set it on the limiter object directly.
    app.config["RATELIMIT_ENABLED"] = False
    from dashboard.auth_user import limiter

    limiter.enabled = False
    return app


@pytest.fixture(scope="session")
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture(scope="session")
def queries():
    """Load aiosql queries."""
    return load_queries()


@pytest.fixture()
def db():
    """Create a test database connection, clean tables before and after."""
    if not _mysql_available:
        pytest.skip("MySQL not available")
    conn = _get_test_connection()
    # Cleanup before test
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("DELETE FROM activities")
    cur.execute("DELETE FROM task_wiki_classifications")
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
    yield conn
    # Cleanup after test
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("DELETE FROM activities")
    cur.execute("DELETE FROM task_wiki_classifications")
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


@pytest.fixture()
def seed_category(db, queries):
    """Insert a test category and return it."""
    queries.cat_create(
        db, id="test-cat", name="Test", color="var(--accent)", position=0
    )
    return queries.cat_get_by_id(db, id="test-cat")


@pytest.fixture()
def seed_project(db, queries, seed_category):
    """Insert a test project and return it."""
    queries.proj_create(
        db,
        id="test-proj",
        cat_id="test-cat",
        name="Test Project",
        acronym="TEST",
        status="active",
        position=0,
        default_who="",
    )
    return queries.proj_get_by_id(db, id="test-proj")


@pytest.fixture()
def seed_task(db, queries, seed_project):
    """Insert a test task and return it."""
    queries.task_create(
        db,
        project_id="test-proj",
        title="Test Task",
        description="A test task",
        status="todo",
        who="Q",
        due_date=None,
        attachement=None,
        position=0,
    )
    cur = db.cursor()
    cur.execute("SELECT LAST_INSERT_ID()")
    task_id = cur.fetchone()["LAST_INSERT_ID()"]
    return queries.task_get_by_id(db, id=task_id)

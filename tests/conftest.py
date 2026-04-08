"""Shared test fixtures."""

import pymysql
import pymysql.cursors
import pytest

from dashboard.app import create_app
from dashboard.config import Config
from dashboard.db import load_queries

# Provide a deterministic secret key for the test session so that
# init_login_manager doesn't fall back to its dev default. Set on the
# Config class itself before any app fixture runs.
Config.KENBOARD_SECRET_KEY = "test-secret-do-not-use-outside-tests"


def _ensure_test_db() -> None:
    """Create the test database and tables using the test admin user."""
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            name VARCHAR(250) NOT NULL,
            color VARCHAR(50) NOT NULL,
            position INT NOT NULL DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            cat_id VARCHAR(36) NOT NULL,
            name VARCHAR(250) NOT NULL,
            acronym VARCHAR(4) NOT NULL,
            status ENUM('active', 'archived') NOT NULL DEFAULT 'active',
            position INT NOT NULL DEFAULT 0,
            default_who VARCHAR(100) NOT NULL DEFAULT '',
            FOREIGN KEY (cat_id) REFERENCES categories(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    # In case the table was created by an earlier session without the
    # default_who column, add it. MySQL 8 doesn't support ADD COLUMN IF
    # NOT EXISTS — check INFORMATION_SCHEMA first.
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            project_id VARCHAR(36) NOT NULL,
            title VARCHAR(250) NOT NULL,
            description TEXT NOT NULL DEFAULT (''),
            status ENUM('todo', 'doing', 'review', 'done') NOT NULL DEFAULT 'todo',
            who VARCHAR(100) NOT NULL DEFAULT '',
            due_date DATE NULL,
            position INT NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            INDEX idx_project_status (project_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            color VARCHAR(50) NOT NULL,
            password_hash VARCHAR(255) NOT NULL DEFAULT '',
            is_admin TINYINT(1) NOT NULL DEFAULT 0,
            session_nonce CHAR(32) NOT NULL DEFAULT '',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    # users.session_nonce was added in migration 0008. Existing test DBs
    # carried over from a previous run still have the old schema; back-fill.
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'users' "
        "AND COLUMN_NAME = 'session_nonce'"
    )
    if cur.fetchone()[0] == 0:
        cur.execute(
            "ALTER TABLE users " "ADD COLUMN session_nonce CHAR(32) NOT NULL DEFAULT ''"
        )
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            user_id VARCHAR(36) NULL,
            key_hash CHAR(64) NOT NULL UNIQUE,
            label VARCHAR(100) NOT NULL,
            expires_at DATETIME NULL,
            last_used_at DATETIME NULL,
            revoked_at DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_key_hash (key_hash),
            CONSTRAINT fk_api_keys_user
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    # api_keys.user_id was added in migration 0010. Back-fill on legacy
    # carried-over schemas, in two atomic steps so a partial state can
    # converge — mirrors the idempotent pattern in the migration itself.
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_key_projects (
            api_key_id VARCHAR(36) NOT NULL,
            project_id VARCHAR(36) NOT NULL,
            scope ENUM('read','write','admin') NOT NULL,
            PRIMARY KEY (api_key_id, project_id),
            FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.close()


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
    """Create the test database once per session."""
    _ensure_test_db()


@pytest.fixture(scope="session", autouse=True)
def patch_db_connection(setup_test_db):
    """Force ``dashboard.db.get_connection`` to point at the test database for the
    entire test session, regardless of which fixtures are pulled in.

    Without this, helper modules that resolve their connection at
    call time (e.g. ``dashboard.auth``, ``dashboard.auth_user``) would
    hit the production database when a test only requests the ``db``
    fixture.
    """
    import dashboard.db as db_module

    db_module.get_connection = _get_test_connection


@pytest.fixture(scope="session")
def app(setup_test_db):
    """Create Flask test app pointing to test database."""
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
    app.config["RATELIMIT_ENABLED"] = False
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
    conn = _get_test_connection()
    # Cleanup before test
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
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
        position=0,
    )
    cur = db.cursor()
    cur.execute("SELECT LAST_INSERT_ID()")
    task_id = cur.fetchone()["LAST_INSERT_ID()"]
    return queries.task_get_by_id(db, id=task_id)

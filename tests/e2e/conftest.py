"""E2E test fixtures — starts a live Flask server for Playwright."""

import threading
import time

import pymysql
import pymysql.cursors
import pytest

from dashboard.app import create_app
from dashboard.config import Config

SERVER_PORT = 5099


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
            FOREIGN KEY (cat_id) REFERENCES categories(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
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
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            key_hash CHAR(64) NOT NULL UNIQUE,
            label VARCHAR(100) NOT NULL,
            expires_at DATETIME NULL,
            last_used_at DATETIME NULL,
            revoked_at DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_key_hash (key_hash)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
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
    cur.execute("DELETE FROM api_key_projects")
    cur.execute("DELETE FROM api_keys")
    cur.execute("DELETE FROM tasks")
    cur.execute("DELETE FROM projects")
    cur.execute("DELETE FROM categories")
    cur.execute("DELETE FROM users")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.close()

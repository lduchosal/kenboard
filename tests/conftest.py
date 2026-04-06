"""Shared test fixtures."""

import pymysql
import pymysql.cursors
import pytest

from dashboard.app import create_app
from dashboard.config import Config
from dashboard.db import load_queries


@pytest.fixture(scope="session")
def app():
    """Create Flask test app."""
    app = create_app()
    app.config["TESTING"] = True
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
    """Create a database connection, clean tables after each test."""
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    # Cleanup before test
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("DELETE FROM tasks")
    cur.execute("DELETE FROM projects")
    cur.execute("DELETE FROM categories")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    yield conn
    # Cleanup after test
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur.execute("DELETE FROM tasks")
    cur.execute("DELETE FROM projects")
    cur.execute("DELETE FROM categories")
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

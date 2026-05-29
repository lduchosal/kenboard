"""Activity log unit tests (#261).

Covers:
- ``log_activity`` writes one row per call with the expected fields.
- ``activity_daily_total`` aggregates over the requested window.
- Failures inside the aiosql call are swallowed (best-effort log).
- Each task route mutation appends one activity row with the right action.
"""

from __future__ import annotations

import json

import pytest

import dashboard.db as db_module
from dashboard.activity import (
    ACTION_CREATE,
    ACTION_DELETE,
    ACTION_MOVE,
    ACTION_SAVE,
    log_activity,
)


@pytest.fixture()
def project(db):
    """Insert a category + project so activity rows have a valid FK target."""
    cur = db.cursor()
    cur.execute(
        "INSERT INTO categories (id, name, color, position) VALUES (%s, %s, %s, %s)",
        ("cat-act", "Cat", "var(--accent)", 0),
    )
    cur.execute(
        "INSERT INTO projects (id, cat_id, name, acronym, status, position) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        ("proj-act", "cat-act", "Proj", "PROJ", "active", 0),
    )
    return "proj-act"


def test_log_activity_writes_row(db, project):
    """log_activity inserts the expected fields."""
    queries = db_module.load_queries()
    log_activity(
        db,
        queries,
        project_id=project,
        action=ACTION_CREATE,
        target_id=42,
        details={"status": "todo"},
    )
    cur = db.cursor()
    cur.execute(
        "SELECT project_id, user_name, action, target_type, target_id, details "
        "FROM activities WHERE project_id = %s",
        (project,),
    )
    rows = cur.fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row["project_id"] == project
    assert row["action"] == "create"
    assert row["target_type"] == "task"
    assert row["target_id"] == "42"
    if isinstance(row["details"], str):
        assert json.loads(row["details"]) == {"status": "todo"}
    else:
        assert row["details"] == {"status": "todo"}


def test_log_activity_swallows_failures(db, project):
    """A bogus action value (not in the ENUM) must not raise."""
    queries = db_module.load_queries()
    log_activity(
        db,
        queries,
        project_id=project,
        action="not-an-action",
        target_id=1,
    )
    cur = db.cursor()
    cur.execute(
        "SELECT COUNT(*) AS c FROM activities WHERE project_id = %s", (project,)
    )
    assert cur.fetchone()["c"] == 0


def test_activity_daily_total_aggregates(db, project):
    """activity_daily_total returns one row per day with non-zero activity."""
    queries = db_module.load_queries()
    for action in (ACTION_CREATE, ACTION_SAVE, ACTION_MOVE, ACTION_DELETE):
        log_activity(db, queries, project_id=project, action=action, target_id=1)
    rows = list(queries.activity_daily_total(db, days=7))
    assert len(rows) == 1
    assert rows[0]["count"] == 4


def test_activity_daily_by_user_groups_by_day_and_principal(db, project):
    """activity_daily_by_user groups counts per day + raw principal."""
    from datetime import date, timedelta

    queries = db_module.load_queries()
    cur = db.cursor()
    for uname, n in (("Luc", 2), ("key:k1:user:u1", 1)):
        for _ in range(n):
            cur.execute(
                "INSERT INTO activities (project_id, user_name, action, target_id) "
                "VALUES (%s, %s, 'create', '1')",
                (project, uname),
            )
    since = (date.today() - timedelta(days=6)).isoformat()
    rows = list(queries.activity_daily_by_user(db, since=since))
    counts = {r["user_name"]: r["count"] for r in rows}
    assert counts["Luc"] == 2
    assert counts["key:k1:user:u1"] == 1
    # all inserted now → a single day bucket
    assert len({str(r["day"]) for r in rows}) == 1


def test_create_task_logs_activity(client, db, project):
    """POST /api/v1/tasks appends a 'create' activity row."""
    r = client.post(
        "/api/v1/tasks",
        json={"project_id": project, "title": "T", "status": "todo"},
    )
    assert r.status_code == 201
    cur = db.cursor()
    cur.execute(
        "SELECT action FROM activities WHERE project_id = %s ORDER BY id",
        (project,),
    )
    actions = [row["action"] for row in cur.fetchall()]
    assert actions == ["create"]


def test_move_task_logs_move(client, db, project):
    """A PATCH that changes status logs as 'move' (not 'save')."""
    r = client.post(
        "/api/v1/tasks", json={"project_id": project, "title": "T", "status": "todo"}
    )
    task_id = r.get_json()["id"]
    r = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "doing"})
    assert r.status_code == 200
    cur = db.cursor()
    cur.execute(
        "SELECT action FROM activities WHERE target_id = %s ORDER BY id",
        (str(task_id),),
    )
    actions = [row["action"] for row in cur.fetchall()]
    assert actions == ["create", "move"]


def test_field_only_update_logs_save(client, db, project):
    """A PATCH that only changes title/desc/who logs as 'save'."""
    r = client.post(
        "/api/v1/tasks", json={"project_id": project, "title": "T", "status": "todo"}
    )
    task_id = r.get_json()["id"]
    r = client.patch(f"/api/v1/tasks/{task_id}", json={"title": "T2"})
    assert r.status_code == 200
    cur = db.cursor()
    cur.execute(
        "SELECT action FROM activities WHERE target_id = %s ORDER BY id",
        (str(task_id),),
    )
    actions = [row["action"] for row in cur.fetchall()]
    assert actions == ["create", "save"]


def test_delete_task_logs_delete(client, db, project):
    """DELETE /api/v1/tasks/<id> appends a 'delete' activity row."""
    r = client.post(
        "/api/v1/tasks", json={"project_id": project, "title": "T", "status": "todo"}
    )
    task_id = r.get_json()["id"]
    r = client.delete(f"/api/v1/tasks/{task_id}")
    assert r.status_code == 204
    cur = db.cursor()
    cur.execute(
        "SELECT action FROM activities WHERE target_id = %s ORDER BY id",
        (str(task_id),),
    )
    actions = [row["action"] for row in cur.fetchall()]
    assert actions == ["create", "delete"]

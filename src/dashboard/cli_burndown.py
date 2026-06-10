"""``kenboard snapshot`` / ``backfill`` — burndown history maintenance (#206).

Split out of ``cli.py`` (ken #808): the daily task-count snapshot and the historical
backfill computed from task created/updated timestamps.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import click
from pymysql import Connection

from dashboard.cli import cli


@cli.command()
def snapshot() -> None:
    """Record today's task counts per project for the burndown chart (#206).

    Counts the tasks in each status (todo/doing/review/done) per project
    and upserts one row per project into ``burndown_snapshots`` at today's
    date. Designed to run as a daily cron job::

        0 2 * * * kenboard snapshot

    Idempotent: running multiple times on the same day simply overwrites
    the counters with the latest values.
    """
    import dashboard.db as db_module

    conn = db_module.get_connection()
    queries = db_module.load_queries()
    try:
        projects = list(queries.proj_get_all(conn))
        recorded = 0
        for proj in projects:
            rows = list(
                queries.burndown_task_counts_by_project(conn, project_id=proj["id"])
            )
            counts = {r["status"]: r["cnt"] for r in rows}
            queries.burndown_record_snapshot(
                conn,
                project_id=proj["id"],
                todo=counts.get("todo", 0),
                doing=counts.get("doing", 0),
                review=counts.get("review", 0),
                done=counts.get("done", 0),
            )
            recorded += 1
        click.echo(f"Recorded snapshots for {recorded} project(s).")
    finally:
        conn.close()


@cli.command()
@click.option(
    "--days",
    default=60,
    type=int,
    help="How many days of history to reconstruct (default 60).",
)
def backfill(days: int) -> None:
    """Reconstruct burndown snapshots from task timestamps (#206).

    Approximates historical task counts by walking each day from
    ``--days`` ago to today and inferring status from
    ``tasks.created_at`` / ``tasks.updated_at``:

    - A task with ``status='done'`` was "open" from ``created_at`` to
      ``updated_at`` (exclusive) and "done" from ``updated_at`` onwards.
    - A task with any other status is counted as "open" (todo) from
      ``created_at`` to today.

    The intermediate statuses (doing, review) cannot be reconstructed,
    so all non-done tasks are counted as "todo" in the backfill. The
    burndown curve (remaining = todo + doing + review) is still accurate
    because all three statuses are summed together.

    Idempotent: existing snapshots are overwritten via upsert.
    """
    from datetime import timedelta

    import dashboard.db as db_module

    conn = db_module.get_connection()
    queries = db_module.load_queries()
    try:
        projects = list(queries.proj_get_all(conn))
        # Local date wanted: burndown snapshots are keyed on the operator's
        # calendar day, matching the DATE() grouping done DB-side (#785).
        today = date.today()  # noqa: DTZ011
        start = today - timedelta(days=days)
        total = 0
        for proj in projects:
            tasks = list(queries.task_get_by_project(conn, project_id=proj["id"]))
            if not tasks:
                continue
            total += _backfill_project(conn, proj["id"], tasks, start, days)
        click.echo(f"Backfilled {total} snapshot(s) across {len(projects)} project(s).")
    finally:
        conn.close()


def _to_date(val: datetime | date) -> date:
    """Convert a datetime to a date, or return as-is if already a date."""
    return val.date() if isinstance(val, datetime) else val


def _count_task_status_at(task: dict[str, Any], day: date) -> tuple[int, int]:
    """Return (todo, done) contribution of a single task for a given day."""
    t_created = _to_date(task["created_at"])
    if t_created > day:
        return 0, 0
    t_updated = _to_date(task["updated_at"])
    if task["status"] == "done" and t_updated <= day:
        return 0, 1
    return 1, 0


def _backfill_project(
    conn: Connection, proj_id: str, tasks: list[dict[str, Any]], start: date, days: int
) -> int:
    """Backfill snapshots for a single project, return count of rows upserted."""
    from datetime import timedelta

    count = 0
    for day_offset in range(days + 1):
        day = start + timedelta(days=day_offset)
        todo = 0
        done = 0
        for t in tasks:
            t_todo, t_done = _count_task_status_at(t, day)
            todo += t_todo
            done += t_done
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO burndown_snapshots"
            " (snapshot_date, project_id, todo, doing, review, done)"
            " VALUES (%s, %s, %s, 0, 0, %s)"
            " ON DUPLICATE KEY UPDATE"
            " todo=VALUES(todo), doing=0, review=0, done=VALUES(done)",
            (day.isoformat(), proj_id, todo, done),
        )
        count += 1
    return count

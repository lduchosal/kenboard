"""CLI entry point."""

import sys
from pathlib import Path
from typing import Any

import click

# Force UTF-8 on Windows so kenboard CLI output (migration logs, error
# messages) does not crash on non-ASCII characters (#148).
if sys.platform == "win32":  # pragma: no cover
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name)
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")


@click.group()
@click.version_option(package_name="kenboard")  # type: ignore[call-arg]
def cli() -> None:
    """Dashboard management commands."""


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to.")
@click.option("--port", default=5000, help="Port to bind to.")
@click.option("--debug", is_flag=True, help="Enable debug mode.")
def serve(host: str, port: int, debug: bool) -> None:
    """Start the Flask development server (local dev only).

    Refuses to run without ``--debug`` to make it impossible to
    accidentally serve production traffic from Werkzeug — that's the
    server that prints "WARNING: This is a development server. Do not
    use it in a production deployment." For prod, use a real WSGI
    server (gunicorn, see INSTALL.md).
    """
    if not debug:
        click.echo(
            "Refusal: `kenboard serve` runs the Werkzeug development "
            "server, which is single-threaded, unhardened, and not "
            "intended for production traffic.\n"
            "  - For local development:  kenboard serve --debug\n"
            "  - For production:         "
            'gunicorn "dashboard.app:create_app()" '
            "--bind 0.0.0.0:8080 --workers 4\n"
            "See INSTALL.md section 7 for the full production setup.",
            err=True,
        )
        sys.exit(2)
    if host != "127.0.0.1":
        click.echo(
            "Refusal: --debug exposes the Werkzeug debug console (RCE risk) "
            "and must stay local. Run without --debug or with --host 127.0.0.1.",
            err=True,
        )
        sys.exit(2)

    from dashboard.app import create_app

    app = create_app()
    app.run(host=host, port=port, debug=debug)


@cli.command()
@click.option(
    "--bind",
    default="0.0.0.0:8080",
    help="Address to bind to (host:port). Default 0.0.0.0:8080.",
)
@click.option(
    "--workers",
    default=4,
    type=int,
    help="Number of gunicorn worker processes. Default 4.",
)
def prod(bind: str, workers: int) -> None:
    """Start kenboard in production mode via gunicorn.

    Wraps gunicorn so the operator does not need to remember the WSGI
    target string. Requires the optional ``prod`` extra:
    ``pip install "kenboard[prod]"``.
    """
    try:
        from gunicorn.app.wsgiapp import WSGIApplication
    except ImportError:
        click.echo(
            "Refusal: gunicorn is not installed. Install the prod extra:\n"
            '    pip install "kenboard[prod]"\n'
            "Then re-run `kenboard prod`.",
            err=True,
        )
        sys.exit(2)

    # gunicorn's WSGIApplication reads from sys.argv. Rebuild it as if
    # the operator had typed `gunicorn --bind … --workers … dashboard.app:create_app()`
    # so all the standard gunicorn flags remain reachable via env vars
    # / config files for advanced users.
    sys.argv = [
        "gunicorn",
        "--bind",
        bind,
        "--workers",
        str(workers),
        "dashboard.app:create_app()",
    ]
    WSGIApplication().run()


@cli.command()
def migrate() -> None:
    """Run database migrations on the production database."""
    import subprocess

    from dashboard.config import Config

    db_url = (
        f"mysql://{Config.DB_MIGRATE_USER}:{Config.DB_MIGRATE_PASSWORD}"
        f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    )
    subprocess.run(
        [
            "yoyo",
            "apply",
            "--batch",
            "--database",
            db_url,
            str(Path(__file__).parent / "migrations"),
        ],
        check=True,
    )


@cli.command()
@click.argument("name")
def set_password(name: str) -> None:
    """Set or reset a user's password (prompts twice for confirmation)."""
    import getpass

    from argon2 import PasswordHasher

    import dashboard.db as db_module

    pw = getpass.getpass(f"New password for {name}: ")
    pw2 = getpass.getpass("Confirm: ")
    if pw != pw2:
        click.echo("Passwords do not match", err=True)
        sys.exit(1)
    # #198: enforce the same zxcvbn-based strength policy the API uses.
    from dashboard.password_strength import validate_password_strength

    try:
        validate_password_strength(pw)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    h = PasswordHasher().hash(pw)
    conn = db_module.get_connection()
    queries = db_module.load_queries()
    try:
        row = queries.usr_get_by_name(conn, name=name)
        if not row:
            click.echo(f"User {name} not found", err=True)
            sys.exit(1)
        queries.usr_update_password(conn, id=row["id"], password_hash=h)
        click.echo(f"Password updated for {name}")
    finally:
        conn.close()


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
    from datetime import date, timedelta

    import dashboard.db as db_module

    conn = db_module.get_connection()
    queries = db_module.load_queries()
    try:
        projects = list(queries.proj_get_all(conn))
        today = date.today()
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


def _to_date(val: Any) -> Any:
    """Convert a datetime to a date, or return as-is if already a date."""
    return val.date() if hasattr(val, "date") else val


def _count_task_status_at(task: dict[str, Any], day: Any) -> tuple[int, int]:
    """Return (todo, done) contribution of a single task for a given day."""
    t_created = _to_date(task["created_at"])
    if t_created > day:
        return 0, 0
    t_updated = _to_date(task["updated_at"])
    if task["status"] == "done" and t_updated <= day:
        return 0, 1
    return 1, 0


def _backfill_project(
    conn: Any, proj_id: str, tasks: list[dict[str, Any]], start: Any, days: int
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


@cli.command()
@click.option(
    "--yes",
    is_flag=True,
    help="Skip interactive confirmation (for scripted use).",
)
def grant_legacy_read(yes: bool) -> None:
    """Grant ``read`` on every existing category to every non-admin user (#197).

    Opt-in recovery path for deployments migrating from a pre-permissions
    version: the default-closed policy locks everyone out until an admin
    assigns scopes. Running this once restores the pre-migration "everyone
    sees everything" behaviour, only in read mode. Admins already bypass
    scopes via ``users.is_admin``; this command only touches non-admins.

    Idempotent: existing entries are left untouched (``INSERT IGNORE``).
    """
    import dashboard.db as db_module

    if not yes:
        click.confirm(
            "Grant 'read' on every category to every non-admin user?",
            abort=True,
        )
    conn = db_module.get_connection()
    queries = db_module.load_queries()
    try:
        queries.usr_grant_all_categories_read(conn)
        click.echo("Done. Existing entries were left untouched.")
    finally:
        conn.close()


@cli.command()
def migrate_test() -> None:
    """Run database migrations on the test database."""
    import subprocess

    from dashboard.config import Config

    db_url = (
        f"mysql://{Config.DB_TEST_MIGRATE_USER}:{Config.DB_TEST_MIGRATE_PASSWORD}"
        f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_TEST_NAME}"
    )
    subprocess.run(
        [
            "yoyo",
            "apply",
            "--batch",
            "--database",
            db_url,
            str(Path(__file__).parent / "migrations"),
        ],
        check=True,
    )

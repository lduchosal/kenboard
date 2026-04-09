"""CLI entry point."""

import sys
from pathlib import Path

import click


@click.group()
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
    if len(pw) < 8:
        click.echo("Password must be at least 8 characters", err=True)
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

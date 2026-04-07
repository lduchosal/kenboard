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
    """Start the Flask development server."""
    from dashboard.app import create_app

    app = create_app()
    app.run(host=host, port=port, debug=debug)


@cli.command()
def build() -> None:
    """Generate static HTML pages from data.json."""
    import subprocess
    import sys

    subprocess.run([sys.executable, "build.py"], check=True)


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

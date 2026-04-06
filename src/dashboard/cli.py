"""CLI entry point."""

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
    """Run database migrations."""
    import subprocess

    from dashboard.config import Config

    db_url = f"mysql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    subprocess.run(
        ["yoyo", "apply", "--batch", "--database", db_url, "migrations/"], check=True
    )

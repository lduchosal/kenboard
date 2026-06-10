"""Root Click group and lifecycle commands of the ``ken`` CLI.

Holds the ``cli`` group every command registers on, plus the commands that manage the
CLI itself: ``init`` (bootstrap ken.ini / .ken), ``self-update`` (pip upgrade) and
``help`` (agent guide).
"""

from __future__ import annotations

import configparser
import sys
from importlib import resources
from pathlib import Path

import click

from dashboard.ken.config import (
    KEN_FILE,
    KEN_INI_FILE,
    KEN_INI_SECTION,
    KenConfig,
    _add_to_gitignore,
    _load_config,
)
from dashboard.ken.http import _request


@click.group()
@click.option("--project", help="Override project_id (UUID).")
@click.option("--base-url", help="Override the kenboard base URL.")
@click.option("--token", help="Override the API bearer token.")
@click.option("--config", "config_file", help="Path to a .ken config file.")
@click.pass_context
def cli(
    ctx: click.Context,
    project: str | None,
    base_url: str | None,
    token: str | None,
    config_file: str | None,
) -> None:
    """Ken — task CLI for the kenboard board."""
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = _load_config(project, base_url, token, config_file)


@cli.command()
@click.argument("project_uuid", required=False)
@click.option("--force", is_flag=True, help="Overwrite an existing ken.ini and/or .ken")
@click.pass_context
def init(ctx: click.Context, project_uuid: str | None, force: bool) -> None:
    """Initialize ``ken.ini`` (and ``.ken`` if a token is set) in the cwd.

    ``ken.ini`` is the versioned, shared config — it holds ``project_id``, ``base_url``
    and ``description``. It is **not** added to ``.gitignore`` so the whole team picks
    up the same defaults.

    ``.ken`` is the local secrets file — it holds ``api_token`` only (when one is
    resolved from flags/env), is created with mode ``0600`` and added to the repository
    ``.gitignore``. Skipped when no token is available.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    cwd = Path.cwd()
    ini_target = cwd / KEN_INI_FILE
    ken_target = cwd / KEN_FILE
    if ini_target.exists() and not force:
        click.echo(
            f"Error: {KEN_INI_FILE} already exists. Use --force to overwrite.",
            err=True,
        )
        sys.exit(1)
    if cfg.api_token and ken_target.exists() and not force:
        click.echo(
            f"Error: {KEN_FILE} already exists. Use --force to overwrite.",
            err=True,
        )
        sys.exit(1)

    projects_data = _request(cfg, "GET", "/api/v1/projects")
    if not projects_data:
        click.echo(
            "Error: no projects found on the kenboard. "
            "Create one via the web UI first.",
            err=True,
        )
        sys.exit(1)

    if project_uuid is None:
        click.echo("Available projects:")
        for i, p in enumerate(projects_data, 1):
            click.echo(f"  {i}. {p['name']} ({p.get('acronym', '')}) — {p['id']}")
        choice = click.prompt(
            "Select a project (number)",
            type=click.IntRange(1, len(projects_data)),
        )
        project_uuid = projects_data[choice - 1]["id"]
        chosen_name = projects_data[choice - 1]["name"]
    else:
        match = next((p for p in projects_data if p["id"] == project_uuid), None)
        if match is None:
            click.echo(
                f"Error: project {project_uuid} not found on {cfg.base_url}.",
                err=True,
            )
            sys.exit(1)
        chosen_name = match["name"]

    ini_parser = configparser.ConfigParser()
    ini_parser[KEN_INI_SECTION] = {
        "project_id": project_uuid,
        "base_url": cfg.base_url,
        "description": chosen_name,
    }
    with ini_target.open("w", encoding="utf-8") as fh:
        ini_parser.write(fh)
    click.echo(f"Wrote {KEN_INI_FILE} (project: {chosen_name})")

    if cfg.api_token:
        ken_target.write_text(f"api_token={cfg.api_token}\n", encoding="utf-8")
        ken_target.chmod(0o600)
        click.echo(f"Wrote {KEN_FILE} (api_token)")
        _add_to_gitignore(cwd)
    else:
        click.echo(
            f"Note: no api_token resolved — skipped {KEN_FILE}. "
            f"Set KEN_API_TOKEN or pass --token, then re-run `ken init --force`.",
            err=True,
        )


@cli.command(name="self-update")
def self_update() -> None:
    """Upgrade kenboard to the latest version from PyPI.

    Runs ``pip install --upgrade kenboard`` using the same Python that is running this
    CLI. The new version is available on the next ``ken`` invocation.
    """
    import subprocess

    from dashboard import __version__

    click.echo(f"Current version: {__version__}")
    click.echo("Upgrading kenboard from PyPI...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "kenboard"],
        check=False,
    )
    if result.returncode != 0:
        click.echo("Error: upgrade failed", err=True)
        sys.exit(1)
    click.echo("Done. Run `ken --help` to verify the new version.")


@cli.command(name="help")
def help_cmd() -> None:
    """Print the agent guide (kenboard best practices for LLM agents).

    Loads ``agent_guide.md`` from the installed package via ``importlib.resources`` so
    the doc travels with the wheel and stays in sync with the CLI version. Pair with
    ``ken --help`` for the auto-generated command reference.
    """
    text = (
        resources.files("dashboard")
        .joinpath("agent_guide.md")
        .read_text(encoding="utf-8")
    )
    click.echo(text)

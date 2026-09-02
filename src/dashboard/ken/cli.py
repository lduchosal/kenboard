"""Root Click group and lifecycle commands of the ``ken`` CLI.

Holds the ``cli`` group every command registers on, plus the commands that manage the
CLI itself: ``init`` (bootstrap ken.ini / .ken, from the URL parsed by ``onboard_url``
and written by ``init_files``), ``self-update`` (pip upgrade) and ``help`` (agent
guide).
"""

from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

import click

from dashboard.ken.config import KenConfig, _load_config
from dashboard.ken.http import _request, _try_request
from dashboard.ken.init_files import _refuse_existing_files, _write_config_files
from dashboard.ken.onboard_url import (
    OnboardingLink,
    parse_onboarding_url,
    read_url_argument,
)


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
    """Ken — task CLI for the kenboard board.

    Config is resolved flag > env (KEN_*) > .ken (local secrets, gitignored) > ken.ini
    (shared, versioned) > built-in defaults. Provide no base_url and ken falls back to a
    default that points at localhost:9090 — nothing reaches your board, and the failure
    then looks like the board misbehaving (#1021).

    Bootstrap a repo with `ken init <onboarding-url>`: paste the link behind the board's
    "copy onboard link" button and ken writes ken.ini + .ken for you.
    """
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = _load_config(project, base_url, token, config_file)


def _config_from_link(ctx: click.Context, link: OnboardingLink) -> KenConfig:
    """Build the config ``init`` runs on: the URL alone, plus explicit global flags.

    The group's resolved ``ctx.obj["cfg"]`` is deliberately ignored here — on the fresh
    checkout ``init`` exists for, it *is* the localhost fallback. ``--base-url`` and
    ``--token`` still win when the operator passes them (an API host that differs from
    the public one, a link handed over without its token).
    """
    overrides = ctx.parent.params if ctx.parent is not None else {}
    return KenConfig(
        project_id=link.project_id,
        base_url=(overrides.get("base_url") or link.base_url).rstrip("/"),
        api_token=overrides.get("token") or link.token,
        ken_file=None,
    )


def _verify_project(cfg: KenConfig, project_id: str) -> str:
    """Prove the link works, and read the project's name when the board serves it.

    ``GET /api/v1/projects/<id>`` answers both questions at once: it demands the very
    read scope every later command needs, and it carries the name that becomes
    ``description``. It is a recent route (#1089), so a CLI talking to an older board
    falls back to that project's task list — same authorisation, no label. The
    cross-project listing is not an option here: a token minted by an onboarding link
    is scoped to one project and the board answers 403 on it.
    """
    project = _try_request(cfg, "GET", f"/api/v1/projects/{project_id}")
    if isinstance(project, dict) and project.get("name"):
        return str(project["name"])
    _request(
        cfg,
        "GET",
        f"/api/v1/tasks?project={project_id}",
        hints={
            401: "\nHint: the token in the onboarding link is missing, invalid or "
            "expired — ask for a fresh link.",
            403: f"\nHint: that token carries no access to project {project_id} on "
            "this board — ask for a fresh onboarding link.",
        },
    )
    return ""


@cli.command()
@click.argument("onboarding_url")
@click.option("--force", is_flag=True, help="Overwrite an existing ken.ini and/or .ken")
@click.pass_context
def init(ctx: click.Context, onboarding_url: str, *, force: bool) -> None:
    r"""Bootstrap this repo's config from the board's onboarding URL.

    ONBOARDING_URL is the link behind the board's "copy onboard link" button:

    \b
        https://board.example.com/onboard/cat/<cat-id>/project/<project-id>?token=<token>

    It carries everything ken needs — base_url, project_id and, when the link
    includes ?token=, the API token — so init needs no prior configuration. That is
    the point: every other command reads .ken / ken.ini, the very files a fresh
    checkout does not have yet, which is why a config-driven init would aim at
    http://localhost:9090 instead of your board.

    Pass `-` to read the URL from stdin and keep the token out of the shell history:

    \b
        pbpaste | ken init -

    Two files are written in the current directory:

    \b
      ken.ini  shared, versioned — project_id, base_url, description and the
               wiki/sync paths. Commit it; it never holds the token.
      .ken     local secrets — api_token only, mode 0600, added to .gitignore.
    """
    link = parse_onboarding_url(read_url_argument(onboarding_url))
    cfg = _config_from_link(ctx, link)
    cwd = Path.cwd()
    _refuse_existing_files(cwd, has_token=cfg.api_token is not None, force=force)
    chosen_name = _verify_project(cfg, link.project_id)
    _write_config_files(cfg, cwd, link.project_id, chosen_name)


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

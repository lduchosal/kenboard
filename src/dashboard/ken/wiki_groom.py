"""``ken wiki groom`` — agent-driven task classification (#376).

Split out of ``ken/wiki.py`` (ken #808). The command registers on the ``wiki`` group;
section/slug helpers stay in ``ken/wiki.py``.
"""

from __future__ import annotations

import json as json_lib
import os
from typing import Any

import click

from dashboard.ken.config import KenConfig
from dashboard.ken.fmt import _format_columns, _output
from dashboard.ken.http import _request
from dashboard.ken.wiki import (
    _architecture_help,
    _load_sections,
    _section_title_for,
    wiki,
)

_WIKI_GROOM_HELP = """\
``ken wiki groom`` — agent-driven task classification for the project wiki.

WHAT THIS IS
============

The wiki is a structured MD tree exported from your kanban tasks,
organized according to your project's ``ARCHITECTURE.md`` (sections
declared in YAML frontmatter). The export step (``ken wiki sync``) needs
to know which section each task belongs to — that mapping is what we
call its *classification*.

This command is the bridge: an LLM agent reads the unclassified queue,
decides the best section for each task, and writes back via repeated
``ken wiki groom <id> <section>`` calls. No model is invoked by ``ken``
itself — the agent is the orchestrator.

Conceptual reference (LLM Wiki pattern):
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

WORKFLOW
========

1. Call ``ken wiki groom`` with no args to dump:
   - the list of unclassified tasks (id / status / who / title)
   - the section paths declared in ``ARCHITECTURE.md``
   - instructions for the next step

2. For each task, decide the best section by reading the task title
   (and ``ken show <id>`` if needed) against the section descriptions.
   Prefer the deepest matching path (``backend/api`` beats ``backend``).

3. Apply the decision:

       ken wiki groom <task_id> <section_path>

   Example:

       ken wiki groom 42 backend/api

   The section path must exist in ``ARCHITECTURE.md`` — typos are
   rejected with the list of valid paths.

4. To inspect or revert:

       ken wiki groom <id> --show     # current classification
       ken wiki groom <id> --clear    # drop, back to unclassified

OPTIONS
=======

``--architecture PATH``  alternate path to the architecture file
                         (default: ``./ARCHITECTURE.md`` in cwd).
"""


def _classified_by(cfg: KenConfig) -> str:
    """Best-effort actor label sent to the server's ``classified_by`` column.

    Prefers the API token's user (server resolves it via the auth middleware), falls
    back to the local ``$USER`` env var, then to ``"agent"``.
    """
    if cfg.api_token:
        # The server's _principal_name() picks the real identity from the
        # token — sending anything here is overwritten. Send a hint anyway
        # so it shows up if the server is mis-configured.
        return os.environ.get("USER") or "agent"
    return os.environ.get("USER") or "agent"


def _show_classification(cfg: KenConfig, task_id: int, *, json_mode: bool) -> None:
    """Print the current classification of ``task_id`` (friendly on 404)."""
    try:
        row = _request(cfg, "GET", f"/api/v1/wiki/classify/{task_id}")
    except SystemExit:
        # _request exits on HTTPError; the 404 ("Unclassified")
        # case is informational, not fatal. Re-emit a friendly
        # line then exit 0 instead of propagating.
        click.echo(f"Task #{task_id} is unclassified.")
        return
    _output(row, json_mode=json_mode, columns=None)


def _classify_task(
    cfg: KenConfig,
    task_id: int,
    section: str,
    architecture: str,
    *,
    json_mode: bool,
) -> None:
    """Validate ``section`` against the architecture and classify ``task_id``.

    Raises:
        UsageError: when the architecture declares no sections or the section
            path isn't one of them.
    """
    # Validate against the architecture before sending.
    _sections, valid = _load_sections(architecture)
    if not valid:
        raise click.UsageError(_architecture_help(architecture))
    if section not in valid:
        joined = "\n  ".join(valid)
        msg = f"Unknown section '{section}'. Declared paths:\n  {joined}"
        raise click.UsageError(msg)
    body = {
        "task_id": task_id,
        "section_path": section,
        "classified_by": _classified_by(cfg),
    }
    row = _request(cfg, "POST", "/api/v1/wiki/classify", body=body)
    _output(row, json_mode=json_mode, columns=None)


def _print_groom_overview(
    unclassified: list[dict[str, Any]],
    sections: list,
    paths: list[str],
    architecture: str,
) -> None:
    """Print the human-readable groom overview (instructions + tables)."""
    click.echo("WIKI GROOMING")
    click.echo("")
    click.echo(
        "Assign each task to a section of ARCHITECTURE.md so the wiki "
        "export mirrors the project structure. Decide for each task, "
        "then run:",
    )
    click.echo("")
    click.echo("    ken wiki groom <id> <section>")
    click.echo("")
    if not unclassified:
        click.echo("(no unclassified tasks)")
    else:
        click.echo(f"{len(unclassified)} unclassified task(s):")
        click.echo(
            _format_columns(
                unclassified,
                [
                    ("ID", "id"),
                    ("STATUS", "status"),
                    ("WHO", "who"),
                    ("TITLE", "title"),
                ],
            ),
        )
    click.echo("")
    if not paths:
        click.echo(_architecture_help(architecture))
    else:
        click.echo(f"Sections (from {architecture}):")
        for p in paths:
            title = _section_title_for(sections, p)
            click.echo(f"  {p:30s}  {title}")
    click.echo("")
    click.echo("See `ken wiki groom --help` for the concept (LLM Wiki pattern).")


def _groom_overview(cfg: KenConfig, architecture: str, *, json_mode: bool) -> None:
    """List unclassified tasks + declared sections (the no-args groom view)."""
    # When a project is configured, send it server-side so a per-project
    # api_key passes the auth scope check (admin keys see across projects).
    endpoint = "/api/v1/wiki/unclassified"
    if cfg.project_id:
        endpoint = f"{endpoint}?project={cfg.project_id}"
    unclassified = _request(cfg, "GET", endpoint) or []
    sections, paths = _load_sections(architecture)

    if json_mode:
        click.echo(
            json_lib.dumps(
                {
                    "unclassified": unclassified,
                    "sections": [
                        {"path": p, "title": _section_title_for(sections, p)}
                        for p in paths
                    ],
                    "architecture": architecture,
                },
                indent=2,
                default=str,
            ),
        )
        return

    _print_groom_overview(unclassified, sections, paths, architecture)


@wiki.command(name="groom", help="Classify tasks into wiki sections (agent-driven).")
@click.argument("task_id", type=int, required=False)
@click.argument("section", required=False)
@click.option(
    "--architecture",
    default=None,
    help=(
        "Path to the architecture file. Resolves to: flag > KEN_ARCHITECTURE "
        "env > `architecture=` in .ken > ./ARCHITECTURE.md (#473)."
    ),
)
@click.option("--show", is_flag=True, help="Show current classification for TASK_ID.")
@click.option("--clear", is_flag=True, help="Drop the classification for TASK_ID.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def groom(  # noqa: PLR0913
    ctx: click.Context,
    task_id: int | None,
    section: str | None,
    architecture: str | None,
    *,
    show: bool,
    clear: bool,
    json_mode: bool,
) -> None:
    """See ``ken wiki groom --help`` for the LLM Wiki pattern.

    Raises:
        UsageError: when the flag combination is invalid (e.g. ``--show`` and
            ``--clear`` together), when an op requiring ``TASK_ID`` is invoked
            without one, or when the section path isn't declared in the
            project's ARCHITECTURE.md.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    architecture = architecture or cfg.architecture
    if show and clear:
        msg = "--show and --clear are mutually exclusive."
        raise click.UsageError(msg)
    if (show or clear) and task_id is None:
        msg = "--show / --clear require TASK_ID."
        raise click.UsageError(msg)
    if section is not None and task_id is None:
        msg = "SECTION requires TASK_ID."
        raise click.UsageError(msg)

    if task_id is None:
        _groom_overview(cfg, architecture, json_mode=json_mode)
    elif clear:
        _request(cfg, "DELETE", f"/api/v1/wiki/classify/{task_id}")
        click.echo(f"Cleared classification for task #{task_id}.")
    elif show:
        _show_classification(cfg, task_id, json_mode=json_mode)
    elif section is None:
        msg = "Pass SECTION to classify, or --show / --clear."
        raise click.UsageError(msg)
    else:
        _classify_task(cfg, task_id, section, architecture, json_mode=json_mode)


groom.help = _WIKI_GROOM_HELP

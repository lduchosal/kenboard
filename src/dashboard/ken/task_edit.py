"""``ken add`` / ``ken update`` — task mutations and their shared helpers.

Split out of ``ken/tasks.py`` (ken #808): attachement/description input handling (#574,
#393), the two commands, and the move-to-review reminders (#605, #376) used by both
``update`` and ``move``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from dashboard.ken.cli import cli
from dashboard.ken.config import TASK_COLUMNS, VALID_STATUSES, KenConfig
from dashboard.ken.fmt import _output
from dashboard.ken.http import _request, _require_project

# tasks.attachement is MEDIUMTEXT (16 MB) — pre-check on the client so an
# oversized SVG fails with a clear CLI error instead of a 422 round-trip.
_ATTACHEMENT_MAX_BYTES = 16 * 1024 * 1024 - 1


def _read_attachement_file(path: str | None) -> str | None:
    """Read an attachement SVG from disk for ``ken add`` / ``ken update`` (#574).

    Used by both commands to populate ``tasks.attachement`` (the paintbrush extension's
    annotation layer, #541). Returns ``None`` when the path is not supplied. Pre-checks
    the encoded size against the MEDIUMTEXT column cap so an oversized payload fails
    with a clear CLI error instead of a 422 from the server.
    """
    if path is None:
        return None
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        msg = f"Cannot read --attachement-file: {e}"
        raise click.UsageError(msg) from e
    n = len(content.encode("utf-8"))
    if n > _ATTACHEMENT_MAX_BYTES:
        msg = (
            f"--attachement-file is too large ({n} bytes); "
            f"the tasks.attachement column caps at {_ATTACHEMENT_MAX_BYTES} bytes."
        )
        raise click.UsageError(msg)
    return content


def _resolve_desc(desc: str | None, desc_file: str | None = None) -> str | None:
    """Pick the description body from --desc-file > stdin (--desc -) > --desc (#393).

    Three input shapes are supported for agents that have different host capabilities:
    - ``--desc-file path/to/body.md`` reads from a file on disk (most agent-friendly,
      no shell escaping at all).
    - ``--desc -`` reads from stdin (heredoc-friendly for agents that can pipe).
    - ``--desc "literal text"`` passes the value through unchanged (single-line only —
      multi-line bash double-quoted strings drop newlines).

    Passing both ``--desc`` and ``--desc-file`` is an error so we don't have to invent
    a merge semantic. ``None`` (option not passed) and the empty string fall through
    unchanged.
    """
    if desc_file:
        if desc:
            msg = (
                "Pass --desc OR --desc-file, not both. "
                "See `ken help` for the multi-line description idioms."
            )
            raise click.UsageError(msg)
        try:
            return Path(desc_file).read_text(encoding="utf-8")
        except OSError as e:
            msg = f"Cannot read --desc-file: {e}"
            raise click.UsageError(msg) from e
    if desc == "-":
        return sys.stdin.read()
    return desc


@cli.command()
@click.argument("title")
@click.option(
    "--desc",
    default="",
    help="Description (single-line text, or '-' to read stdin)",
)
@click.option(
    "--desc-file",
    type=click.Path(dir_okay=False, readable=True),
    default=None,
    help="Read description from a file on disk (best for multi-line markdown)",
)
@click.option("--who", default="", help="Assignee")
@click.option("--status", type=click.Choice(VALID_STATUSES), default="todo")
@click.option("--when", help="Due date YYYY-MM-DD")
@click.option(
    "--attachement-file",
    "attachement_file",
    type=click.Path(dir_okay=False, readable=True),
    default=None,
    help="Read an SVG attachement (#541) from this path",
)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
# One option per task field, by design — silence the "too many arguments" warning.
@click.pass_context
def add(  # noqa: PLR0913
    ctx: click.Context,
    title: str,
    desc: str,
    desc_file: str | None,
    who: str,
    status: str,
    when: str | None,
    attachement_file: str | None,
    *,
    json_mode: bool,
) -> None:
    r"""Add a new task to the current project.

    For multi-line markdown descriptions, prefer ``--desc-file path/to/body.md`` (no
    shell escaping at all). ``--desc -`` reads from stdin (heredoc). Passing ``--desc
    "line1\nline2"`` in a double-quoted shell string stores the literal ``\n`` and
    breaks markdown rendering. See ``ken help`` for full examples.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    body: dict[str, Any] = {
        "project_id": project_id,
        "title": title,
        "description": _resolve_desc(desc, desc_file) or "",
        "who": who,
        "status": status,
        "due_date": when,
    }
    attachement = _read_attachement_file(attachement_file)
    if attachement is not None:
        body["attachement"] = attachement
    task = _request(cfg, "POST", "/api/v1/tasks", body=body)
    _output(task, json_mode=json_mode, columns=TASK_COLUMNS)


@cli.command()
@click.argument("task_id", type=int)
@click.option("--title", help="New title")
@click.option(
    "--desc",
    help="New description (single-line text, or '-' to read stdin)",
)
@click.option(
    "--desc-file",
    type=click.Path(dir_okay=False, readable=True),
    default=None,
    help="Read new description from a file on disk (best for multi-line markdown)",
)
@click.option("--who", help="New assignee")
@click.option("--status", type=click.Choice(VALID_STATUSES), help="New status")
@click.option("--when", help="New due date YYYY-MM-DD")
@click.option(
    "--attachement-file",
    "attachement_file",
    type=click.Path(dir_okay=False, readable=True),
    default=None,
    help="Read an SVG attachement (#541) from this path",
)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
# One option per task field, by design — silence the "too many arguments" warning.
@click.pass_context
def update(  # noqa: PLR0913
    ctx: click.Context,
    task_id: int,
    title: str | None,
    desc: str | None,
    desc_file: str | None,
    who: str | None,
    status: str | None,
    when: str | None,
    attachement_file: str | None,
    *,
    json_mode: bool,
) -> None:
    r"""Update an existing task (only the fields you pass).

    For multi-line markdown in the description, prefer ``--desc-file path/to/body.md``
    (no shell escaping). ``--desc -`` reads from stdin (heredoc). ``--desc
    "line1\nline2"`` in a bash double-quoted string stores literal backslash-n's and
    corrupts markdown rendering (#393).
    """
    cfg: KenConfig = ctx.obj["cfg"]
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    # ``--desc-file`` is independent of ``--desc`` being set; resolve through
    # the helper so the file path wins (with a UsageError if both are passed).
    if desc is not None or desc_file is not None:
        body["description"] = _resolve_desc(desc, desc_file)
    if who is not None:
        body["who"] = who
    if status is not None:
        body["status"] = status
    if when is not None:
        body["due_date"] = when
    if attachement_file is not None:
        body["attachement"] = _read_attachement_file(attachement_file)
    if not body:
        click.echo(
            "Error: nothing to update. Pass at least one of "
            "--title/--desc/--who/--status/--when/--attachement-file",
            err=True,
        )
        sys.exit(1)
    task = _request(cfg, "PATCH", f"/api/v1/tasks/{task_id}", body=body)
    _output(task, json_mode=json_mode, columns=TASK_COLUMNS)
    if status == "review":
        _review_update_reminder(task_id)
        _wiki_groom_reminder(task_id)


def _review_update_reminder(task_id: int) -> None:
    """Remind the agent to append an implementation trail to the task (#605).

    Printed to stderr so it doesn't corrupt ``--json`` output. The original description
    must be preserved verbatim and the implementation details appended as a new section
    — the board is the audit trail when commits don't map 1:1 to tasks.
    """
    click.echo(
        f"Reminder: update task #{task_id} with the implementation trail before review:\n"
        f"    ken show {task_id}                          # read the original description\n"
        f'    ken update {task_id} --desc "<original>\\n\\n---\\n\\n## Résolution\\n..."\n'
        "Keep the original description intact; append a Résolution section with\n"
        "Modifications (files + one-line summary), Comportements obtenus, Garde-fous.",
        err=True,
    )


def _wiki_groom_reminder(task_id: int) -> None:
    """Remind the agent to classify the task for the wiki (#376).

    Printed to stderr so it doesn't corrupt ``--json`` output. Always shown on
    transitions to ``review`` — if the task is already classified the reminder is a
    cheap no-op for the agent.
    """
    click.echo(
        f"Reminder: classify task #{task_id} for the wiki:\n"
        f"    ken wiki groom {task_id} <section_path>\n"
        "(run `ken wiki groom` with no args to list available sections)",
        err=True,
    )

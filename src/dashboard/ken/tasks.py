"""Task commands of the ``ken`` CLI.

Everything that manipulates board tasks: ``projects``, ``list``, ``show``, ``add``,
``update``, ``polish``, ``move`` and ``done``. The disk mirror lives in ``sync``.
"""

from __future__ import annotations

import json as json_lib
import sys
import tempfile
from pathlib import Path
from typing import Any

import click

from dashboard.ken.cli import cli
from dashboard.ken.config import TASK_COLUMNS, VALID_STATUSES, KenConfig
from dashboard.ken.fmt import _output
from dashboard.ken.http import _request, _require_project


@cli.command()
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.pass_context
def projects(ctx: click.Context, json_mode: bool) -> None:
    """List all projects on the kenboard."""
    cfg: KenConfig = ctx.obj["cfg"]
    data = _request(cfg, "GET", "/api/v1/projects")
    _output(
        data,
        json_mode,
        columns=[("ID", "id"), ("ACRONYM", "acronym"), ("NAME", "name")],
    )


@cli.command(name="list")
@click.option("--status", type=click.Choice(VALID_STATUSES))
@click.option("--who", help="Filter by assignee")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.pass_context
def list_tasks(
    ctx: click.Context, status: str | None, who: str | None, json_mode: bool
) -> None:
    """List tasks of the current project."""
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    tasks = _request(cfg, "GET", f"/api/v1/tasks?project={project_id}")
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if who:
        tasks = [t for t in tasks if t.get("who") == who]
    _output(tasks, json_mode, columns=TASK_COLUMNS)


@cli.command()
@click.argument("task_id", type=int)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.option(
    "--save-attachement",
    "save_attachement",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Write the task's SVG attachement (#541) to this path and exit",
)
@click.pass_context
def show(
    ctx: click.Context,
    task_id: int,
    json_mode: bool,
    save_attachement: str | None,
) -> None:
    """Show full details of a task."""
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    tasks = _request(cfg, "GET", f"/api/v1/tasks?project={project_id}")
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        click.echo(
            f"Error: task #{task_id} not found in project {project_id}",
            err=True,
        )
        sys.exit(1)
    # --save-attachement: write the SVG and exit (no other output on success
    # except a short stderr confirmation — keeps stdout clean for shell pipes).
    if save_attachement is not None:
        att = task.get("attachement")
        if not att:
            click.echo(f"Error: task #{task_id} has no attachement", err=True)
            sys.exit(1)
        try:
            Path(save_attachement).write_text(att, encoding="utf-8")
        except OSError as e:
            click.echo(f"Error: cannot write attachement: {e}", err=True)
            sys.exit(1)
        click.echo(
            f"Wrote {len(att.encode('utf-8'))} bytes to {save_attachement}",
            err=True,
        )
        return
    if json_mode:
        click.echo(json_lib.dumps(task, indent=2, default=str))
        return
    for key in (
        "id",
        "status",
        "who",
        "due_date",
        "title",
        "description",
        "created_at",
        "updated_at",
    ):
        click.echo(f"{key:12s}: {task.get(key) if task.get(key) is not None else ''}")
    # Attachement hint (#574) — show size + how to retrieve, but never the
    # raw SVG (would flood the terminal).
    att = task.get("attachement")
    if att:
        size_kb = len(att.encode("utf-8")) / 1024
        click.echo(
            f"{'attachement':12s}: {size_kb:.1f} KB SVG "
            f"(use `ken show {task_id} --save-attachement <path>` to write)"
        )


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
        raise click.UsageError(f"Cannot read --attachement-file: {e}") from e
    n = len(content.encode("utf-8"))
    if n > _ATTACHEMENT_MAX_BYTES:
        raise click.UsageError(
            f"--attachement-file is too large ({n} bytes); "
            f"the tasks.attachement column caps at {_ATTACHEMENT_MAX_BYTES} bytes."
        )
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
            raise click.UsageError(
                "Pass --desc OR --desc-file, not both. "
                "See `ken help` for the multi-line description idioms.",
            )
        try:
            return Path(desc_file).read_text(encoding="utf-8")
        except OSError as e:
            raise click.UsageError(f"Cannot read --desc-file: {e}") from e
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
    _output(task, json_mode, columns=TASK_COLUMNS)


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
    _output(task, json_mode, columns=TASK_COLUMNS)
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


@cli.command()
@click.argument("task_id", type=int)
@click.option(
    "--tmp-dir",
    "tmp_dir",
    default=None,
    type=click.Path(file_okay=False, writable=True),
    help="Directory for the dropped SVG + description "
    "(default: system temp dir via tempfile.gettempdir())",
)
@click.pass_context
def polish(ctx: click.Context, task_id: int, tmp_dir: str | None) -> None:
    """Prepare a paintbrush task for agent reformulation (#550).

    Saves the task's raw description and (when present) its SVG attachement on disk and
    prints a structured prompt instructing the agent to read both, propose a clean
    ``MODULE / Titre`` + actionable description, and apply via ``ken update``. The
    command itself never calls an LLM — keeping ``ken`` dependency-free was an explicit
    design choice (#550 phase 1).

    The default temp directory is resolved at call time via ``tempfile.gettempdir()``
    (system-specific) rather than a hardcoded ``/tmp`` so Windows hosts get a sensible
    default and Sonar stops flagging a fixed publicly-writable path.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    tasks = _request(cfg, "GET", f"/api/v1/tasks?project={project_id}")
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        click.echo(
            f"Error: task #{task_id} not found in project {project_id}",
            err=True,
        )
        sys.exit(1)
    tmp = Path(tmp_dir) if tmp_dir is not None else Path(tempfile.gettempdir())
    desc_path = tmp / f"kenboard-polish-{task_id}.md"
    svg_path = tmp / f"kenboard-polish-{task_id}.svg"
    desc_path.write_text(task.get("description") or "", encoding="utf-8")
    svg_note: str
    if task.get("attachement"):
        svg_path.write_text(task["attachement"], encoding="utf-8")
        svg_note = (
            f"  SVG attachement : {svg_path} "
            f"(ouvre-le pour voir ce qui a été encadré)"
        )
    else:
        svg_note = "  SVG attachement : (aucun)"
    click.echo(
        "\n".join(
            [
                f"# Polish task #{task_id} — agent reformulation prompt",
                "",
                f"Titre actuel : {task.get('title', '')!r}",
                f"Status      : {task.get('status', '')}",
                f"Description sauvée dans : {desc_path}",
                svg_note,
                "",
                "Action attendue (agent / LLM) :",
                "  1. Lis la description (et le SVG si présent : il a la page "
                "encadrée par l'utilisateur).",
                "  2. Produis un nouveau MODULE / Titre concis (convention "
                "kenboard, cf. `ken help`).",
                "  3. Réécris la description en mode résolution actionnable "
                "(contexte, ce qu'il faut faire, garde-fous).",
                "  4. Applique :",
                f"       ken update {task_id} --title 'MODULE / ...' "
                f"--desc-file {desc_path}",
                "",
                "Le SVG attachement reste inchangé (trace de la demande " "d'origine).",
            ]
        )
    )


@cli.command()
@click.argument("task_id", type=int)
@click.option(
    "--to",
    "to_status",
    required=True,
    type=click.Choice(VALID_STATUSES),
    help="Target status column",
)
@click.pass_context
def move(ctx: click.Context, task_id: int, to_status: str) -> None:
    """Move a task to another status column."""
    cfg: KenConfig = ctx.obj["cfg"]
    task = _request(
        cfg, "PATCH", f"/api/v1/tasks/{task_id}", body={"status": to_status}
    )
    click.echo(f"Task #{task['id']} → {task['status']}")
    if to_status == "review":
        _review_update_reminder(task_id)
        _wiki_groom_reminder(task_id)


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def done(ctx: click.Context, task_id: int) -> None:
    """Mark a task as done — shortcut for `update --status done`."""
    cfg: KenConfig = ctx.obj["cfg"]
    task = _request(cfg, "PATCH", f"/api/v1/tasks/{task_id}", body={"status": "done"})
    click.echo(f"Task #{task['id']} → {task['status']}")

"""Task commands of the ``ken`` CLI.

Everything that manipulates board tasks: ``projects``, ``list``, ``show``, ``add``,
``update``, ``polish``, ``move`` and ``done``. The disk mirror lives in ``sync``.
"""

from __future__ import annotations

import json as json_lib
import sys
from pathlib import Path
from typing import Any

import click

from dashboard.ken.cli import cli
from dashboard.ken.config import TASK_COLUMNS, VALID_STATUSES, KenConfig
from dashboard.ken.fmt import _output
from dashboard.ken.http import _request, _require_project
from dashboard.ken.task_edit import _review_update_reminder, _wiki_groom_reminder


@cli.command()
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.pass_context
def projects(ctx: click.Context, *, json_mode: bool) -> None:
    """List all projects on the kenboard."""
    cfg: KenConfig = ctx.obj["cfg"]
    data = _request(cfg, "GET", "/api/v1/projects")
    _output(
        data,
        json_mode=json_mode,
        columns=[("ID", "id"), ("ACRONYM", "acronym"), ("NAME", "name")],
    )


@cli.command(name="list")
@click.option("--status", type=click.Choice(VALID_STATUSES))
@click.option("--who", help="Filter by assignee")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.pass_context
def list_tasks(
    ctx: click.Context, status: str | None, who: str | None, *, json_mode: bool
) -> None:
    """List tasks of the current project."""
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    tasks = _request(cfg, "GET", f"/api/v1/tasks?project={project_id}")
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if who:
        tasks = [t for t in tasks if t.get("who") == who]
    _output(tasks, json_mode=json_mode, columns=TASK_COLUMNS)


def _save_attachement(task: dict[str, Any], task_id: int, path: str) -> None:
    """Write the task's SVG attachement (#541) to ``path`` and confirm on stderr.

    No other output on success — keeps stdout clean for shell pipes.
    """
    att = task.get("attachement")
    if not att:
        click.echo(f"Error: task #{task_id} has no attachement", err=True)
        sys.exit(1)
    try:
        Path(path).write_text(att, encoding="utf-8")
    except OSError as e:
        click.echo(f"Error: cannot write attachement: {e}", err=True)
        sys.exit(1)
    click.echo(f"Wrote {len(att.encode('utf-8'))} bytes to {path}", err=True)


def _print_task(task: dict[str, Any], task_id: int) -> None:
    """Print the human-readable task detail (attachement hinted, never dumped)."""
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
    *,
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
    if save_attachement is not None:
        _save_attachement(task, task_id, save_attachement)
        return
    if json_mode:
        click.echo(json_lib.dumps(task, indent=2, default=str))
        return
    _print_task(task, task_id)


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

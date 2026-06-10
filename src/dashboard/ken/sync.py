"""``ken sync`` — mirror the board's tasks to disk as markdown files."""

from __future__ import annotations

import json as json_lib
from pathlib import Path

import click

from dashboard.ken.cli import cli
from dashboard.ken.config import KenConfig, _persist_sync_dir, _resolve_sync_dir
from dashboard.ken.fmt import _SYNC_FILENAME_RE, _format_sync_markdown, _sync_filename
from dashboard.ken.http import _request, _require_project


@cli.command()
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.pass_context
def sync(ctx: click.Context, *, json_mode: bool) -> None:
    """Mirror the project's tasks into ``sync_dir`` as one markdown file each.

    For every task in the configured project, writes
    ``<sync_dir>/<id> - <title>.md`` with a YAML frontmatter header.
    Files corresponding to tasks that no longer exist on the board are
    deleted, and title changes are handled by removing the old file
    before writing the new one. ``sync_dir`` defaults to ``doc/kenboard``
    and is persisted into ``.ken`` on first use.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    target = _resolve_sync_dir(cfg)
    target.mkdir(parents=True, exist_ok=True)
    _persist_sync_dir(cfg)

    tasks = _request(cfg, "GET", f"/api/v1/tasks?project={project_id}")
    desired: dict[int, tuple[str, str]] = {
        int(t["id"]): (_sync_filename(t), _format_sync_markdown(t)) for t in tasks
    }

    existing: dict[int, Path] = {}
    for entry in target.iterdir():
        if not entry.is_file():
            continue
        match = _SYNC_FILENAME_RE.match(entry.name)
        if match:
            existing[int(match.group(1))] = entry

    written: list[str] = []
    deleted: list[str] = []
    for task_id, (filename, content) in desired.items():
        new_path = target / filename
        old = existing.get(task_id)
        if old is not None and old != new_path:
            old.unlink()
            deleted.append(old.name)
        new_path.write_text(content, encoding="utf-8")
        written.append(filename)

    for task_id, path in existing.items():
        if task_id not in desired:
            path.unlink()
            deleted.append(path.name)

    if json_mode:
        click.echo(
            json_lib.dumps(
                {
                    "target": str(target),
                    "written": sorted(written),
                    "deleted": sorted(deleted),
                },
                indent=2,
            )
        )
        return
    click.echo(f"Synced {len(written)} task(s) to {target}")
    if deleted:
        click.echo(f"Removed {len(deleted)} stale file(s)")

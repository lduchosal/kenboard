"""``ken wiki sync`` — export classifications to a structured MD tree.

The per-page-kind formatters live in ``wiki_md`` since #1017; they feed
``_build_sync_plan``, which plans every file to write, and the command materialises the
plan on disk (#376c, #376f, #742).
"""

from __future__ import annotations

import json as json_lib
import shutil
from pathlib import Path
from typing import Any

import click

from dashboard.ken.config import KenConfig
from dashboard.ken.http import _request
from dashboard.ken.wiki import (
    _architecture_help,
    _load_sections,
    _task_filename,
    wiki,
)
from dashboard.ken.wiki_log import (
    _classified_date,
    _format_log_day_md,
    _format_log_index_md,
    _format_orphans_md,
)
from dashboard.ken.wiki_md import (
    _format_root_index_md,
    _format_section_md,
    _format_task_detail_md,
)


def _section_pages(
    sections: list, by_path: dict[str, list[dict[str, Any]]]
) -> list[dict[str, str]]:
    """One ``index.md`` per section plus the per-task detail pages (#376f)."""
    files: list[dict[str, str]] = []
    for section in sections:
        for path, node in section.flatten():
            section_tasks = by_path.get(path, [])
            files.append(
                {
                    "path": f"{path}/index.md",
                    "content": _format_section_md(node, path, section_tasks),
                },
            )
            # One MD per task with YAML frontmatter so wiki build can lift
            # the metadata into the ``.fullscreen-card`` HTML layout.
            files.extend(
                {
                    "path": f"{path}/{_task_filename(task)}",
                    "content": _format_task_detail_md(task, path, node.title),
                }
                for task in section_tasks
            )
    return files


def _build_sync_plan(
    sections: list, paths: list[str], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Plan every file to write — pure function, easy to unit test."""
    by_path: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_path.setdefault(r["section_path"], []).append(r)
    declared = set(paths)
    orphans = {p: v for p, v in by_path.items() if p not in declared}

    files: list[dict[str, str]] = [
        {"path": "index.md", "content": _format_root_index_md(sections, by_path)},
    ]
    files.extend(_section_pages(sections, by_path))
    # Journal d'exploitation (#742) — one MD per day, plus an index. Replaces
    # the flat ``log.md`` so the sidebar can list days and detail pages can
    # link to the specific day rather than a giant single page.
    by_date: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_date.setdefault(_classified_date(r), []).append(r)
    files.append(
        {"path": "log/index.md", "content": _format_log_index_md(by_date)},
    )
    for date, day_tasks in by_date.items():
        files.append(
            {"path": f"log/{date}.md", "content": _format_log_day_md(date, day_tasks)},
        )
    if orphans:
        files.append({"path": "orphans.md", "content": _format_orphans_md(orphans)})
    return {
        "files": files,
        "sections": len(paths),
        "classifications": len(rows),
        "orphans": len(orphans),
    }


def _write_sync_plan(out: str, plan: dict[str, Any]) -> None:
    """Idempotently materialise ``plan`` under ``out`` (clean + re-write)."""
    base = Path(out)
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    for f in plan["files"]:
        target = base / f["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f["content"], encoding="utf-8")


@wiki.command(name="sync", help="Export classifications to a structured MD tree.")
@click.option(
    "--out",
    default=None,
    help=(
        "Output directory — re-written from scratch each run. Resolves to: "
        "flag > KEN_WIKI_DIR env > `wiki_dir=` in .ken > ./wiki (#479)."
    ),
)
@click.option(
    "--architecture",
    default=None,
    help=(
        "Path to the architecture file. Resolves to: flag > KEN_ARCHITECTURE "
        "env > `architecture=` in .ken > ./ARCHITECTURE.md (#473)."
    ),
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Dry-run: print the plan as JSON and don't touch disk.",
)
@click.pass_context
def wiki_sync(
    ctx: click.Context,
    out: str | None,
    architecture: str | None,
    *,
    json_mode: bool,
) -> None:
    """Materialise the wiki MD tree from live classifications (chunk C, #376c).

    Raises:
        UsageError: when ``ARCHITECTURE.md`` is missing or declares no sections.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    architecture = architecture or cfg.architecture
    out = out or cfg.wiki_dir
    sections, paths = _load_sections(architecture)
    if not paths:
        raise click.UsageError(_architecture_help(architecture))
    endpoint = "/api/v1/wiki/all"
    if cfg.project_id:
        endpoint = f"{endpoint}?project={cfg.project_id}"
    rows = _request(cfg, "GET", endpoint) or []
    plan = _build_sync_plan(sections, paths, rows)

    if json_mode:
        click.echo(json_lib.dumps(plan, indent=2, default=str))
        return

    _write_sync_plan(out, plan)
    click.echo(
        f"Wrote {len(plan['files'])} file(s) under {out}/ "
        f"({plan['sections']} sections, {plan['classifications']} classifications"
        + (f", {plan['orphans']} orphan section(s)" if plan["orphans"] else "")
        + ").",
    )

"""``ken wiki sync`` — export classifications to a structured MD tree.

Pure formatting helpers (one per page kind) feed ``_build_sync_plan``, which plans every
file to write; the command materialises the plan on disk (#376c, #376f, #742).
"""

from __future__ import annotations

import json as json_lib
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from dashboard.ken.config import KenConfig
from dashboard.ken.http import _request
from dashboard.ken.wiki_log import (
    _ARCHIVED_STATUSES,
    _classified_date,
    _format_log_day_md,
    _format_log_index_md,
    _format_orphans_md,
)

if TYPE_CHECKING:
    from dashboard.wiki import Section
from dashboard.ken.wiki import (
    _architecture_help,
    _load_sections,
    _task_filename,
    wiki,
)

_ACTIVE_STATUS_ORDER = ("doing", "review", "todo")


def _format_section_md(node: Section, path: str, tasks: list[dict[str, Any]]) -> str:
    """Render one section's ``index.md`` — split into "En cours" / "Archivé" (#376f).

    Each row links to ``<slug>-<id>.md`` (the per-task detail page). ``who`` is omitted
    (always Q/Claude → no signal). ``status`` and ``due_date`` are only shown when they
    carry information (status hidden on archived rows; due_date only if set on a non-
    done task).
    """
    lines = [f"# {node.title}", ""]
    if node.description:
        lines.extend([node.description, ""])
    lines.extend([f"Section: `{path}`", ""])
    if not tasks:
        lines.append("(no tasks classified yet)")
        return "\n".join(lines) + "\n"

    active = [t for t in tasks if (t.get("status") or "") not in _ARCHIVED_STATUSES]
    archived = [t for t in tasks if (t.get("status") or "") in _ARCHIVED_STATUSES]

    def _active_key(t: dict[str, Any]) -> tuple[int, int]:
        """Sort key: doing → review → todo → others, ties broken by id."""
        status = t.get("status") or ""
        order = (
            _ACTIVE_STATUS_ORDER.index(status)
            if status in _ACTIVE_STATUS_ORDER
            else len(_ACTIVE_STATUS_ORDER)
        )
        return (order, int(t["task_id"]))

    if active:
        lines.extend((f"## En cours ({len(active)})", ""))
        lines.extend(
            _format_section_row(t, archived=False)
            for t in sorted(active, key=_active_key)
        )
        lines.append("")
    if archived:
        lines.extend((f"## Archivé ({len(archived)})", ""))
        lines.extend(
            _format_section_row(t, archived=True)
            for t in sorted(archived, key=lambda x: int(x["task_id"]))
        )
    return "\n".join(lines) + "\n"


def _format_section_row(task: dict[str, Any], *, archived: bool) -> str:
    """One bullet line for the section index — `[title](slug-id.md)` + metadata."""
    title = task.get("title") or ""
    href = _task_filename(task)
    line = f"- [{title}]({href})"
    if not archived:
        status = task.get("status") or ""
        if status:
            line += f" — _{status}_"
        due = task.get("due_date")
        if due:
            line += f" — due {due}"
    return line


def _format_task_detail_md(
    task: dict[str, Any], section_path: str, section_title: str
) -> str:
    """Render the per-task detail page (#376f).

    Emits YAML frontmatter so ``wiki build`` can lift the metadata into the
    ``.fullscreen-card`` HTML layout without re-parsing the body. The body is the task
    description, rendered as-is (already MD).
    """
    fm_lines = [
        "---",
        f"id: {task['task_id']}",
        f"title: {_yaml_str(task.get('title') or '')}",
        f"status: {task.get('status') or ''}",
        f"who: {_yaml_str(task.get('who') or '')}",
        f"due_date: {task.get('due_date') or ''}",
        f"classified_at: {task.get('classified_at') or ''}",
        f"classified_by: {_yaml_str(task.get('classified_by') or '')}",
        f"section: {section_path}",
        f"section_title: {_yaml_str(section_title)}",
        "---",
        "",
    ]
    title = task.get("title") or ""
    body_lines = [
        f"# #{task['task_id']} — {title}",
        "",
    ]
    desc = task.get("description") or ""
    if desc.strip():
        body_lines.extend([desc.rstrip(), ""])
    else:
        body_lines.extend(["*(no description)*", ""])
    # #742 — point "voir log" at the task's specific day instead of a flat
    # log.md, so readers land on the daily journal page that contains it.
    log_day = _classified_date(task)
    up_to_root = "../" * (section_path.count("/") + 1)
    nav = (
        f"---\n\n[← retour à {section_path}](index.md) · "
        f"[voir log]({up_to_root}log/{log_day}.md)\n"
    )
    return "\n".join(fm_lines + body_lines) + nav


def _yaml_str(text: str) -> str:
    """Quote a YAML scalar so colons / `#` / leading whitespace don't break parsing."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _format_root_index_md(
    sections: list, by_path: dict[str, list[dict[str, Any]]]
) -> str:
    """Render the wiki root ``index.md`` (sidebar-style TOC + counts)."""
    lines = ["# kenboard wiki", "", "Generated by `ken wiki sync`.", ""]
    total = sum(len(v) for v in by_path.values())
    lines.extend([f"Total classified: **{total}**.", ""])
    for section in sections:
        for path, node in section.flatten():
            depth = path.count("/")
            indent = "  " * depth
            count = len(by_path.get(path, []))
            lines.append(
                f"{indent}- [{node.title}]({path}/index.md) — {count} task(s)",
            )
    return "\n".join(lines) + "\n"


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

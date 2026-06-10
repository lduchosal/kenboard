"""``ken wiki lint`` — report orphans / unclassified / empty sections (#376e)."""

from __future__ import annotations

import json as json_lib
import sys
from typing import Any

import click

from dashboard.ken.config import KenConfig
from dashboard.ken.http import _request
from dashboard.ken.wiki import _architecture_help, _load_sections, wiki


def _build_lint_report(
    paths: list[str],
    classified: list[dict[str, Any]],
    unclassified: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute orphans / unclassified / empty-section findings (#376e).

    Pure function so the CLI's exit-code logic and JSON output share one source of
    truth. Inputs are the declared section paths from ``ARCHITECTURE.md`` and the two
    server lists (all classifications + unclassified tasks).
    """
    declared = set(paths)
    classified_paths = {r["section_path"] for r in classified}
    orphan_paths = sorted(classified_paths - declared)
    empty_sections = sorted(declared - classified_paths)

    orphans: list[dict[str, Any]] = []
    for path in orphan_paths:
        tasks = [r for r in classified if r["section_path"] == path]
        orphans.append(
            {
                "section_path": path,
                "task_count": len(tasks),
                "task_ids": [r["task_id"] for r in tasks],
            },
        )

    unclassified_brief = [
        {
            "task_id": t["id"],
            "title": t.get("title") or "",
            "status": t.get("status") or "",
        }
        for t in unclassified
    ]

    return {
        "errors": [{"code": "ORPHAN"} | o for o in orphans],
        "warnings": [{"code": "UNCLASSIFIED"} | t for t in unclassified_brief],
        "info": [{"code": "EMPTY-SECTION", "section_path": p} for p in empty_sections],
        "summary": {
            "errors": len(orphans),
            "warnings": len(unclassified_brief),
            "info": len(empty_sections),
            "sections": len(declared),
            "classified": len(classified),
        },
    }


def _print_lint_report(report: dict[str, Any]) -> None:
    """Render the lint report as readable text on stdout."""
    s = report["summary"]
    click.echo(
        f"wiki lint: {s['errors']} error(s), {s['warnings']} warning(s), "
        f"{s['info']} info ({s['sections']} sections, "
        f"{s['classified']} classifications)",
    )
    if report["errors"]:
        click.echo("")
        click.echo("ERRORS:")
        for e in report["errors"]:
            ids = ", ".join(f"#{i}" for i in e["task_ids"])
            click.echo(
                f"  ORPHAN  section `{e['section_path']}` not in ARCHITECTURE.md "
                f"({e['task_count']} task(s): {ids})",
            )
    if report["warnings"]:
        click.echo("")
        click.echo("WARNINGS:")
        for w in report["warnings"]:
            click.echo(
                f"  UNCLASSIFIED  #{w['task_id']} [{w['status']}] {w['title']}",
            )
    if report["info"]:
        click.echo("")
        click.echo("INFO:")
        for i in report["info"]:
            click.echo(f"  EMPTY-SECTION  `{i['section_path']}` has no tasks")


@wiki.command(name="lint", help="Report orphans / unclassified / empty sections.")
@click.option(
    "--architecture",
    default=None,
    help=(
        "Path to the architecture file. Resolves to: flag > KEN_ARCHITECTURE "
        "env > `architecture=` in .ken > ./ARCHITECTURE.md (#473)."
    ),
)
@click.option(
    "--strict",
    is_flag=True,
    help="Warnings also fail with exit 1 (default: only errors fail).",
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Emit the report as JSON (stable schema for CI).",
)
@click.pass_context
def wiki_lint(
    ctx: click.Context,
    architecture: str | None,
    strict: bool,
    json_mode: bool,
) -> None:
    """Check the live wiki for orphans, unclassified tasks, and empty sections (#376e).

    Exit code: ``1`` when any ERROR is present, or when any WARNING is present in
    ``--strict`` mode. ``0`` otherwise.

    Raises:
        UsageError: when ``ARCHITECTURE.md`` is missing or declares no sections.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    architecture = architecture or cfg.architecture
    _sections, paths = _load_sections(architecture)
    if not paths:
        raise click.UsageError(_architecture_help(architecture))
    suffix = f"?project={cfg.project_id}" if cfg.project_id else ""
    classified = _request(cfg, "GET", f"/api/v1/wiki/all{suffix}") or []
    unclassified = _request(cfg, "GET", f"/api/v1/wiki/unclassified{suffix}") or []
    report = _build_lint_report(paths, classified, unclassified)

    if json_mode:
        click.echo(json_lib.dumps(report, indent=2, default=str))
    else:
        _print_lint_report(report)

    failing = report["summary"]["errors"] > 0 or (
        strict and report["summary"]["warnings"] > 0
    )
    if failing:
        sys.exit(1)

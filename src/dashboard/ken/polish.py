"""``ken polish`` — prepare a paintbrush task for agent reformulation (#550)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

import click

from dashboard.ken.cli import cli
from dashboard.ken.config import KenConfig
from dashboard.ken.http import _request, _require_project


def _polish_prompt(
    task_id: int, task: dict[str, Any], desc_path: Path, svg_note: str
) -> str:
    """Build the structured reformulation prompt printed to the agent."""
    return "\n".join(
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
    click.echo(_polish_prompt(task_id, task, desc_path, svg_note))

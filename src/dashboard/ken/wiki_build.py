"""``ken wiki build`` — render the wiki MD tree as standalone HTML.

Walks the MD tree and plans one HTML file per page; the chrome around each body (sidebar
nav, footer, page shell) lives in ``wiki_layout`` since #1017. Detail pages get the
``.fullscreen-card`` layout mirroring the board's full-screen task view (#376f, #741,
#742, #743).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import click

from dashboard.ken.config import KenConfig
from dashboard.ken.wiki import _architecture_help, _load_sections, wiki
from dashboard.ken.wiki_detail import (
    _render_markdown,
    _render_task_detail,
    _rewrite_md_links_to_html,
)
from dashboard.ken.wiki_layout import _format_footer, _format_sidebar_nav, _wrap_html


def _split_frontmatter(md_text: str) -> tuple[dict[str, Any], str]:
    r"""Strip a leading ``---\n…\n---`` block; return ``(meta, body)``.

    Returns ``({}, md_text)`` when there is no frontmatter. Used by ``_build_html_plan``
    to detect per-task detail pages (#376f) and lift their metadata into the
    ``.fullscreen-card`` template.
    """
    if not md_text.startswith("---"):
        return {}, md_text
    lines = md_text.splitlines()
    end = next(
        (i for i, ln in enumerate(lines[1:], start=1) if ln.strip() == "---"),
        None,
    )
    if end is None:
        return {}, md_text
    import yaml

    try:
        data = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError:
        return {}, md_text
    if not isinstance(data, dict):
        return {}, md_text
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return data, body


def _extract_title(md_text: str) -> str:
    """Pull the first ``# heading`` line out of an MD blob to use as the ``<title>``."""
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "kenboard wiki"


def _sidebar_section_key(rel: Path, meta: dict[str, Any]) -> str:
    """Compute the sidebar "current"-highlight key for the page ``rel`` (#742, #856).

    Section dir for index/detail pages, ``log/<date>`` for a daily journal page, the
    bare posix filename for any other MD, ``""`` for root. ``as_posix()`` keeps it
    matching the ``/``-joined section paths on every OS.
    """
    if rel.name == "index.md" or meta:
        key = rel.parent.as_posix()
    elif rel.parent.as_posix() == "log":
        key = rel.with_suffix("").as_posix()
    else:
        key = rel.as_posix()
    return "" if key == "." else key


def _build_html_plan(in_dir: Path, sections: list) -> list[dict[str, str]]:
    """Walk ``in_dir`` and return the ``[{path, content}]`` HTML plan.

    Covers every ``.md`` file under the tree. Detail pages (any MD with a YAML
    frontmatter block — written by ``_format_task_detail_md`` since #376f) get the
    ``.fullscreen-card`` layout mirroring the kenboard board's full-screen task view;
    everything else gets the plain Markdown layout.
    """
    files: list[dict[str, str]] = []
    # #742 — discover daily log pages so the sidebar can list them as a
    # "Journal" group. Newest first (reverse-alpha = reverse-chrono for ISO).
    log_dir = in_dir / "log"
    daily_dates = (
        sorted(
            (p.stem for p in log_dir.glob("*.md") if p.stem != "index"),
            reverse=True,
        )
        if log_dir.is_dir()
        else []
    )
    # #999/#1014 — per-task stamp only; no build time, no version (both churn).
    for md_path in sorted(in_dir.rglob("*.md")):
        rel = md_path.relative_to(in_dir)
        # Always derive path strings from ``as_posix()`` (not ``str(rel)``): on
        # Windows ``str`` yields backslashes, which zeroes the depth/relpath
        # computation in the sidebar and breaks every internal link (#856).
        rel_posix = rel.as_posix()
        md_text = md_path.read_text(encoding="utf-8")
        meta, body_md = _split_frontmatter(md_text)
        section_key = _sidebar_section_key(rel, meta)
        sidebar = _format_sidebar_nav(sections, rel_posix, section_key, daily_dates)
        if meta and "id" in meta:
            page_title = f"#{meta.get('id')} — {meta.get('title') or 'task'}"
            body_html = _render_task_detail(meta, body_md)
            footer_html = _format_footer(meta.get("updated_at"))
        else:
            page_title = _extract_title(md_text)
            body_html = _rewrite_md_links_to_html(_render_markdown(md_text))
            footer_html = ""
        html = _wrap_html(page_title, body_html, sidebar, footer_html)
        files.append({"path": rel.with_suffix(".html").as_posix(), "content": html})
    return files


def _write_html_plan(out: str, files: list[dict[str, str]]) -> None:
    """Idempotently materialise the HTML tree (clean + re-write)."""
    base = Path(out)
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    for f in files:
        target = base / f["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f["content"], encoding="utf-8")


@wiki.command(name="build", help="Render the wiki MD tree as standalone HTML.")
@click.option(
    "--in",
    "in_dir",
    default=None,
    help=(
        "Input directory holding the MD tree. Resolves to: flag > KEN_WIKI_DIR "
        "env > `wiki_dir=` in .ken > ./wiki (#479)."
    ),
)
@click.option(
    "--out",
    default=None,
    help=(
        "Output directory — re-written from scratch each run. Resolves to: "
        "flag > KEN_WIKI_HTML_DIR env > `wiki_html_dir=` in .ken > "
        "./wiki-html (#479)."
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
@click.pass_context
def wiki_build(
    ctx: click.Context,
    in_dir: str | None,
    out: str | None,
    architecture: str | None,
) -> None:
    """Build the HTML wiki from the MD tree produced by ``ken wiki sync``.

    Raises:
        UsageError: when ``--in`` doesn't exist or ``ARCHITECTURE.md`` is missing.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    architecture = architecture or cfg.architecture
    in_dir = in_dir or cfg.wiki_dir
    out = out or cfg.wiki_html_dir
    src = Path(in_dir)
    if not src.is_dir():
        msg = (
            f"Input directory '{in_dir}' does not exist. "
            "Run `ken wiki sync` first to generate the MD tree."
        )
        raise click.UsageError(msg)
    sections, paths = _load_sections(architecture)
    if not paths:
        raise click.UsageError(_architecture_help(architecture))
    files = _build_html_plan(src, sections)
    _write_html_plan(out, files)
    click.echo(f"Wrote {len(files)} HTML file(s) under {out}/.")

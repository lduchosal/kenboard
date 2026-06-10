"""``ken wiki build`` — render the wiki MD tree as standalone HTML.

Wraps every page in the standard layout (sidebar + main + build footer) and renders per-
task detail pages with the ``.fullscreen-card`` layout mirroring the board's full-screen
task view (#376f, #741, #742, #743).
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from dashboard.ken.config import KenConfig, _version
from dashboard.ken.wiki import _architecture_help, _load_sections, wiki
from dashboard.ken.wiki_css import _WIKI_HTML_CSS
from dashboard.ken.wiki_detail import (
    _render_markdown,
    _render_task_detail,
    _rewrite_md_links_to_html,
)


# Stable per-name avatar colour — picked from a small palette so the
# detail page renders the same swatch as the board card. Mirrors
# ``buildAvatar`` in ``static/js/tasks.js`` at a high level (palette
# differs in length but the deterministic hash keeps it consistent
# per identity).
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


def _format_sidebar_nav(
    sections: list,
    current_file: str,
    current_section: str | None,
    daily_dates: list[str] | None = None,
) -> str:
    """Render the per-page sidebar nav, marking the current page with ``class=current``.

    ``current_file`` is the rendered page's path relative to the wiki root
    (e.g. ``"index.md"``, ``"docs/index.md"``, ``"log/2026-06-04.md"``,
    ``"backend/api/foo.md"``). Its ``count("/")`` gives the on-disk depth
    used to prefix every href with the right number of ``../`` so links work
    when the wiki is browsed via ``file://`` (#741).

    ``current_section`` is matched against the section path to highlight the
    active entry: ``""`` for the root index, ``"<section>"`` for
    section/task pages, ``"log"`` for the journal index, ``"log/<date>"``
    for a daily page, ``None`` to suppress the Home link.

    ``daily_dates`` (#742) is the list of dates with a daily log page,
    newest first. When non-empty, a "Journal" group is appended after the
    architecture tree, with one sub-entry per date.
    """
    up = "../" * current_file.count("/")
    lines = ['<nav class="sidebar"><h1>kenboard wiki</h1><ul>']
    if current_section is not None:
        root_cls = ' class="current"' if current_section == "" else ""
        lines.append(f'<li><a href="{up}index.html"{root_cls}>Home</a></li>')
    for section in sections:
        for path, node in section.flatten():
            indent_style = f"padding-left:{path.count('/') * 12}px"
            href = f"{up}{path}/index.html"
            cls = ' class="current"' if path == current_section else ""
            lines.append(
                f'<li style="{indent_style}"><a href="{href}"{cls}>{node.title}</a></li>',
            )
    if daily_dates:
        log_cls = ' class="current"' if current_section == "log" else ""
        lines.append(
            f'<li style="padding-left:0px">'
            f'<a href="{up}log/index.html"{log_cls}>Journal</a></li>',
        )
        for date in daily_dates:
            day_cls = ' class="current"' if current_section == f"log/{date}" else ""
            lines.append(
                f'<li style="padding-left:12px">'
                f'<a href="{up}log/{date}.html"{day_cls}>{date}</a></li>',
            )
    lines.append("</ul></nav>")
    return "".join(lines)


def _format_footer(version: str, generated_at: datetime) -> str:
    """Render the build footer shown at the bottom of every wiki page (#743).

    The footer carries the version of ``ken`` (= kenboard) and the build timestamp so a
    reader can tell at a glance how fresh the rendered HTML is and which release
    produced it. UTC is used to stay portable across machines that publish the wiki.
    """
    stamp = generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f'<footer class="wiki-footer">'
        f"Généré le {stamp} par kenboard {version}"
        f"</footer>"
    )


def _wrap_html(
    title: str, body_html: str, sidebar_html: str, footer_html: str = ""
) -> str:
    """Wrap a rendered body with the standard layout (head + sidebar + main).

    ``footer_html`` is appended inside ``<main>`` after the body so it sits at the
    bottom of the content column on every page (#743). Optional for callers that don't
    care (defaults to empty), but ``_build_html_plan`` always passes a non-empty value.
    """
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{title} — kenboard wiki</title>"
        f"<style>{_WIKI_HTML_CSS}</style>"
        '</head><body><div class="layout">'
        f"{sidebar_html}"
        f"<main>{body_html}{footer_html}</main>"
        "</div></body></html>"
    )


def _extract_title(md_text: str) -> str:
    """Pull the first ``# heading`` line out of an MD blob to use as the ``<title>``."""
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "kenboard wiki"


def _build_html_plan(in_dir: Path, sections: list) -> list[dict[str, str]]:
    """Walk every ``.md`` under ``in_dir`` and return ``[{path, content}]`` for HTML
    output.

    Detail pages (any MD with a YAML frontmatter block — written by
    ``_format_task_detail_md`` since #376f) get the ``.fullscreen-card`` layout
    mirroring the kenboard board's full-screen task view; everything else gets the plain
    Markdown layout.
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
    # #743 — build footer computed once and embedded on every page.
    footer_html = _format_footer(_version(), datetime.now(UTC))
    for md_path in sorted(in_dir.rglob("*.md")):
        rel = md_path.relative_to(in_dir)
        md_text = md_path.read_text(encoding="utf-8")
        meta, body_md = _split_frontmatter(md_text)
        # Sidebar "current" key: section directory for index/detail pages,
        # ``log/<date>`` for a daily journal page so the sidebar entry lights
        # up (#742), else the bare filename for any other free-standing MD.
        if rel.name == "index.md" or meta:
            section_key = str(rel.parent)
        elif str(rel.parent) == "log":
            section_key = str(rel.with_suffix(""))
        else:
            section_key = str(rel)
        if section_key == ".":
            section_key = ""
        sidebar = _format_sidebar_nav(sections, str(rel), section_key, daily_dates)
        if meta and "id" in meta:
            page_title = f"#{meta.get('id')} — {meta.get('title') or 'task'}"
            body_html = _render_task_detail(meta, body_md)
        else:
            page_title = _extract_title(md_text)
            body_html = _rewrite_md_links_to_html(_render_markdown(md_text))
        html = _wrap_html(page_title, body_html, sidebar, footer_html)
        files.append({"path": str(rel.with_suffix(".html")), "content": html})
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

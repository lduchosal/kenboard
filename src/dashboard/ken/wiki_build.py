"""``ken wiki build`` — render the wiki MD tree as standalone HTML.

Wraps every page in the standard layout (sidebar + main + build footer) and renders per-
task detail pages with the ``.fullscreen-card`` layout mirroring the board's full-screen
task view (#376f, #741, #742, #743).
"""

from __future__ import annotations

import posixpath
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


def _rel_href(target: str, page_dir: str) -> str:
    """Return ``target`` (wiki-root-relative posix path) relative to ``page_dir``.

    Links computed relative to the page's directory stay valid at any depth and
    under any mount point — ``file://``, ``/``, or ``/wiki/`` (#856). Both args use
    ``/`` on every OS, so callers must pass ``Path.as_posix()`` (not ``str(Path)``,
    which yields backslashes on Windows and breaks the computation).
    """
    return posixpath.relpath(target, page_dir or ".")


def _format_journal_nav(
    daily_dates: list[str], current_section: str | None, page_dir: str
) -> list[str]:
    """Render the "Journal" sidebar group: index link + one entry per date (#742).

    Hrefs are computed relative to ``page_dir`` via :func:`_rel_href` so the group
    resolves at any nesting depth and under any mount point (#856).
    """
    log_cls = ' class="current"' if current_section == "log" else ""
    log_href = _rel_href("log/index.html", page_dir)
    out = [
        f'<li style="padding-left:0px"><a href="{log_href}"{log_cls}>Journal</a></li>',
    ]
    for date in daily_dates:
        day_cls = ' class="current"' if current_section == f"log/{date}" else ""
        day_href = _rel_href(f"log/{date}.html", page_dir)
        out.append(
            f'<li style="padding-left:12px">'
            f'<a href="{day_href}"{day_cls}>{date}</a></li>',
        )
    return out


def _format_sidebar_nav(
    sections: list,
    current_file: str,
    current_section: str | None,
    daily_dates: list[str] | None = None,
) -> str:
    """Render the per-page sidebar nav, marking the current page with ``class=current``.

    ``current_file`` is the page's path relative to the wiki root, ``/``-separated
    (e.g. ``"backend/api/foo.md"``). Every href is rewritten relative to its
    directory via :func:`_rel_href`, so links resolve at any depth and mount point
    (#856, supersedes the ``../``-prefix scheme of #741).

    ``current_section`` selects the highlighted entry: ``""`` for the root index,
    ``"<section>"`` for section/task pages, ``"log"`` / ``"log/<date>"`` for the
    journal, ``None`` to suppress the Home link. ``daily_dates`` (#742), newest
    first, appends a "Journal" group when non-empty.
    """
    page_dir = posixpath.dirname(current_file)
    lines = ['<nav class="sidebar"><h1>kenboard wiki</h1><ul>']
    if current_section is not None:
        root_cls = ' class="current"' if current_section == "" else ""
        home = _rel_href("index.html", page_dir)
        lines.append(f'<li><a href="{home}"{root_cls}>Home</a></li>')
    for section in sections:
        for path, node in section.flatten():
            indent_style = f"padding-left:{path.count('/') * 12}px"
            href = _rel_href(f"{path}/index.html", page_dir)
            cls = ' class="current"' if path == current_section else ""
            lines.append(
                f'<li style="{indent_style}"><a href="{href}"{cls}>{node.title}</a></li>',
            )
    if daily_dates:
        lines.extend(_format_journal_nav(daily_dates, current_section, page_dir))
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


def _sidebar_section_key(rel: Path, meta: dict[str, Any]) -> str:
    """Compute the sidebar "current"-highlight key for the page ``rel`` (#742, #856).

    Section dir for index/detail pages, ``log/<date>`` for a daily journal page,
    the bare posix filename for any other MD, ``""`` for root. ``as_posix()`` keeps
    it matching the ``/``-joined section paths on every OS.
    """
    if rel.name == "index.md" or meta:
        key = rel.parent.as_posix()
    elif rel.parent.as_posix() == "log":
        key = rel.with_suffix("").as_posix()
    else:
        key = rel.as_posix()
    return "" if key == "." else key


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
        else:
            page_title = _extract_title(md_text)
            body_html = _rewrite_md_links_to_html(_render_markdown(md_text))
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

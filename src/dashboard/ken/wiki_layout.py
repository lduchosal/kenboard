"""HTML chrome shared by every wiki page: sidebar nav, footer, page shell.

Split out of ``wiki_build`` (#1017), which was pinned at the ``max_file_lines`` ceiling.
Presentation layer, sibling of ``wiki_css``: pure string builders with no IO and no
click, so ``wiki_build`` keeps only the walk-the-tree / write-the-plan orchestration.
"""

from __future__ import annotations

import posixpath
from datetime import datetime

from dashboard.ken.wiki_css import _WIKI_HTML_CSS


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

    ``current_file`` is the page's path relative to the wiki root, ``/``-separated (e.g.
    ``"backend/api/foo.md"``). Every href is rewritten relative to its directory via
    :func:`_rel_href`, so links resolve at any depth and mount point (#856, supersedes
    the ``../``-prefix scheme of #741).

    ``current_section`` selects the highlighted entry: ``""`` for the root index,
    ``"<section>"`` for section/task pages, ``"log"`` / ``"log/<date>"`` for the
    journal, ``None`` to suppress the Home link. ``daily_dates`` (#742), newest first,
    appends a "Journal" group when non-empty.
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


def _format_footer(updated_at: datetime | str | None = None) -> str:
    """Render a page's footer: the task's last-modified stamp (#743, #999, #1014).

    ``updated_at`` is the frontmatter datetime (or ISO string); pages with no backing
    task get ``""`` — no footer at all. Carries neither the build time (#999) nor the
    ``ken`` version (#1014): both are page-independent, so either one rewrites the whole
    committed HTML tree on every release. Only per-task data belongs here.
    """
    if isinstance(updated_at, datetime):
        stamp = updated_at.strftime("%Y-%m-%d %H:%M:%S")
    else:
        stamp = str(updated_at or "").replace("T", " ")
    return f'<footer class="wiki-footer">Modifié le {stamp}</footer>' if stamp else ""


def _wrap_html(
    title: str, body_html: str, sidebar_html: str, footer_html: str = ""
) -> str:
    """Wrap a rendered body with the standard layout (head + sidebar + main).

    ``footer_html`` is appended inside ``<main>`` after the body so it sits at the
    bottom of the content column (#743). Empty on pages with no per-task stamp — index
    and journal pages render no footer at all (#1014).
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

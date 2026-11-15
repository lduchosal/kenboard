"""Per-task detail page rendering for ``ken wiki build`` (#376f).

Split out of ``ken/wiki_build.py`` (ken #808): the ``.fullscreen-card`` HTML layout
mirroring the board's full-screen task view, plus the avatar palette shared with
``static/js/tasks.js`` at a high level.
"""

from __future__ import annotations

import re
from html import escape
from typing import Any

from dashboard.ken.wiki_sanitize import sanitize_html


def _render_markdown(md_text: str) -> str:
    """Convert a markdown string to sanitised HTML.

    The ``markdown`` library passes raw HTML through untouched and puts no restriction
    on link targets, so its output goes through the allowlist sanitizer (#1186).
    """
    import markdown as md_lib

    return sanitize_html(md_lib.markdown(md_text, extensions=["fenced_code", "tables"]))


def _rewrite_md_links_to_html(html: str) -> str:
    """Rewrite ``href="…/index.md"`` (and ``foo.md``) to ``.html`` in rendered HTML."""
    return re.sub(r'href="([^"]+)\.md"', r'href="\1.html"', html)


# Length of an ISO ``YYYY-MM-DD`` date prefix.
_ISO_DATE_LEN = 10
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

_AVATAR_PALETTE = (
    "#0969da",
    "#bf3989",
    "#1a7f37",
    "#9a6700",
    "#cf222e",
    "#8250df",
    "#0a3069",
    "#bc4c00",
)


def _log_day(classified_at: str) -> str:
    """Journal page of a task (#742): the ISO day it was classified, or ``unknown``."""
    day = classified_at[:_ISO_DATE_LEN]
    return day if _ISO_DATE_RE.fullmatch(day) else "unknown"


def _text(value: object) -> str:
    """Render a frontmatter value as an escaped HTML text node (``None`` → empty)."""
    return escape(str(value or ""), quote=False)


def _avatar_color(name: str) -> str:
    """Deterministically map a name to one of ``_AVATAR_PALETTE``."""
    if not name:
        return _AVATAR_PALETTE[0]
    return _AVATAR_PALETTE[sum(ord(c) for c in name) % len(_AVATAR_PALETTE)]


def _render_task_detail(meta: dict[str, Any], body_md: str) -> str:
    """Render a per-task detail page as ``.fullscreen-card`` HTML (#376f).

    ``meta`` comes from the page's YAML frontmatter (set by ``_format_task_detail_md``).
    ``body_md`` is the description body — the H1 / footer-nav written by sync are
    stripped server-side here since the fullscreen template renders its own header.
    """
    # Frontmatter values are task data (free text typed by any writer): escape
    # every one of them before it lands in the page (#1186).
    status = _text(meta.get("status"))
    who = _text(meta.get("who"))
    due = _text(meta.get("due_date"))
    classified_at = _text(meta.get("classified_at"))
    classified_by = _text(meta.get("classified_by"))
    section = _text(meta.get("section"))
    raw_who = str(meta.get("who") or "")
    avatar_initial = escape((raw_who[:1] or "?").upper(), quote=False)
    avatar_color = _avatar_color(raw_who)
    meta_parts = [
        f'<div class="task-avatar" style="background:{avatar_color}">{avatar_initial}</div>',
        f'<span class="fs-who">{who}</span>' if who else "",
        f"<span>Due {due}</span>" if due else "",
        f"<span>Classified {classified_at[:10]}</span>" if classified_at else "",
        f"<span>by {classified_by}</span>" if classified_by else "",
    ]
    desc_md = _strip_detail_chrome(body_md)
    desc_html = _rewrite_md_links_to_html(_render_markdown(desc_md))
    log_href = "../" * (section.count("/") + 1) + f"log/{_log_day(classified_at)}.html"
    section_label = section or "section"
    status_cls = f"status-{status}" if re.fullmatch(r"[a-z]+", status) else ""
    return (
        '<div class="fullscreen-card">'
        '<div class="fullscreen-header">'
        f'<span class="fullscreen-id">#{_text(meta.get("id"))}</span>'
        f'<span class="fullscreen-status {status_cls}">{status}</span>'
        "</div>"
        f'<h2 class="fullscreen-title">{_text(meta.get("title"))}</h2>'
        '<div class="fullscreen-meta">' + "".join(p for p in meta_parts if p) + "</div>"
        f'<div class="fullscreen-desc">{desc_html}</div>'
        '<div class="wiki-nav">'
        f'<a href="index.html">← retour à {section_label}</a> · '
        f'<a href="{log_href}">voir log</a>'
        "</div>"
        "</div>"
    )


def _strip_detail_chrome(body_md: str) -> str:
    """Drop the ``# #ID — title`` header and footer nav from a detail body.

    The HTML layout supplies its own header (``fullscreen-title``) and footer (``wiki-
    nav``) so we don't want them duplicated when rendering the body.
    """
    lines = body_md.splitlines()
    if lines and lines[0].startswith("# #"):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    # Drop the trailing footer nav (an ``---`` separator + a one-line
    # ``[← retour …](…) · [voir log](…)``). It's the last non-empty block.
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and lines[-1].startswith("[← retour"):
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
        if lines and lines[-1].strip() == "---":
            lines.pop()
    return "\n".join(lines)

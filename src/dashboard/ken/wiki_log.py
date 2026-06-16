"""Journal d'exploitation + orphans pages of the wiki MD tree (#742, #376e).

Split out of ``ken/wiki_sync.py`` (ken #808): one page per classification day, an index
(newest first), and the orphan-sections report.
"""

from __future__ import annotations

from typing import Any

from dashboard.ken.wiki import _task_filename

# Length of an ISO ``YYYY-MM-DD`` date prefix.
_ISO_DATE_LEN = 10

# Statuses treated as "archived" — their status carries no signal once a task
# reaches them, so it is hidden in listings. Single source of truth, also
# imported by ``wiki_sync`` (#857).
_ARCHIVED_STATUSES = frozenset({"done"})


def _classified_date(row: dict[str, Any]) -> str:
    """Extract the ISO date (``YYYY-MM-DD``) prefix from a classification row (#742).

    Falls back to ``"unknown"`` if ``classified_at`` is missing or malformed so a
    corrupt row doesn't lose its tasks — they end up in a single catch-all daily page
    operators can investigate.
    """
    raw = str(row.get("classified_at") or "")
    return raw[:_ISO_DATE_LEN] if len(raw) >= _ISO_DATE_LEN else "unknown"


def _format_log_index_md(by_date: dict[str, list[dict[str, Any]]]) -> str:
    """Render ``log/index.md`` — list of daily pages, newest first (#742).

    ISO date filenames mean reverse-alphabetical = reverse-chronological,
    so a directory listing is already sorted correctly. The index just
    materialises the same order for human readers.
    """
    lines = [
        "# Journal d'exploitation",
        "",
        "Une page par jour, du plus récent au plus ancien. "
        "Chaque page liste les tâches classées ce jour-là.",
        "",
    ]
    if not by_date:
        lines.append("_Aucune classification enregistrée pour l'instant._")
        return "\n".join(lines) + "\n"
    for date in sorted(by_date.keys(), reverse=True):
        count = len(by_date[date])
        lines.append(f"- [{date}]({date}.md) — {count} task(s)")
    return "\n".join(lines) + "\n"


def _format_log_day_md(date: str, tasks: list[dict[str, Any]]) -> str:
    """Render ``log/<date>.md`` — one day's classifications (#742, #857).

    Tasks are sorted by id for stable output. Each line links to the task's detail page
    (``../<section>/<slug>-<id>.md``); ``_rewrite_md_links_to_html`` converts the
    ``.md`` suffix at build time.

    Each row is trimmed to signal (#857): the title link plus its section. The
    ``classified_by`` actor is dropped (an opaque ``key:…:user:…`` token with no reader
    value, mirroring the section index which omits ``who``), and ``status`` is shown
    only when it still carries information — hidden once the task is archived
    (``done``), the dominant case on a journal page.
    """
    lines = [f"# {date}", "", f"{len(tasks)} task(s) classée(s) ce jour.", ""]
    for t in sorted(tasks, key=lambda r: int(r["task_id"])):
        title = t.get("title") or ""
        section = t.get("section_path") or "?"
        status = t.get("status") or ""
        task_file = _task_filename({"task_id": t["task_id"], "title": title})
        # log/<date>.md → ../<section>/<task>.md to reach the detail page.
        link = f"../{section}/{task_file}"
        line = f"- [#{t['task_id']} {title}]({link}) — `{section}`"
        if status and status not in _ARCHIVED_STATUSES:
            line += f" — _{status}_"
        lines.append(line)
    return "\n".join(lines) + "\n"


def _format_orphans_md(orphans: dict[str, list[dict[str, Any]]]) -> str:
    """Render ``orphans.md`` — classifications pointing to undeclared sections."""
    lines = [
        "# Orphan classifications",
        "",
        "These section paths are referenced by tasks but **not** declared in "
        "``ARCHITECTURE.md``. Re-classify the tasks or add the section.",
        "",
    ]
    for path, tasks in sorted(orphans.items()):
        lines.extend((f"## `{path}` — {len(tasks)} task(s)", ""))
        for t in sorted(tasks, key=lambda x: int(x["task_id"])):
            title = t.get("title") or ""
            lines.append(f"- #{t['task_id']} {title}")
        lines.append("")
    return "\n".join(lines) + "\n"

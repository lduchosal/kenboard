"""Text and markdown rendering helpers for the ``ken`` CLI.

Covers the aligned-column table output shared by most commands and the per-task markdown
files written by ``ken sync``.
"""

from __future__ import annotations

import json as json_lib
import re
from typing import Any

import click

# Filenames written by ``ken sync`` look like ``0042 - Title.md``.
_SYNC_FILENAME_RE = re.compile(r"^(\d+) - .+\.md$")
# Characters that are illegal (or risky) in filenames on common file systems.
_SYNC_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _format_columns(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    """Format rows as aligned columns."""
    if not rows:
        return "(no rows)"
    headers = [h for h, _ in columns]
    keys = [k for _, k in columns]
    cells: list[list[str]] = [headers]
    cells.extend(
        [str(row.get(k)) if row.get(k) not in (None, "") else "--" for k in keys]
        for row in rows
    )
    widths = [max(len(line[i]) for line in cells) for i in range(len(headers))]
    return "\n".join(
        "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(line))
        for line in cells
    )


def _output(
    data: Any,  # noqa: ANN401 — payload JSON arbitraire de l'API
    *,
    json_mode: bool,
    columns: list[tuple[str, str]] | None = None,
) -> None:
    """Print ``data`` as JSON or as an aligned column table."""
    if json_mode or columns is None:
        click.echo(json_lib.dumps(data, indent=2, default=str))
        return
    rows = data if isinstance(data, list) else [data]
    click.echo(_format_columns(rows, columns))


def _sanitize_filename(title: str) -> str:
    r"""Replace filesystem-invalid characters in a task title.

    Strips ``/ \ : * ? " < > |`` and control characters, collapses whitespace runs, and
    trims trailing dots/spaces (which Windows rejects). Returns ``"untitled"`` if
    nothing usable is left.
    """
    cleaned = " ".join(_SYNC_INVALID_CHARS.sub("_", title).split()).rstrip(". ")
    return cleaned or "untitled"


def _sync_filename(task: dict[str, Any]) -> str:
    """Build the on-disk filename for a synced task (``NNNN - Title.md``)."""
    return f"{int(task['id']):04d} - {_sanitize_filename(task.get('title') or '')}.md"


def _format_sync_markdown(task: dict[str, Any]) -> str:
    """Render a task as markdown with a YAML frontmatter header.

    The frontmatter holds the structured fields (id, status, who, dates, position) so
    the body stays focused on the human-authored title and description. ``None`` values
    render as empty strings to keep the frontmatter parseable.
    """
    fields = (
        "id",
        "status",
        "who",
        "due_date",
        "position",
        "created_at",
        "updated_at",
    )
    lines = ["---"]
    for field in fields:
        value = task.get(field)
        lines.append(f"{field}: {value if value is not None else ''}")
    lines.extend(
        (
            "---",
            "",
            f"# {task.get('title') or ''}",
            "",
            task.get("description") or "",
            "",
        )
    )
    return "\n".join(lines)

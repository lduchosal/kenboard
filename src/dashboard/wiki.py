"""Wiki support module (#376).

Implements the LLM Wiki pattern proposed by Karpathy:
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

The wiki is a structured MD tree exported from the kanban tasks, organized
according to a project-owned ``ARCHITECTURE.md`` schema. This module
provides the schema parser + data shapes shared by ``ken wiki groom``,
``ken wiki sync``, ``ken wiki build``, and ``ken wiki lint``.

This file ships the **foundations** (chunk A of #376): parsing
``ARCHITECTURE.md``, surfacing the section list to callers, with typed
data shapes the later chunks consume. The CLI commands and the export /
render / lint operations land in subsequent chunks (B-E).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Section:
    """A single wiki section declared in ``ARCHITECTURE.md`` frontmatter."""

    id: str
    title: str
    description: str = ""
    sub: list[Section] = field(default_factory=list)

    def flatten(self, prefix: str = "") -> list[tuple[str, Section]]:
        """Walk the tree and yield (path, section) pairs.

        ``path`` joins parent ids with ``/``, e.g. ``backend/api``. The result is in
        declaration order so callers can render a stable sidebar / index.
        """
        path = f"{prefix}/{self.id}" if prefix else self.id
        out: list[tuple[str, Section]] = [(path, self)]
        for child in self.sub:
            out.extend(child.flatten(path))
        return out


def _frontmatter(text: str) -> str:
    """Extract the YAML frontmatter block (between ``---`` markers).

    Returns the raw YAML string, or an empty string when no frontmatter is present. The
    first ``---`` must be the very first line (per the Jekyll / MkDocs convention).
    """
    if not text.startswith("---"):
        return ""
    lines = text.splitlines()
    if not lines:
        return ""
    end = next(
        (i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if end is None:
        return ""
    return "\n".join(lines[1:end])


def _build_section(node: dict) -> Section | None:
    """Convert a YAML dict into a ``Section``; skip nodes missing ``id``."""
    if not isinstance(node, dict):
        return None
    section_id = node.get("id")
    if not section_id:
        return None
    title = node.get("title") or section_id
    description = node.get("description") or ""
    raw_children = node.get("sub") or []
    children: list[Section] = []
    if isinstance(raw_children, list):
        for raw in raw_children:
            child = _build_section(raw)
            if child is not None:
                children.append(child)
    return Section(
        id=str(section_id),
        title=str(title),
        description=str(description),
        sub=children,
    )


def parse_architecture(path: str | Path) -> list[Section]:
    """Parse ``ARCHITECTURE.md`` and return the declared wiki sections.

    Expected frontmatter shape::

        ---
        wiki:
          sections:
            - id: backend
              title: Backend
              sub:
                - id: api
                  title: REST API
        ---

    Returns an empty list when the file is missing, has no frontmatter,
    or the frontmatter has no ``wiki.sections`` key. Malformed YAML
    raises ``yaml.YAMLError`` so callers can surface a usable error.
    """
    target = Path(path)
    if not target.is_file():
        return []
    text = target.read_text(encoding="utf-8")
    fm_text = _frontmatter(text)
    if not fm_text:
        return []
    parsed = yaml.safe_load(fm_text) or {}
    if not isinstance(parsed, dict):
        return []
    wiki = parsed.get("wiki") or {}
    raw_sections = wiki.get("sections") if isinstance(wiki, dict) else None
    if not isinstance(raw_sections, list):
        return []
    sections: list[Section] = []
    for raw in raw_sections:
        section = _build_section(raw)
        if section is not None:
            sections.append(section)
    return sections


def section_paths(sections: list[Section]) -> list[str]:
    """Return every section path declared in ``sections``, depth-first.

    Used by ``ken wiki groom`` to validate that an agent-supplied path (e.g.
    ``backend/api``) actually exists in the schema.
    """
    paths: list[str] = []
    for section in sections:
        for path, _node in section.flatten():
            paths.append(path)
    return paths

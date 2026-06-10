"""``ken wiki`` group and grooming (task → section classification).

Holds the ``wiki`` Click group the other wiki subcommands register on, the ``groom``
command (agent-driven classification, #376), and the shared section/slug helpers used by
``wiki sync`` and ``wiki build``.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from dashboard.ken.cli import cli


@cli.group()
def wiki() -> None:
    """Wiki commands — see ``ken wiki groom --help`` for the LLM Wiki pattern."""


def _load_sections(architecture: str) -> tuple[list, list[str]]:
    """Parse ARCHITECTURE.md and return ``(sections, valid_paths)``."""
    from dashboard.wiki import parse_architecture, section_paths

    sections = parse_architecture(architecture)
    return sections, section_paths(sections)


def _architecture_help(architecture: str) -> str:
    """Compose the user-facing help when ``architecture`` can't yield sections (#472).

    Distinguishes the two failure modes (file missing vs file present but no
    ``wiki.sections`` block) and shows the operator both fix paths: create the file at
    the expected location, or repoint the CLI via ``architecture=`` in ``.ken``.
    """
    target = Path(architecture)
    yaml_example = (
        "---\n"
        "wiki:\n"
        "  sections:\n"
        "    - id: backend\n"
        "      title: Backend\n"
        "    - id: frontend\n"
        "      title: Frontend\n"
        "---\n"
    )
    if not target.is_file():
        return (
            f"ARCHITECTURE file not found: {architecture}\n"
            "\n"
            "Two fixes:\n"
            f"  (a) Create {architecture} with this YAML frontmatter:\n"
            "\n"
            + "\n".join(f"      {line}" for line in yaml_example.splitlines())
            + "\n\n"
            "  (b) Or point ken at the existing file via .ken:\n"
            "\n"
            "      echo 'architecture=path/to/Architecture.md' >> .ken\n"
            "      (or export KEN_ARCHITECTURE=path/to/Architecture.md)\n"
        )
    return (
        f"{architecture} exists but declares no wiki sections.\n"
        "\n"
        "Add a `wiki.sections` block to its YAML frontmatter, for example:\n"
        "\n" + "\n".join(f"  {line}" for line in yaml_example.splitlines()) + "\n"
        "See `ken wiki groom --help` for the LLM Wiki pattern."
    )


def _section_title_for(sections: list, path: str) -> str:
    """Look up a section by its flat path and return its title (or path)."""
    for section in sections:
        for p, node in section.flatten():
            if p == path:
                return node.title or path
    return path


# Inject the verbose help text after registration (Click can't easily
# accept a paragraph-styled docstring AND a one-line --help summary).


_SLUG_NONWORD_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """Lowercase ``text`` and collapse non-alphanumerics into dashes.

    Used to build the filename portion of a task detail page:
    ``<section>/<slug>-<id>.md`` (#376f). The id suffix breaks ties when two
    tasks share the same title.

    Diacritics are stripped but the underlying letter is kept (``é → e``,
    ``ô → o``, ``ç → c``) so titles like *mot de passe oublié* yield
    readable slugs (``mot-de-passe-oublie``) instead of dropping the
    accented letter entirely (``mot-de-passe-oubli``). NFD decomposes
    accented chars into base + combining marks; we filter the marks.
    """
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    slug = _SLUG_NONWORD_RE.sub("-", stripped.lower()).strip("-")
    return slug or "untitled"


def _task_filename(task: dict[str, Any]) -> str:
    """Return ``<slug>-<id>.md`` for the per-task detail page."""
    return f"{_slugify(str(task.get('title') or ''))}-{task['task_id']}.md"

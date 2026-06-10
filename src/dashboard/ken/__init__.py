"""Ken — task CLI for the kenboard board.

See ``doc/ken-cli.md`` for the full spec. Resolves config in this order: flags > env
vars (KEN_*) > .ken (secrets, gitignored) > ken.ini (versioned shared config) >
hardcoded defaults. Talks to the kenboard REST API via the stdlib (no extra HTTP
dependency).

The CLI is a package (#786): ``config`` (resolution), ``http`` (REST client),
``fmt`` (text/markdown rendering), ``cli`` (root group + lifecycle commands),
``tasks`` (board commands) and ``wiki``/``wiki_sync``/``wiki_build``/``wiki_lint``
(the wiki pipeline). Importing the package registers every command on ``cli``,
which stays the ``ken`` console entry point (``dashboard.ken:cli``).
"""

from __future__ import annotations

import io
import sys

# Windows uses cp1252 (or the system locale) for stdout/stderr by default.
# Characters like → or accented letters in task descriptions cause
# UnicodeEncodeError. Force UTF-8 so `ken` works plug-and-play without
# requiring PYTHONUTF8=1 in the environment (#148).
if sys.platform == "win32":  # pragma: no cover
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name)
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
        elif not isinstance(_stream, io.TextIOWrapper):
            setattr(
                sys,
                _stream_name,
                io.TextIOWrapper(_stream.buffer, encoding="utf-8", errors="replace"),
            )

# Importing the command modules registers them on the ``cli`` group —
# order matters: ``wiki`` defines the subgroup the wiki_* modules attach to.
from dashboard.ken import polish as _polish_module  # noqa: F401
from dashboard.ken import sync as _sync_module  # noqa: F401
from dashboard.ken import task_edit as _task_edit_module  # noqa: F401
from dashboard.ken import tasks as _tasks_module  # noqa: F401
from dashboard.ken import wiki as _wiki_module  # noqa: F401
from dashboard.ken import wiki_build as _wiki_build_module  # noqa: F401
from dashboard.ken import wiki_groom as _wiki_groom_module  # noqa: F401
from dashboard.ken import wiki_lint as _wiki_lint_module  # noqa: F401
from dashboard.ken import wiki_sync as _wiki_sync_module  # noqa: F401
from dashboard.ken.cli import cli

# Re-exports kept for back-compat: tests and external callers historically
# reached these helpers via the flat ``dashboard.ken`` module.
from dashboard.ken.config import (
    DEFAULT_BASE_URL,
    KenConfig,
    _load_config,
    _persist_sync_dir,
    _resolve_sync_dir,
)
from dashboard.ken.fmt import (
    _format_columns,
    _format_sync_markdown,
    _sanitize_filename,
    _sync_filename,
)
from dashboard.ken.http import _request
from dashboard.ken.wiki import _slugify, _task_filename
from dashboard.ken.wiki_build import _format_footer, _format_sidebar_nav, _wrap_html
from dashboard.ken.wiki_sync import (
    _classified_date,
    _format_log_day_md,
    _format_log_index_md,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "KenConfig",
    "_classified_date",
    "_format_columns",
    "_format_footer",
    "_format_log_day_md",
    "_format_log_index_md",
    "_format_sidebar_nav",
    "_format_sync_markdown",
    "_load_config",
    "_persist_sync_dir",
    "_request",
    "_resolve_sync_dir",
    "_sanitize_filename",
    "_slugify",
    "_sync_filename",
    "_task_filename",
    "_wrap_html",
    "cli",
]

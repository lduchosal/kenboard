"""Configuration resolution for the ``ken`` CLI.

Resolves config in this order: flags > env vars (KEN_*) > .ken (secrets, gitignored) >
ken.ini (versioned shared config) > hardcoded defaults. See ``doc/ken-cli.md`` for the
full spec (#778).
"""

from __future__ import annotations

import configparser
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import click


def _version() -> str:
    """Return the kenboard package version for the User-Agent header."""
    try:
        from dashboard import __version__
    except ImportError:
        return "unknown"
    else:
        return __version__


DEFAULT_BASE_URL = "http://localhost:9090"
DEFAULT_SYNC_DIR = "doc/kenboard"
DEFAULT_ARCHITECTURE = "ARCHITECTURE.md"
DEFAULT_WIKI_DIR = "wiki"
DEFAULT_WIKI_HTML_DIR = "wiki-html"
KEN_FILE = ".ken"
KEN_INI_FILE = "ken.ini"
KEN_INI_SECTION = "ken"
VALID_STATUSES = ("todo", "doing", "review", "done")
TASK_COLUMNS = [
    ("ID", "id"),
    ("STATUS", "status"),
    ("WHO", "who"),
    ("WHEN", "due_date"),
    ("TITLE", "title"),
]


@dataclass
class KenConfig:
    """Resolved CLI configuration, attached to the Click context."""

    project_id: str | None
    base_url: str
    api_token: str | None
    ken_file: Path | None
    ini_file: Path | None = None
    sync_dir: str = DEFAULT_SYNC_DIR
    architecture: str = DEFAULT_ARCHITECTURE
    wiki_dir: str = DEFAULT_WIKI_DIR
    wiki_html_dir: str = DEFAULT_WIKI_HTML_DIR
    description: str = ""


def _find_file_upwards(start: Path, name: str) -> Path | None:
    """Walk up from ``start`` looking for a file or dir named ``name``."""
    cur = start.resolve()
    while True:
        candidate = cur / name
        if candidate.exists():
            return candidate
        if cur.parent == cur:
            return None
        cur = cur.parent


def _parse_ken_file(path: Path) -> dict[str, str]:
    """Parse a ``.ken`` file (key=value lines, ``#`` comments allowed)."""
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def _parse_ini_file(path: Path) -> dict[str, str]:
    """Parse a ``ken.ini`` file (configparser, ``[ken]`` section).

    Unknown sections and keys are silently ignored so a future feature can add new
    sections without breaking older CLIs. Missing ``[ken]`` section returns ``{}``.
    """
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    if not parser.has_section(KEN_INI_SECTION):
        return {}
    return dict(parser.items(KEN_INI_SECTION))


def _check_ken_permissions(path: Path) -> None:
    """Warn on stderr if ``.ken`` is readable by group/other.

    Skipped on Windows where POSIX permission bits are meaningless —
    ``os.stat().st_mode`` always reports 0o666 and ``os.chmod(0o600)`` is a no-op.
    Windows relies on NTFS ACLs instead, and the user profile directory is already
    protected by default (#146).
    """
    if sys.platform == "win32":
        return
    try:
        mode = path.stat().st_mode & 0o777
    except OSError:
        return
    if mode & 0o077:
        click.echo(
            f"Warning: {path} has mode {mode:o}, expected 600 (user only). "
            f"It contains an API token — fix with: chmod 600 {path}",
            err=True,
        )


def _locate_config_files(
    config_override: str | None,
) -> tuple[Path | None, Path | None]:
    """Return ``(ken_path, ini_path)`` — explicit ``--config`` or upward search.

    When ``--config`` is passed it points to a single file, parsed according to its
    extension (``.ini`` → ini format, otherwise legacy ``.ken``).
    """
    if config_override:
        override = Path(config_override).resolve()
        if not override.is_file():
            click.echo(f"Error: config file not found: {config_override}", err=True)
            sys.exit(1)
        if override.suffix == ".ini":
            return None, override
        return override, None
    return (
        _find_file_upwards(Path.cwd(), KEN_FILE),
        _find_file_upwards(Path.cwd(), KEN_INI_FILE),
    )


def _pick_value(
    key: str,
    env: str | None,
    file_data: dict[str, str],
    ini_data: dict[str, str],
) -> str | None:
    """Resolve ``key`` along env > .ken > ken.ini (defaults handled by caller)."""
    if env and (val := os.environ.get(env)):
        return val
    return file_data.get(key) or ini_data.get(key) or None


def _resolved_fields(
    file_data: dict[str, str], ini_data: dict[str, str]
) -> dict[str, str | None]:
    """Resolve every configurable key along env > .ken > ken.ini.

    #473: ``architecture`` is the default path of the ``ken wiki *`` subcommands (UTF-8
    preserved end-to-end). #479: ``wiki_dir`` / ``wiki_html_dir`` are the per-project
    output dirs of the pipeline.
    """
    keys = (
        ("project_id", "KEN_PROJECT_ID"),
        ("base_url", "KEN_BASE_URL"),
        ("api_token", "KEN_API_TOKEN"),
        ("sync_dir", "KEN_SYNC_DIR"),
        ("architecture", "KEN_ARCHITECTURE"),
        ("wiki_dir", "KEN_WIKI_DIR"),
        ("wiki_html_dir", "KEN_WIKI_HTML_DIR"),
    )
    fields: dict[str, str | None] = {
        key: _pick_value(key, env, file_data, ini_data) for key, env in keys
    }
    fields["description"] = (
        file_data.get("description") or ini_data.get("description") or None
    )
    return fields


def _load_config(
    project_override: str | None = None,
    base_url_override: str | None = None,
    token_override: str | None = None,
    config_override: str | None = None,
) -> KenConfig:
    """Resolve config from flags > env > .ken > ken.ini > defaults.

    Two files participate (#778):

    - ``ken.ini`` — shared, versioned, `configparser` format with section ``[ken]``.
    - ``.ken``    — local, gitignored, legacy ``key=value`` format. Holds
      ``api_token`` (the only true secret) and any per-user override.

    ``.ken`` keys override ``ken.ini`` keys, mirroring "local beats shared". When
    ``--config`` is passed explicitly, it points to a single file and is parsed
    according to its extension (``.ini`` → ini format, otherwise legacy).
    """
    ken_path, ini_path = _locate_config_files(config_override)

    ini_data: dict[str, str] = {}
    if ini_path is not None and ini_path.is_file():
        ini_data = _parse_ini_file(ini_path)

    file_data: dict[str, str] = {}
    if ken_path is not None and ken_path.is_file():
        _check_ken_permissions(ken_path)
        file_data = _parse_ken_file(ken_path)

    fields = _resolved_fields(file_data, ini_data)
    project_id = project_override or fields["project_id"]
    base_url = (base_url_override or fields["base_url"] or DEFAULT_BASE_URL).rstrip("/")
    api_token = token_override or fields["api_token"]
    return KenConfig(
        project_id=project_id,
        base_url=base_url,
        api_token=api_token,
        ken_file=ken_path if ken_path is not None and ken_path.is_file() else None,
        ini_file=ini_path if ini_path is not None and ini_path.is_file() else None,
        sync_dir=fields["sync_dir"] or DEFAULT_SYNC_DIR,
        architecture=fields["architecture"] or DEFAULT_ARCHITECTURE,
        wiki_dir=fields["wiki_dir"] or DEFAULT_WIKI_DIR,
        wiki_html_dir=fields["wiki_html_dir"] or DEFAULT_WIKI_HTML_DIR,
        description=fields["description"] or "",
    )


def _add_to_gitignore(cwd: Path) -> None:
    """Append ``.ken`` to the repo ``.gitignore`` if not already present."""
    git_marker = _find_file_upwards(cwd, ".git")
    if git_marker is None:
        click.echo(
            f"Warning: not in a git repository, "
            f"{KEN_FILE} not added to any .gitignore",
            err=True,
        )
        return
    repo_root = git_marker.parent
    gitignore = repo_root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    lines_in = [line.strip() for line in existing.splitlines()]
    if KEN_FILE in lines_in:
        return
    sep = "" if existing.endswith("\n") or not existing else "\n"
    gitignore.write_text(existing + sep + KEN_FILE + "\n", encoding="utf-8")
    click.echo(f"Added {KEN_FILE} to {gitignore}")


def _resolve_sync_dir(cfg: KenConfig) -> Path:
    """Resolve ``sync_dir`` to an absolute path.

    A relative ``sync_dir`` is anchored on the directory holding ``ken.ini`` (or
    ``.ken`` if no ini exists) so ``ken sync`` works from any subdirectory of the
    project. Falls back to ``cwd`` when no config file was found.
    """
    path = Path(cfg.sync_dir)
    if path.is_absolute():
        return path
    anchor = cfg.ini_file or cfg.ken_file
    base = anchor.parent if anchor is not None else Path.cwd()
    return base / path


def _persist_sync_dir(cfg: KenConfig) -> None:
    """Append ``sync_dir=<value>`` to the active config file if not recorded.

    Prefers ``ken.ini`` (versioned, shared) so the whole team picks up the value. Falls
    back to ``.ken`` for installs that never migrated.
    """
    if cfg.ini_file is not None:
        parser = configparser.ConfigParser()
        parser.read(cfg.ini_file, encoding="utf-8")
        if not parser.has_section(KEN_INI_SECTION):
            parser.add_section(KEN_INI_SECTION)
        if parser.get(KEN_INI_SECTION, "sync_dir", fallback=None) is not None:
            return
        parser.set(KEN_INI_SECTION, "sync_dir", cfg.sync_dir)
        with cfg.ini_file.open("w", encoding="utf-8") as fh:
            parser.write(fh)
        return
    if cfg.ken_file is None:
        return
    text = cfg.ken_file.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("sync_dir="):
            return
    sep = "" if not text or text.endswith("\n") else "\n"
    cfg.ken_file.write_text(text + sep + f"sync_dir={cfg.sync_dir}\n", encoding="utf-8")

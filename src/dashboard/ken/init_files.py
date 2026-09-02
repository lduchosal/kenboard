"""The files ``ken init`` writes and inspects in a repo.

Two of them, deliberately split (#778): ``ken.ini`` is the shared, versioned config the
whole team reads, ``.ken`` holds the API token alone and is gitignored at mode 0600.
Everything that decides *what lands on disk* lives here; ``cli`` keeps the command flow
and ``onboard_url`` the parsing of the link it starts from.
"""

from __future__ import annotations

import configparser
import sys
from fnmatch import fnmatch
from pathlib import Path

import click

from dashboard.ken.config import (
    DEFAULT_ARCHITECTURE,
    DEFAULT_SYNC_DIR,
    DEFAULT_WIKI_DIR,
    DEFAULT_WIKI_HTML_DIR,
    KEN_FILE,
    KEN_INI_FILE,
    KEN_INI_SECTION,
    KenConfig,
    _find_file_upwards,
    _parse_ini_file,
)

_WIKI_INI_KEYS = ("sync_dir", "architecture", "wiki_dir", "wiki_html_dir")


def _gitignore_rule_hiding_ini(cwd: Path) -> tuple[Path, str] | None:
    """Return the ``.gitignore`` rule that would keep ``ken.ini`` out of the repo.

    ``ken.ini`` is the shared, versioned half of the config (#778) — a rule broad enough
    to catch it (``ken*``, ``*.ini``) silently keeps the rest of the team on the default
    base_url. The last matching pattern wins, mirroring git's own semantics, so a
    negation (``!ken.ini``) cancels an earlier match. Only the repo-root ``.gitignore``
    is read: this is a warning, not a git reimplementation.
    """
    git_marker = _find_file_upwards(cwd, ".git")
    if git_marker is None:
        return None
    gitignore = git_marker.parent / ".gitignore"
    if not gitignore.is_file():
        return None
    hit: tuple[Path, str] | None = None
    for raw in gitignore.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pattern = line.removeprefix("!").strip("/")
        if not fnmatch(KEN_INI_FILE, pattern):
            continue
        hit = None if line.startswith("!") else (gitignore, line)
    return hit


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


def _refuse_existing_files(cwd: Path, *, has_token: bool, force: bool) -> None:
    """Exit rather than clobber an existing ``ken.ini`` / ``.ken`` without --force."""
    if force:
        return
    targets = [KEN_INI_FILE, *([KEN_FILE] if has_token else [])]
    for name in targets:
        if (cwd / name).is_file():
            click.echo(
                f"Error: {name} already exists. Use --force to overwrite.",
                err=True,
            )
            sys.exit(1)


def _ini_values(
    cfg: KenConfig, ini_target: Path, project_uuid: str, chosen_name: str
) -> dict[str, str]:
    """Build the whole ``[ken]`` section, keeping paths already customised on disk.

    Every key the resolver knows is written out, defaults included: the wiki/sync paths
    are a per-repo convention, and spelling them in the versioned file is how the team
    reads them without going through ``doc/ken-cli.md``. A re-run (``--force``)
    refreshes only the board coordinates.
    """
    values = {
        "project_id": project_uuid,
        "base_url": cfg.base_url,
        "description": chosen_name,
        "sync_dir": DEFAULT_SYNC_DIR,
        "architecture": DEFAULT_ARCHITECTURE,
        "wiki_dir": DEFAULT_WIKI_DIR,
        "wiki_html_dir": DEFAULT_WIKI_HTML_DIR,
    }
    if ini_target.is_file():
        existing = _parse_ini_file(ini_target)
        values.update({k: existing[k] for k in _WIKI_INI_KEYS if existing.get(k)})
    return values


def _warn_when_ini_is_gitignored(cwd: Path) -> None:
    """Warn when a .gitignore rule hides ``ken.ini`` — it is meant to be committed."""
    hit = _gitignore_rule_hiding_ini(cwd)
    if hit is None:
        return
    gitignore, pattern = hit
    click.echo(
        f"Warning: {KEN_INI_FILE} matches `{pattern}` in {gitignore}, so it will "
        f"never be committed. It holds the shared config (never the token) — drop "
        f"that rule or add `!{KEN_INI_FILE}`.",
        err=True,
    )


def _write_config_files(
    cfg: KenConfig, cwd: Path, project_uuid: str, chosen_name: str
) -> None:
    """Write ``ken.ini`` (shared) and, with a token in hand, ``.ken`` (0600)."""
    ini_target = cwd / KEN_INI_FILE
    ini_parser = configparser.ConfigParser()
    ini_parser[KEN_INI_SECTION] = _ini_values(
        cfg, ini_target, project_uuid, chosen_name
    )
    with ini_target.open("w", encoding="utf-8") as fh:
        ini_parser.write(fh)
    # An older board cannot hand over the display name (#1089) — fall back to the
    # id rather than print an empty pair of parentheses.
    click.echo(
        f"Wrote {KEN_INI_FILE} (project: {chosen_name or project_uuid}) — commit it"
    )
    _warn_when_ini_is_gitignored(cwd)

    if cfg.api_token:
        ken_target = cwd / KEN_FILE
        ken_target.write_text(f"api_token={cfg.api_token}\n", encoding="utf-8")
        ken_target.chmod(0o600)
        click.echo(f"Wrote {KEN_FILE} (api_token, mode 0600) — never commit it")
        _add_to_gitignore(cwd)
    else:
        click.echo(
            f"Note: the onboarding URL carried no ?token= — skipped {KEN_FILE}. "
            f"Ask for a link with a token (or pass --token), then re-run "
            f"`ken init <url> --force`.",
            err=True,
        )

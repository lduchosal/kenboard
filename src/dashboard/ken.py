"""Ken — task CLI for the kenboard board.

See ``doc/ken-cli.md`` for the full spec. Resolves config in this order: flags > env
vars (KEN_*) > .ken file in cwd (or any parent) > hardcoded defaults. Talks to the
kenboard REST API via the stdlib (no extra HTTP dependency).
"""

from __future__ import annotations

import io
import json as json_lib
import os
import re
import shutil
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
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

import click


def _version() -> str:
    """Return the kenboard package version for the User-Agent header."""
    try:
        from dashboard import __version__

        return __version__
    except ImportError:
        return "unknown"


DEFAULT_BASE_URL = "http://localhost:9090"
DEFAULT_SYNC_DIR = "doc/kenboard"
KEN_FILE = ".ken"
VALID_STATUSES = ("todo", "doing", "review", "done")
TASK_COLUMNS = [
    ("ID", "id"),
    ("STATUS", "status"),
    ("WHO", "who"),
    ("WHEN", "due_date"),
    ("TITLE", "title"),
]

# Filenames written by ``ken sync`` look like ``0042 - Title.md``.
_SYNC_FILENAME_RE = re.compile(r"^(\d+) - .+\.md$")
# Characters that are illegal (or risky) in filenames on common file systems.
_SYNC_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


@dataclass
class KenConfig:
    """Resolved CLI configuration, attached to the Click context."""

    project_id: str | None
    base_url: str
    api_token: str | None
    ken_file: Path | None
    sync_dir: str = DEFAULT_SYNC_DIR
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


def _load_config(
    project_override: str | None = None,
    base_url_override: str | None = None,
    token_override: str | None = None,
    config_override: str | None = None,
) -> KenConfig:
    """Resolve config from flags > env > .ken > defaults."""
    ken_path: Path | None
    if config_override:
        ken_path = Path(config_override).resolve()
        if not ken_path.is_file():
            click.echo(f"Error: config file not found: {config_override}", err=True)
            sys.exit(1)
    else:
        ken_path = _find_file_upwards(Path.cwd(), KEN_FILE)
    file_data: dict[str, str] = {}
    if ken_path is not None and ken_path.is_file():
        _check_ken_permissions(ken_path)
        file_data = _parse_ken_file(ken_path)

    project_id = (
        project_override
        or os.environ.get("KEN_PROJECT_ID")
        or file_data.get("project_id")
        or None
    )
    base_url = (
        base_url_override
        or os.environ.get("KEN_BASE_URL")
        or file_data.get("base_url")
        or DEFAULT_BASE_URL
    ).rstrip("/")
    api_token = (
        token_override
        or os.environ.get("KEN_API_TOKEN")
        or file_data.get("api_token")
        or None
    )
    sync_dir = (
        os.environ.get("KEN_SYNC_DIR") or file_data.get("sync_dir") or DEFAULT_SYNC_DIR
    )
    description = file_data.get("description", "")
    return KenConfig(
        project_id=project_id,
        base_url=base_url,
        api_token=api_token,
        ken_file=ken_path if ken_path is not None and ken_path.is_file() else None,
        sync_dir=sync_dir,
        description=description,
    )


def _ssl_context() -> Any:
    """Build an SSL context using certifi's CA bundle.

    Python installed via python.org on macOS ships without a CA bundle (the user must
    run ``Install Certificates.command`` manually). Using ``certifi.where()`` as the CA
    file makes ``ken`` work plug-and-play on any Python installation. ``certifi`` is a
    transitive dependency (via ``requests``) and updates its CA bundle automatically on
    ``pip install --upgrade kenboard``.
    """
    import ssl

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


_SSL_CTX = _ssl_context()


def _request(
    cfg: KenConfig,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
) -> Any:
    """Send a JSON request, return parsed response or None on empty body."""
    url = cfg.base_url + path
    data = json_lib.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Content-Type": "application/json",
        "User-Agent": f"ken/{_version()} Python/{sys.version.split()[0]}",
    }
    if cfg.api_token:
        headers["Authorization"] = f"Bearer {cfg.api_token}"
    req = urllib_request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, context=_SSL_CTX) as resp:  # noqa: S310
            raw = resp.read()
            if not raw:
                return None
            return json_lib.loads(raw)
    except urllib_error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        click.echo(f"Error: HTTP {e.code} on {method} {path}: {body_text}", err=True)
        sys.exit(1)
    except urllib_error.URLError as e:
        click.echo(f"Error: cannot reach {url}: {e.reason}", err=True)
        sys.exit(1)


def _require_project(cfg: KenConfig) -> str:
    """Return the resolved project_id or exit with a clear error."""
    if not cfg.project_id:
        click.echo(
            "Error: no project configured. "
            "Run `ken init <UUID>` or set KEN_PROJECT_ID.",
            err=True,
        )
        sys.exit(1)
    return cfg.project_id


def _format_columns(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    """Format rows as aligned columns."""
    if not rows:
        return "(no rows)"
    headers = [h for h, _ in columns]
    keys = [k for _, k in columns]
    cells: list[list[str]] = [headers]
    for row in rows:
        cells.append(
            [str(row.get(k)) if row.get(k) not in (None, "") else "--" for k in keys]
        )
    widths = [max(len(line[i]) for line in cells) for i in range(len(headers))]
    return "\n".join(
        "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(line))
        for line in cells
    )


def _output(
    data: Any,
    json_mode: bool,
    columns: list[tuple[str, str]] | None = None,
) -> None:
    """Print ``data`` as JSON or as an aligned column table."""
    if json_mode or columns is None:
        click.echo(json_lib.dumps(data, indent=2, default=str))
        return
    rows = data if isinstance(data, list) else [data]
    click.echo(_format_columns(rows, columns))


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


def _resolve_sync_dir(cfg: KenConfig) -> Path:
    """Resolve ``sync_dir`` to an absolute path.

    A relative ``sync_dir`` is anchored on the directory containing ``.ken`` (so ``ken
    sync`` works from any subdirectory of the project), falling back to the current
    working directory when no ``.ken`` exists.
    """
    path = Path(cfg.sync_dir)
    if path.is_absolute():
        return path
    base = cfg.ken_file.parent if cfg.ken_file is not None else Path.cwd()
    return base / path


def _persist_sync_dir(cfg: KenConfig) -> None:
    """Append ``sync_dir=<value>`` to ``.ken`` if not already recorded."""
    if cfg.ken_file is None:
        return
    text = cfg.ken_file.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("sync_dir="):
            return
    sep = "" if not text or text.endswith("\n") else "\n"
    cfg.ken_file.write_text(text + sep + f"sync_dir={cfg.sync_dir}\n", encoding="utf-8")


# -- Click commands -----------------------------------------------------------


@click.group()
@click.option("--project", help="Override project_id (UUID).")
@click.option("--base-url", help="Override the kenboard base URL.")
@click.option("--token", help="Override the API bearer token.")
@click.option("--config", "config_file", help="Path to a .ken config file.")
@click.pass_context
def cli(
    ctx: click.Context,
    project: str | None,
    base_url: str | None,
    token: str | None,
    config_file: str | None,
) -> None:
    """Ken — task CLI for the kenboard board."""
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = _load_config(project, base_url, token, config_file)


@cli.command()
@click.argument("project_uuid", required=False)
@click.option("--force", is_flag=True, help="Overwrite an existing .ken")
@click.pass_context
def init(ctx: click.Context, project_uuid: str | None, force: bool) -> None:
    """Initialize a .ken file in the current directory.

    Writes ``project_id``, ``base_url`` and (if set) ``api_token`` from the resolved CLI
    config. The file is created with mode 0600 and added to the repository
    ``.gitignore``.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    cwd = Path.cwd()
    target = cwd / KEN_FILE
    if target.exists() and not force:
        click.echo(
            f"Error: {KEN_FILE} already exists. Use --force to overwrite.",
            err=True,
        )
        sys.exit(1)

    projects_data = _request(cfg, "GET", "/api/v1/projects")
    if not projects_data:
        click.echo(
            "Error: no projects found on the kenboard. "
            "Create one via the web UI first.",
            err=True,
        )
        sys.exit(1)

    if project_uuid is None:
        click.echo("Available projects:")
        for i, p in enumerate(projects_data, 1):
            click.echo(f"  {i}. {p['name']} ({p.get('acronym', '')}) — {p['id']}")
        choice = click.prompt(
            "Select a project (number)",
            type=click.IntRange(1, len(projects_data)),
        )
        project_uuid = projects_data[choice - 1]["id"]
        chosen_name = projects_data[choice - 1]["name"]
    else:
        match = next((p for p in projects_data if p["id"] == project_uuid), None)
        if match is None:
            click.echo(
                f"Error: project {project_uuid} not found on {cfg.base_url}.",
                err=True,
            )
            sys.exit(1)
        chosen_name = match["name"]

    lines = [
        f"project_id={project_uuid}",
        f"base_url={cfg.base_url}",
        f"description={chosen_name}",
    ]
    if cfg.api_token:
        lines.append(f"api_token={cfg.api_token}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    target.chmod(0o600)
    click.echo(f"Wrote {KEN_FILE} (project: {chosen_name})")
    _add_to_gitignore(cwd)


@cli.command()
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.pass_context
def projects(ctx: click.Context, json_mode: bool) -> None:
    """List all projects on the kenboard."""
    cfg: KenConfig = ctx.obj["cfg"]
    data = _request(cfg, "GET", "/api/v1/projects")
    _output(
        data,
        json_mode,
        columns=[("ID", "id"), ("ACRONYM", "acronym"), ("NAME", "name")],
    )


@cli.command(name="list")
@click.option("--status", type=click.Choice(VALID_STATUSES))
@click.option("--who", help="Filter by assignee")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.pass_context
def list_tasks(
    ctx: click.Context, status: str | None, who: str | None, json_mode: bool
) -> None:
    """List tasks of the current project."""
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    tasks = _request(cfg, "GET", f"/api/v1/tasks?project={project_id}")
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if who:
        tasks = [t for t in tasks if t.get("who") == who]
    _output(tasks, json_mode, columns=TASK_COLUMNS)


@cli.command()
@click.argument("task_id", type=int)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.pass_context
def show(ctx: click.Context, task_id: int, json_mode: bool) -> None:
    """Show full details of a task."""
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    tasks = _request(cfg, "GET", f"/api/v1/tasks?project={project_id}")
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        click.echo(
            f"Error: task #{task_id} not found in project {project_id}",
            err=True,
        )
        sys.exit(1)
    if json_mode:
        click.echo(json_lib.dumps(task, indent=2, default=str))
        return
    for key in (
        "id",
        "status",
        "who",
        "due_date",
        "title",
        "description",
        "created_at",
        "updated_at",
    ):
        click.echo(f"{key:12s}: {task.get(key) if task.get(key) is not None else ''}")


def _resolve_desc(desc: str | None, desc_file: str | None = None) -> str | None:
    """Pick the description body from --desc-file > stdin (--desc -) > --desc (#393).

    Three input shapes are supported for agents that have different host capabilities:
    - ``--desc-file path/to/body.md`` reads from a file on disk (most agent-friendly,
      no shell escaping at all).
    - ``--desc -`` reads from stdin (heredoc-friendly for agents that can pipe).
    - ``--desc "literal text"`` passes the value through unchanged (single-line only —
      multi-line bash double-quoted strings drop newlines).

    Passing both ``--desc`` and ``--desc-file`` is an error so we don't have to invent
    a merge semantic. ``None`` (option not passed) and the empty string fall through
    unchanged.
    """
    if desc_file:
        if desc:
            raise click.UsageError(
                "Pass --desc OR --desc-file, not both. "
                "See `ken help` for the multi-line description idioms.",
            )
        try:
            return Path(desc_file).read_text(encoding="utf-8")
        except OSError as e:
            raise click.UsageError(f"Cannot read --desc-file: {e}") from e
    if desc == "-":
        return sys.stdin.read()
    return desc


@cli.command()
@click.argument("title")
@click.option(
    "--desc",
    default="",
    help="Description (single-line text, or '-' to read stdin)",
)
@click.option(
    "--desc-file",
    type=click.Path(dir_okay=False, readable=True),
    default=None,
    help="Read description from a file on disk (best for multi-line markdown)",
)
@click.option("--who", default="", help="Assignee")
@click.option("--status", type=click.Choice(VALID_STATUSES), default="todo")
@click.option("--when", help="Due date YYYY-MM-DD")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
# One option per task field, by design — silence the "too many arguments" warning.
@click.pass_context
def add(  # noqa: PLR0913
    ctx: click.Context,
    title: str,
    desc: str,
    desc_file: str | None,
    who: str,
    status: str,
    when: str | None,
    json_mode: bool,
) -> None:
    r"""Add a new task to the current project.

    For multi-line markdown descriptions, prefer ``--desc-file path/to/body.md`` (no
    shell escaping at all). ``--desc -`` reads from stdin (heredoc). Passing ``--desc
    "line1\nline2"`` in a double-quoted shell string stores the literal ``\n`` and
    breaks markdown rendering. See ``ken help`` for full examples.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    body: dict[str, Any] = {
        "project_id": project_id,
        "title": title,
        "description": _resolve_desc(desc, desc_file) or "",
        "who": who,
        "status": status,
        "due_date": when,
    }
    task = _request(cfg, "POST", "/api/v1/tasks", body=body)
    _output(task, json_mode, columns=TASK_COLUMNS)


@cli.command()
@click.argument("task_id", type=int)
@click.option("--title", help="New title")
@click.option(
    "--desc",
    help="New description (single-line text, or '-' to read stdin)",
)
@click.option(
    "--desc-file",
    type=click.Path(dir_okay=False, readable=True),
    default=None,
    help="Read new description from a file on disk (best for multi-line markdown)",
)
@click.option("--who", help="New assignee")
@click.option("--status", type=click.Choice(VALID_STATUSES), help="New status")
@click.option("--when", help="New due date YYYY-MM-DD")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
# One option per task field, by design — silence the "too many arguments" warning.
@click.pass_context
def update(  # noqa: PLR0913
    ctx: click.Context,
    task_id: int,
    title: str | None,
    desc: str | None,
    desc_file: str | None,
    who: str | None,
    status: str | None,
    when: str | None,
    json_mode: bool,
) -> None:
    r"""Update an existing task (only the fields you pass).

    For multi-line markdown in the description, prefer ``--desc-file path/to/body.md``
    (no shell escaping). ``--desc -`` reads from stdin (heredoc). ``--desc
    "line1\nline2"`` in a bash double-quoted string stores literal backslash-n's and
    corrupts markdown rendering (#393).
    """
    cfg: KenConfig = ctx.obj["cfg"]
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    # ``--desc-file`` is independent of ``--desc`` being set; resolve through
    # the helper so the file path wins (with a UsageError if both are passed).
    if desc is not None or desc_file is not None:
        body["description"] = _resolve_desc(desc, desc_file)
    if who is not None:
        body["who"] = who
    if status is not None:
        body["status"] = status
    if when is not None:
        body["due_date"] = when
    if not body:
        click.echo(
            "Error: nothing to update. Pass at least one of "
            "--title/--desc/--who/--status/--when",
            err=True,
        )
        sys.exit(1)
    task = _request(cfg, "PATCH", f"/api/v1/tasks/{task_id}", body=body)
    _output(task, json_mode, columns=TASK_COLUMNS)
    if status == "review":
        _wiki_groom_reminder(task_id)


def _wiki_groom_reminder(task_id: int) -> None:
    """Remind the agent to classify the task for the wiki (#376).

    Printed to stderr so it doesn't corrupt ``--json`` output. Always shown on
    transitions to ``review`` — if the task is already classified the reminder is a
    cheap no-op for the agent.
    """
    click.echo(
        f"Reminder: classify task #{task_id} for the wiki:\n"
        f"    ken wiki groom {task_id} <section_path>\n"
        "(run `ken wiki groom` with no args to list available sections)",
        err=True,
    )


@cli.command()
@click.argument("task_id", type=int)
@click.option(
    "--to",
    "to_status",
    required=True,
    type=click.Choice(VALID_STATUSES),
    help="Target status column",
)
@click.pass_context
def move(ctx: click.Context, task_id: int, to_status: str) -> None:
    """Move a task to another status column."""
    cfg: KenConfig = ctx.obj["cfg"]
    task = _request(
        cfg, "PATCH", f"/api/v1/tasks/{task_id}", body={"status": to_status}
    )
    click.echo(f"Task #{task['id']} → {task['status']}")
    if to_status == "review":
        _wiki_groom_reminder(task_id)


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def done(ctx: click.Context, task_id: int) -> None:
    """Mark a task as done — shortcut for `update --status done`."""
    cfg: KenConfig = ctx.obj["cfg"]
    task = _request(cfg, "PATCH", f"/api/v1/tasks/{task_id}", body={"status": "done"})
    click.echo(f"Task #{task['id']} → {task['status']}")


@cli.command()
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.pass_context
def sync(ctx: click.Context, json_mode: bool) -> None:
    """Mirror the project's tasks into ``sync_dir`` as one markdown file each.

    For every task in the configured project, writes
    ``<sync_dir>/<id> - <title>.md`` with a YAML frontmatter header.
    Files corresponding to tasks that no longer exist on the board are
    deleted, and title changes are handled by removing the old file
    before writing the new one. ``sync_dir`` defaults to ``doc/kenboard``
    and is persisted into ``.ken`` on first use.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    target = _resolve_sync_dir(cfg)
    target.mkdir(parents=True, exist_ok=True)
    _persist_sync_dir(cfg)

    tasks = _request(cfg, "GET", f"/api/v1/tasks?project={project_id}")
    desired: dict[int, tuple[str, str]] = {
        int(t["id"]): (_sync_filename(t), _format_sync_markdown(t)) for t in tasks
    }

    existing: dict[int, Path] = {}
    for entry in target.iterdir():
        if not entry.is_file():
            continue
        match = _SYNC_FILENAME_RE.match(entry.name)
        if match:
            existing[int(match.group(1))] = entry

    written: list[str] = []
    deleted: list[str] = []
    for task_id, (filename, content) in desired.items():
        new_path = target / filename
        old = existing.get(task_id)
        if old is not None and old != new_path:
            old.unlink()
            deleted.append(old.name)
        new_path.write_text(content, encoding="utf-8")
        written.append(filename)

    for task_id, path in existing.items():
        if task_id not in desired:
            path.unlink()
            deleted.append(path.name)

    if json_mode:
        click.echo(
            json_lib.dumps(
                {
                    "target": str(target),
                    "written": sorted(written),
                    "deleted": sorted(deleted),
                },
                indent=2,
            )
        )
        return
    click.echo(f"Synced {len(written)} task(s) to {target}")
    if deleted:
        click.echo(f"Removed {len(deleted)} stale file(s)")


@cli.command(name="self-update")
def self_update() -> None:
    """Upgrade kenboard to the latest version from PyPI.

    Runs ``pip install --upgrade kenboard`` using the same Python that is running this
    CLI. The new version is available on the next ``ken`` invocation.
    """
    import subprocess

    from dashboard import __version__

    click.echo(f"Current version: {__version__}")
    click.echo("Upgrading kenboard from PyPI...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "kenboard"],
        check=False,
    )
    if result.returncode != 0:
        click.echo("Error: upgrade failed", err=True)
        sys.exit(1)
    click.echo("Done. Run `ken --help` to verify the new version.")


# -- ken wiki ---------------------------------------------------------------


@cli.group()
def wiki() -> None:
    """Wiki commands — see ``ken wiki groom --help`` for the LLM Wiki pattern."""


_WIKI_GROOM_HELP = """\
``ken wiki groom`` — agent-driven task classification for the project wiki.

WHAT THIS IS
============

The wiki is a structured MD tree exported from your kanban tasks,
organized according to your project's ``ARCHITECTURE.md`` (sections
declared in YAML frontmatter). The export step (``ken wiki sync``) needs
to know which section each task belongs to — that mapping is what we
call its *classification*.

This command is the bridge: an LLM agent reads the unclassified queue,
decides the best section for each task, and writes back via repeated
``ken wiki groom <id> <section>`` calls. No model is invoked by ``ken``
itself — the agent is the orchestrator.

Conceptual reference (LLM Wiki pattern):
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

WORKFLOW
========

1. Call ``ken wiki groom`` with no args to dump:
   - the list of unclassified tasks (id / status / who / title)
   - the section paths declared in ``ARCHITECTURE.md``
   - instructions for the next step

2. For each task, decide the best section by reading the task title
   (and ``ken show <id>`` if needed) against the section descriptions.
   Prefer the deepest matching path (``backend/api`` beats ``backend``).

3. Apply the decision:

       ken wiki groom <task_id> <section_path>

   Example:

       ken wiki groom 42 backend/api

   The section path must exist in ``ARCHITECTURE.md`` — typos are
   rejected with the list of valid paths.

4. To inspect or revert:

       ken wiki groom <id> --show     # current classification
       ken wiki groom <id> --clear    # drop, back to unclassified

OPTIONS
=======

``--architecture PATH``  alternate path to the architecture file
                         (default: ``./ARCHITECTURE.md`` in cwd).
"""


def _load_sections(architecture: str) -> tuple[list, list[str]]:
    """Parse ARCHITECTURE.md and return ``(sections, valid_paths)``."""
    from dashboard.wiki import parse_architecture, section_paths

    sections = parse_architecture(architecture)
    return sections, section_paths(sections)


def _classified_by(cfg: KenConfig) -> str:
    """Best-effort actor label sent to the server's ``classified_by`` column.

    Prefers the API token's user (server resolves it via the auth middleware), falls
    back to the local ``$USER`` env var, then to ``"agent"``.
    """
    if cfg.api_token:
        # The server's _principal_name() picks the real identity from the
        # token — sending anything here is overwritten. Send a hint anyway
        # so it shows up if the server is mis-configured.
        return os.environ.get("USER") or "agent"
    return os.environ.get("USER") or "agent"


@wiki.command(name="groom", help="Classify tasks into wiki sections (agent-driven).")
@click.argument("task_id", type=int, required=False)
@click.argument("section", required=False)
@click.option(
    "--architecture",
    default="ARCHITECTURE.md",
    help="Path to the architecture file (default: ./ARCHITECTURE.md)",
)
@click.option("--show", is_flag=True, help="Show current classification for TASK_ID.")
@click.option("--clear", is_flag=True, help="Drop the classification for TASK_ID.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def groom(  # noqa: PLR0913
    ctx: click.Context,
    task_id: int | None,
    section: str | None,
    architecture: str,
    show: bool,
    clear: bool,
    json_mode: bool,
) -> None:
    """See ``ken wiki groom --help`` for the LLM Wiki pattern.

    Raises:
        UsageError: when the flag combination is invalid (e.g. ``--show`` and
            ``--clear`` together), when an op requiring ``TASK_ID`` is invoked
            without one, or when the section path isn't declared in the
            project's ARCHITECTURE.md.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    if show and clear:
        raise click.UsageError("--show and --clear are mutually exclusive.")
    if (show or clear) and task_id is None:
        raise click.UsageError("--show / --clear require TASK_ID.")
    if section is not None and task_id is None:
        raise click.UsageError("SECTION requires TASK_ID.")

    # ---- per-task ops ----
    if task_id is not None:
        if clear:
            _request(cfg, "DELETE", f"/api/v1/wiki/classify/{task_id}")
            click.echo(f"Cleared classification for task #{task_id}.")
            return
        if show:
            try:
                row = _request(cfg, "GET", f"/api/v1/wiki/classify/{task_id}")
            except SystemExit:
                # _request exits on HTTPError; the 404 ("Unclassified")
                # case is informational, not fatal. Re-emit a friendly
                # line then exit 0 instead of propagating.
                click.echo(f"Task #{task_id} is unclassified.")
                return
            _output(row, json_mode, columns=None)
            return
        if section is None:
            raise click.UsageError(
                "Pass SECTION to classify, or --show / --clear.",
            )
        # Validate against the architecture before sending.
        _sections, valid = _load_sections(architecture)
        if not valid:
            raise click.UsageError(
                f"No sections declared in {architecture}. "
                "Add a `wiki.sections` block to its YAML frontmatter "
                "before classifying tasks. See `ken wiki groom --help`.",
            )
        if section not in valid:
            joined = "\n  ".join(valid)
            raise click.UsageError(
                f"Unknown section '{section}'. Declared paths:\n  {joined}",
            )
        body = {
            "task_id": task_id,
            "section_path": section,
            "classified_by": _classified_by(cfg),
        }
        row = _request(cfg, "POST", "/api/v1/wiki/classify", body=body)
        _output(row, json_mode, columns=None)
        return

    # ---- no-args: list unclassified + sections ----
    # When a project is configured, send it server-side so a per-project
    # api_key passes the auth scope check (admin keys see across projects).
    endpoint = "/api/v1/wiki/unclassified"
    if cfg.project_id:
        endpoint = f"{endpoint}?project={cfg.project_id}"
    unclassified = _request(cfg, "GET", endpoint) or []
    sections, paths = _load_sections(architecture)

    if json_mode:
        click.echo(
            json_lib.dumps(
                {
                    "unclassified": unclassified,
                    "sections": [
                        {"path": p, "title": _section_title_for(sections, p)}
                        for p in paths
                    ],
                    "architecture": architecture,
                },
                indent=2,
                default=str,
            ),
        )
        return

    click.echo("WIKI GROOMING")
    click.echo("")
    click.echo(
        "Assign each task to a section of ARCHITECTURE.md so the wiki "
        "export mirrors the project structure. Decide for each task, "
        "then run:",
    )
    click.echo("")
    click.echo("    ken wiki groom <id> <section>")
    click.echo("")
    if not unclassified:
        click.echo("(no unclassified tasks)")
    else:
        click.echo(f"{len(unclassified)} unclassified task(s):")
        click.echo(
            _format_columns(
                unclassified,
                [
                    ("ID", "id"),
                    ("STATUS", "status"),
                    ("WHO", "who"),
                    ("TITLE", "title"),
                ],
            ),
        )
    click.echo("")
    if not paths:
        click.echo(
            f"WARNING: no sections declared in {architecture}. "
            "Add a `wiki.sections` block to its YAML frontmatter.",
        )
    else:
        click.echo(f"Sections (from {architecture}):")
        for p in paths:
            title = _section_title_for(sections, p)
            click.echo(f"  {p:30s}  {title}")
    click.echo("")
    click.echo("See `ken wiki groom --help` for the concept (LLM Wiki pattern).")


def _section_title_for(sections: list, path: str) -> str:
    """Look up a section by its flat path and return its title (or path)."""
    for section in sections:
        for p, node in section.flatten():
            if p == path:
                return node.title or path
    return path


# Inject the verbose help text after registration (Click can't easily
# accept a paragraph-styled docstring AND a one-line --help summary).
groom.help = _WIKI_GROOM_HELP


# -- ken wiki sync -----------------------------------------------------------


_SLUG_NONWORD_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """Lowercase ``text`` and collapse non-alphanumerics into dashes.

    Used to build the filename portion of a task detail page:
    ``<section>/<slug>-<id>.md`` (#376f). The id suffix breaks ties when two
    tasks share the same title.
    """
    slug = _SLUG_NONWORD_RE.sub("-", text.lower()).strip("-")
    return slug or "untitled"


def _task_filename(task: dict[str, Any]) -> str:
    """Return ``<slug>-<id>.md`` for the per-task detail page."""
    return f"{_slugify(str(task.get('title') or ''))}-{task['task_id']}.md"


_ARCHIVED_STATUSES = frozenset({"done"})
_ACTIVE_STATUS_ORDER = ("doing", "review", "todo")


def _format_section_md(node: Any, path: str, tasks: list[dict[str, Any]]) -> str:
    """Render one section's ``index.md`` — split into "En cours" / "Archivé" (#376f).

    Each row links to ``<slug>-<id>.md`` (the per-task detail page). ``who`` is omitted
    (always Q/Claude → no signal). ``status`` and ``due_date`` are only shown when they
    carry information (status hidden on archived rows; due_date only if set on a non-
    done task).
    """
    lines = [f"# {node.title}", ""]
    if node.description:
        lines.extend([node.description, ""])
    lines.extend([f"Section: `{path}`", ""])
    if not tasks:
        lines.append("(no tasks classified yet)")
        return "\n".join(lines) + "\n"

    active = [t for t in tasks if (t.get("status") or "") not in _ARCHIVED_STATUSES]
    archived = [t for t in tasks if (t.get("status") or "") in _ARCHIVED_STATUSES]

    def _active_key(t: dict[str, Any]) -> tuple[int, int]:
        """Sort key: doing → review → todo → others, ties broken by id."""
        status = t.get("status") or ""
        order = (
            _ACTIVE_STATUS_ORDER.index(status)
            if status in _ACTIVE_STATUS_ORDER
            else len(_ACTIVE_STATUS_ORDER)
        )
        return (order, int(t["task_id"]))

    if active:
        lines.extend((f"## En cours ({len(active)})", ""))
        for t in sorted(active, key=_active_key):
            lines.append(_format_section_row(t, archived=False))
        lines.append("")
    if archived:
        lines.extend((f"## Archivé ({len(archived)})", ""))
        for t in sorted(archived, key=lambda x: int(x["task_id"])):
            lines.append(_format_section_row(t, archived=True))
    return "\n".join(lines) + "\n"


def _format_section_row(task: dict[str, Any], *, archived: bool) -> str:
    """One bullet line for the section index — `[title](slug-id.md)` + metadata."""
    title = task.get("title") or ""
    href = _task_filename(task)
    line = f"- [{title}]({href})"
    if not archived:
        status = task.get("status") or ""
        if status:
            line += f" — _{status}_"
        due = task.get("due_date")
        if due:
            line += f" — due {due}"
    return line


def _format_task_detail_md(
    task: dict[str, Any], section_path: str, section_title: str
) -> str:
    """Render the per-task detail page (#376f).

    Emits YAML frontmatter so ``wiki build`` can lift the metadata into the
    ``.fullscreen-card`` HTML layout without re-parsing the body. The body is the task
    description, rendered as-is (already MD).
    """
    fm_lines = [
        "---",
        f"id: {task['task_id']}",
        f"title: {_yaml_str(task.get('title') or '')}",
        f"status: {task.get('status') or ''}",
        f"who: {_yaml_str(task.get('who') or '')}",
        f"due_date: {task.get('due_date') or ''}",
        f"classified_at: {task.get('classified_at') or ''}",
        f"classified_by: {_yaml_str(task.get('classified_by') or '')}",
        f"section: {section_path}",
        f"section_title: {_yaml_str(section_title)}",
        "---",
        "",
    ]
    title = task.get("title") or ""
    body_lines = [
        f"# #{task['task_id']} — {title}",
        "",
    ]
    desc = task.get("description") or ""
    if desc.strip():
        body_lines.extend([desc.rstrip(), ""])
    else:
        body_lines.extend(["*(no description)*", ""])
    nav = (
        f"---\n\n[← retour à {section_path}](index.md) · "
        "[voir log](" + "../" * (section_path.count("/") + 1) + "log.md)\n"
    )
    return "\n".join(fm_lines + body_lines) + nav


def _yaml_str(text: str) -> str:
    """Quote a YAML scalar so colons / `#` / leading whitespace don't break parsing."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _format_root_index_md(
    sections: list, by_path: dict[str, list[dict[str, Any]]]
) -> str:
    """Render the wiki root ``index.md`` (sidebar-style TOC + counts)."""
    lines = ["# kenboard wiki", "", "Generated by `ken wiki sync`.", ""]
    total = sum(len(v) for v in by_path.values())
    lines.extend([f"Total classified: **{total}**.", ""])
    for section in sections:
        for path, node in section.flatten():
            depth = path.count("/")
            indent = "  " * depth
            count = len(by_path.get(path, []))
            lines.append(
                f"{indent}- [{node.title}]({path}/index.md) — {count} task(s)",
            )
    return "\n".join(lines) + "\n"


def _format_log_md(rows: list[dict[str, Any]]) -> str:
    """Render ``log.md`` — chronological classification audit, newest first."""
    lines = ["# Classification log", "", "Most recent first.", ""]
    sorted_rows = sorted(
        rows,
        key=lambda r: r.get("classified_at") or "",
        reverse=True,
    )
    for r in sorted_rows:
        when = r.get("classified_at") or "?"
        by = r.get("classified_by") or "?"
        title = r.get("title") or ""
        lines.append(
            f"- {when} — task #{r['task_id']} ({title}) → "
            f"`{r['section_path']}` (by {by})",
        )
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


def _build_sync_plan(
    sections: list, paths: list[str], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Plan every file to write — pure function, easy to unit test."""
    by_path: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_path.setdefault(r["section_path"], []).append(r)
    declared = set(paths)
    orphans = {p: v for p, v in by_path.items() if p not in declared}

    files: list[dict[str, str]] = [
        {"path": "index.md", "content": _format_root_index_md(sections, by_path)},
    ]
    for section in sections:
        for path, node in section.flatten():
            section_tasks = by_path.get(path, [])
            files.append(
                {
                    "path": f"{path}/index.md",
                    "content": _format_section_md(node, path, section_tasks),
                },
            )
            # Per-task detail pages (#376f, Option B): one MD per task with
            # YAML frontmatter so wiki build can lift the metadata into the
            # ``.fullscreen-card`` HTML layout.
            for task in section_tasks:
                files.append(
                    {
                        "path": f"{path}/{_task_filename(task)}",
                        "content": _format_task_detail_md(task, path, node.title),
                    },
                )
    files.append({"path": "log.md", "content": _format_log_md(rows)})
    if orphans:
        files.append({"path": "orphans.md", "content": _format_orphans_md(orphans)})
    return {
        "files": files,
        "sections": len(paths),
        "classifications": len(rows),
        "orphans": len(orphans),
    }


def _write_sync_plan(out: str, plan: dict[str, Any]) -> None:
    """Idempotently materialise ``plan`` under ``out`` (clean + re-write)."""
    base = Path(out)
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    for f in plan["files"]:
        target = base / f["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f["content"], encoding="utf-8")


@wiki.command(name="sync", help="Export classifications to a structured MD tree.")
@click.option(
    "--out",
    default="wiki",
    help="Output directory — re-written from scratch each run (default: ./wiki).",
)
@click.option(
    "--architecture",
    default="ARCHITECTURE.md",
    help="Path to the architecture file (default: ./ARCHITECTURE.md).",
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Dry-run: print the plan as JSON and don't touch disk.",
)
@click.pass_context
def wiki_sync(
    ctx: click.Context,
    out: str,
    architecture: str,
    json_mode: bool,
) -> None:
    """Materialise the wiki MD tree from live classifications (chunk C, #376c).

    Raises:
        UsageError: when ``ARCHITECTURE.md`` is missing or declares no sections.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    sections, paths = _load_sections(architecture)
    if not paths:
        raise click.UsageError(
            f"No sections declared in {architecture}. "
            "Add a `wiki.sections` block to its YAML frontmatter "
            "before running sync. See `ken wiki groom --help`.",
        )
    endpoint = "/api/v1/wiki/all"
    if cfg.project_id:
        endpoint = f"{endpoint}?project={cfg.project_id}"
    rows = _request(cfg, "GET", endpoint) or []
    plan = _build_sync_plan(sections, paths, rows)

    if json_mode:
        click.echo(json_lib.dumps(plan, indent=2, default=str))
        return

    _write_sync_plan(out, plan)
    click.echo(
        f"Wrote {len(plan['files'])} file(s) under {out}/ "
        f"({plan['sections']} sections, {plan['classifications']} classifications"
        + (f", {plan['orphans']} orphan section(s)" if plan["orphans"] else "")
        + ").",
    )


# -- ken wiki build ----------------------------------------------------------

_WIKI_HTML_CSS = """\
body{margin:0;font-family:system-ui,sans-serif;color:#222;background:#fff}
.layout{display:grid;grid-template-columns:240px 1fr;min-height:100vh}
nav.sidebar{background:#f6f8fa;border-right:1px solid #d0d7de;padding:16px;
  overflow-y:auto;font-size:13px}
nav.sidebar h1{font-size:14px;text-transform:uppercase;color:#57606a;margin:0 0 12px}
nav.sidebar ul{list-style:none;padding:0;margin:0}
nav.sidebar li{margin:2px 0}
nav.sidebar a{color:#0969da;text-decoration:none}
nav.sidebar a:hover{text-decoration:underline}
nav.sidebar a.current{font-weight:600;color:#1a1a1a}
main{padding:24px 32px;max-width:900px}
main h1{margin-top:0}
main code{background:#f6f8fa;padding:1px 4px;border-radius:3px;font-size:90%}
main pre{background:#f6f8fa;padding:12px;border-radius:6px;overflow-x:auto}
main pre code{background:transparent;padding:0}
main a{color:#0969da}
/* Task detail (#376f — mirrors templates/modals/task_fullscreen.html) */
.fullscreen-card{background:#fff;border:1px solid #d0d7de;border-radius:10px;
  padding:32px 36px;max-width:760px}
.fullscreen-header{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.fullscreen-id{font-size:12px;color:#57606a;font-weight:600}
.fullscreen-status{font-size:11px;text-transform:uppercase;letter-spacing:.5px;
  color:#57606a;background:#f6f8fa;padding:3px 8px;border-radius:10px}
.fullscreen-status.status-todo{background:#ddf4ff;color:#0969da}
.fullscreen-status.status-doing{background:#fff8c5;color:#9a6700}
.fullscreen-status.status-review{background:#dafbe1;color:#1a7f37}
.fullscreen-status.status-done{background:#eaeef2;color:#57606a}
.fullscreen-title{font-size:22px;font-weight:700;margin:0 0 16px;line-height:1.3}
.fullscreen-meta{display:flex;align-items:center;gap:10px;margin-bottom:20px;
  font-size:13px;color:#57606a}
.task-avatar{width:28px;height:28px;border-radius:50%;display:flex;
  align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:12px}
.fs-who{font-weight:600;color:#222}
.fullscreen-desc{font-size:14px;line-height:1.7;border-top:1px solid #d0d7de;
  padding-top:16px}
.fullscreen-desc h1,.fullscreen-desc h2,.fullscreen-desc h3{margin-top:16px;
  margin-bottom:8px}
.fullscreen-desc pre{background:#f6f8fa;border-radius:4px;padding:12px;
  overflow-x:auto;font-size:12px}
.fullscreen-desc code{background:#f6f8fa;border-radius:3px;padding:1px 4px;font-size:12px}
.fullscreen-desc pre code{background:transparent;padding:0}
.fullscreen-desc ul,.fullscreen-desc ol{padding-left:20px}
.wiki-nav{margin-top:20px;padding-top:12px;border-top:1px solid #d0d7de;
  font-size:13px;color:#57606a}
.wiki-nav a{color:#0969da}
"""

# Stable per-name avatar colour — picked from a small palette so the
# detail page renders the same swatch as the board card. Mirrors
# ``buildAvatar`` in ``static/js/tasks.js`` at a high level (palette
# differs in length but the deterministic hash keeps it consistent
# per identity).
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


def _avatar_color(name: str) -> str:
    """Deterministically map a name to one of ``_AVATAR_PALETTE``."""
    if not name:
        return _AVATAR_PALETTE[0]
    return _AVATAR_PALETTE[sum(ord(c) for c in name) % len(_AVATAR_PALETTE)]


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


def _render_markdown(md_text: str) -> str:
    """Convert a markdown string to safe HTML via the ``markdown`` library."""
    import markdown as md_lib

    return str(md_lib.markdown(md_text, extensions=["fenced_code", "tables"]))


def _rewrite_md_links_to_html(html: str) -> str:
    """Rewrite ``href="…/index.md"`` (and ``foo.md``) to ``.html`` in rendered HTML."""
    return re.sub(r'href="([^"]+)\.md"', r'href="\1.html"', html)


def _format_sidebar_nav(sections: list, current_path: str | None) -> str:
    """Render the per-page sidebar nav, marking the current page with
    ``class=current``.
    """
    lines = ['<nav class="sidebar"><h1>kenboard wiki</h1><ul>']
    root_cls = ' class="current"' if current_path == "" else ""
    root_href = (
        "../" * current_path.count("/") + "index.html" if current_path else "index.html"
    )
    if current_path is not None:
        lines.append(f'<li><a href="{root_href}"{root_cls}>Home</a></li>')
    for section in sections:
        for path, node in section.flatten():
            depth = path.count("/")
            indent_style = f"padding-left:{depth * 12}px"
            href = _relative_href(current_path, f"{path}/index.html")
            cls = ' class="current"' if path == current_path else ""
            lines.append(
                f'<li style="{indent_style}"><a href="{href}"{cls}>{node.title}</a></li>',
            )
    lines.append("</ul></nav>")
    return "".join(lines)


def _relative_href(from_path: str | None, to_path: str) -> str:
    """Compute the relative href from one wiki page to another (both relative to wiki
    root).
    """
    if from_path is None or from_path == "":
        return to_path
    # Strip the trailing index.html from from_path to get the directory depth
    depth = from_path.count("/") + 1  # +1 because we're inside a subdir
    return "../" * depth + to_path


def _wrap_html(title: str, body_html: str, sidebar_html: str) -> str:
    """Wrap a rendered body with the standard layout (head + sidebar + main)."""
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{title} — kenboard wiki</title>"
        f"<style>{_WIKI_HTML_CSS}</style>"
        '</head><body><div class="layout">'
        f"{sidebar_html}"
        f"<main>{body_html}</main>"
        "</div></body></html>"
    )


def _extract_title(md_text: str) -> str:
    """Pull the first ``# heading`` line out of an MD blob to use as the ``<title>``."""
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "kenboard wiki"


def _build_html_plan(in_dir: Path, sections: list) -> list[dict[str, str]]:
    """Walk every ``.md`` under ``in_dir`` and return ``[{path, content}]`` for HTML
    output.

    Detail pages (any MD with a YAML frontmatter block — written by
    ``_format_task_detail_md`` since #376f) get the ``.fullscreen-card`` layout
    mirroring the kenboard board's full-screen task view; everything else gets the plain
    Markdown layout.
    """
    files: list[dict[str, str]] = []
    for md_path in sorted(in_dir.rglob("*.md")):
        rel = md_path.relative_to(in_dir)
        md_text = md_path.read_text(encoding="utf-8")
        meta, body_md = _split_frontmatter(md_text)
        # Sidebar "current" key: section directory if this is an index page
        # or a per-task detail page; else the bare filename.
        if rel.name == "index.md" or meta:
            section_key = str(rel.parent)
        else:
            section_key = str(rel)
        if section_key == ".":
            section_key = ""
        sidebar = _format_sidebar_nav(sections, section_key)
        if meta and "id" in meta:
            page_title = f"#{meta.get('id')} — {meta.get('title') or 'task'}"
            body_html = _render_task_detail(meta, body_md)
        else:
            page_title = _extract_title(md_text)
            body_html = _rewrite_md_links_to_html(_render_markdown(md_text))
        html = _wrap_html(page_title, body_html, sidebar)
        files.append({"path": str(rel.with_suffix(".html")), "content": html})
    return files


def _render_task_detail(meta: dict[str, Any], body_md: str) -> str:
    """Render a per-task detail page as ``.fullscreen-card`` HTML (#376f).

    ``meta`` comes from the page's YAML frontmatter (set by ``_format_task_detail_md``).
    ``body_md`` is the description body — the H1 / footer-nav written by sync are
    stripped server-side here since the fullscreen template renders its own header.
    """
    status = str(meta.get("status") or "")
    who = str(meta.get("who") or "")
    due = str(meta.get("due_date") or "")
    classified_at = str(meta.get("classified_at") or "")
    classified_by = str(meta.get("classified_by") or "")
    section = str(meta.get("section") or "")
    avatar_initial = (who[:1] or "?").upper()
    avatar_color = _avatar_color(who)
    meta_parts = [
        f'<div class="task-avatar" style="background:{avatar_color}">{avatar_initial}</div>',
        f'<span class="fs-who">{who}</span>' if who else "",
        f"<span>Due {due}</span>" if due else "",
        f"<span>Classified {classified_at[:10]}</span>" if classified_at else "",
        f"<span>by {classified_by}</span>" if classified_by else "",
    ]
    desc_md = _strip_detail_chrome(body_md)
    desc_html = _rewrite_md_links_to_html(_render_markdown(desc_md))
    log_href = "../" * (section.count("/") + 1) + "log.html"
    section_label = section or "section"
    status_cls = f"status-{status}" if status else ""
    return (
        '<div class="fullscreen-card">'
        '<div class="fullscreen-header">'
        f'<span class="fullscreen-id">#{meta.get("id")}</span>'
        f'<span class="fullscreen-status {status_cls}">{status}</span>'
        "</div>"
        f'<h2 class="fullscreen-title">{meta.get("title") or ""}</h2>'
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
    default="wiki",
    help="Input directory holding the MD tree (default: ./wiki — output of `wiki sync`).",
)
@click.option(
    "--out",
    default="wiki-html",
    help="Output directory — re-written from scratch each run (default: ./wiki-html).",
)
@click.option(
    "--architecture",
    default="ARCHITECTURE.md",
    help="Path to the architecture file (default: ./ARCHITECTURE.md).",
)
@click.pass_context
def wiki_build(
    ctx: click.Context,
    in_dir: str,
    out: str,
    architecture: str,
) -> None:
    """Build the HTML wiki from the MD tree produced by ``ken wiki sync``.

    Raises:
        UsageError: when ``--in`` doesn't exist or ``ARCHITECTURE.md`` is missing.
    """
    _ = ctx  # CLI context not needed (purely local IO).
    src = Path(in_dir)
    if not src.is_dir():
        raise click.UsageError(
            f"Input directory '{in_dir}' does not exist. "
            "Run `ken wiki sync` first to generate the MD tree.",
        )
    sections, paths = _load_sections(architecture)
    if not paths:
        raise click.UsageError(
            f"No sections declared in {architecture}. "
            "Add a `wiki.sections` block to its YAML frontmatter "
            "before running build. See `ken wiki groom --help`.",
        )
    files = _build_html_plan(src, sections)
    _write_html_plan(out, files)
    click.echo(f"Wrote {len(files)} HTML file(s) under {out}/.")


# -- ken wiki lint -----------------------------------------------------------


def _build_lint_report(
    paths: list[str],
    classified: list[dict[str, Any]],
    unclassified: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute orphans / unclassified / empty-section findings (#376e).

    Pure function so the CLI's exit-code logic and JSON output share one source of
    truth. Inputs are the declared section paths from ``ARCHITECTURE.md`` and the two
    server lists (all classifications + unclassified tasks).
    """
    declared = set(paths)
    classified_paths = {r["section_path"] for r in classified}
    orphan_paths = sorted(classified_paths - declared)
    empty_sections = sorted(declared - classified_paths)

    orphans: list[dict[str, Any]] = []
    for path in orphan_paths:
        tasks = [r for r in classified if r["section_path"] == path]
        orphans.append(
            {
                "section_path": path,
                "task_count": len(tasks),
                "task_ids": [r["task_id"] for r in tasks],
            },
        )

    unclassified_brief = [
        {
            "task_id": t["id"],
            "title": t.get("title") or "",
            "status": t.get("status") or "",
        }
        for t in unclassified
    ]

    return {
        "errors": [{"code": "ORPHAN"} | o for o in orphans],
        "warnings": [{"code": "UNCLASSIFIED"} | t for t in unclassified_brief],
        "info": [{"code": "EMPTY-SECTION", "section_path": p} for p in empty_sections],
        "summary": {
            "errors": len(orphans),
            "warnings": len(unclassified_brief),
            "info": len(empty_sections),
            "sections": len(declared),
            "classified": len(classified),
        },
    }


def _print_lint_report(report: dict[str, Any]) -> None:
    """Render the lint report as readable text on stdout."""
    s = report["summary"]
    click.echo(
        f"wiki lint: {s['errors']} error(s), {s['warnings']} warning(s), "
        f"{s['info']} info ({s['sections']} sections, "
        f"{s['classified']} classifications)",
    )
    if report["errors"]:
        click.echo("")
        click.echo("ERRORS:")
        for e in report["errors"]:
            ids = ", ".join(f"#{i}" for i in e["task_ids"])
            click.echo(
                f"  ORPHAN  section `{e['section_path']}` not in ARCHITECTURE.md "
                f"({e['task_count']} task(s): {ids})",
            )
    if report["warnings"]:
        click.echo("")
        click.echo("WARNINGS:")
        for w in report["warnings"]:
            click.echo(
                f"  UNCLASSIFIED  #{w['task_id']} [{w['status']}] {w['title']}",
            )
    if report["info"]:
        click.echo("")
        click.echo("INFO:")
        for i in report["info"]:
            click.echo(f"  EMPTY-SECTION  `{i['section_path']}` has no tasks")


@wiki.command(name="lint", help="Report orphans / unclassified / empty sections.")
@click.option(
    "--architecture",
    default="ARCHITECTURE.md",
    help="Path to the architecture file (default: ./ARCHITECTURE.md).",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Warnings also fail with exit 1 (default: only errors fail).",
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Emit the report as JSON (stable schema for CI).",
)
@click.pass_context
def wiki_lint(
    ctx: click.Context,
    architecture: str,
    strict: bool,
    json_mode: bool,
) -> None:
    """Check the live wiki for orphans, unclassified tasks, and empty sections (#376e).

    Exit code: ``1`` when any ERROR is present, or when any WARNING is present in
    ``--strict`` mode. ``0`` otherwise.

    Raises:
        UsageError: when ``ARCHITECTURE.md`` is missing or declares no sections.
    """
    cfg: KenConfig = ctx.obj["cfg"]
    _sections, paths = _load_sections(architecture)
    if not paths:
        raise click.UsageError(
            f"No sections declared in {architecture}. "
            "Add a `wiki.sections` block to its YAML frontmatter "
            "before running lint. See `ken wiki groom --help`.",
        )
    suffix = f"?project={cfg.project_id}" if cfg.project_id else ""
    classified = _request(cfg, "GET", f"/api/v1/wiki/all{suffix}") or []
    unclassified = _request(cfg, "GET", f"/api/v1/wiki/unclassified{suffix}") or []
    report = _build_lint_report(paths, classified, unclassified)

    if json_mode:
        click.echo(json_lib.dumps(report, indent=2, default=str))
    else:
        _print_lint_report(report)

    failing = report["summary"]["errors"] > 0 or (
        strict and report["summary"]["warnings"] > 0
    )
    if failing:
        sys.exit(1)


@cli.command(name="help")
def help_cmd() -> None:
    """Print the agent guide (kenboard best practices for LLM agents).

    Loads ``agent_guide.md`` from the installed package via ``importlib.resources`` so
    the doc travels with the wheel and stays in sync with the CLI version. Pair with
    ``ken --help`` for the auto-generated command reference.
    """
    text = (
        resources.files("dashboard")
        .joinpath("agent_guide.md")
        .read_text(encoding="utf-8")
    )
    click.echo(text)

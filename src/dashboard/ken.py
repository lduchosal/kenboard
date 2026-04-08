"""Ken — task CLI for the kenboard board.

See ``doc/ken-cli.md`` for the full spec. Resolves config in this order:
flags > env vars (KEN_*) > .ken file in cwd (or any parent) > hardcoded
defaults. Talks to the kenboard REST API via the stdlib (no extra HTTP
dependency).
"""

from __future__ import annotations

import json as json_lib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

import click

DEFAULT_BASE_URL = "http://localhost:9090"
KEN_FILE = ".ken"
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
    """Warn on stderr if ``.ken`` is readable by group/other."""
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
) -> KenConfig:
    """Resolve config from flags > env > .ken > defaults."""
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
    return KenConfig(
        project_id=project_id,
        base_url=base_url,
        api_token=api_token,
        ken_file=ken_path if ken_path is not None and ken_path.is_file() else None,
    )


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
    headers = {"Content-Type": "application/json"}
    if cfg.api_token:
        headers["Authorization"] = f"Bearer {cfg.api_token}"
    req = urllib_request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req) as resp:  # noqa: S310 - http(s) only
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


# -- Click commands -----------------------------------------------------------


@click.group()
@click.option("--project", help="Override project_id (UUID).")
@click.option("--base-url", help="Override the kenboard base URL.")
@click.option("--token", help="Override the API bearer token.")
@click.pass_context
def cli(
    ctx: click.Context,
    project: str | None,
    base_url: str | None,
    token: str | None,
) -> None:
    """Ken — task CLI for the kenboard board."""
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = _load_config(project, base_url, token)


@cli.command()
@click.argument("project_uuid", required=False)
@click.option("--force", is_flag=True, help="Overwrite an existing .ken")
@click.pass_context
def init(ctx: click.Context, project_uuid: str | None, force: bool) -> None:
    """Initialize a .ken file in the current directory.

    Writes ``project_id``, ``base_url`` and (if set) ``api_token`` from the
    resolved CLI config. The file is created with mode 0600 and added to the
    repository ``.gitignore``.
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

    lines = [f"project_id={project_uuid}", f"base_url={cfg.base_url}"]
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


@cli.command()
@click.argument("title")
@click.option("--desc", default="", help="Description")
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
    who: str,
    status: str,
    when: str | None,
    json_mode: bool,
) -> None:
    """Add a new task to the current project."""
    cfg: KenConfig = ctx.obj["cfg"]
    project_id = _require_project(cfg)
    body: dict[str, Any] = {
        "project_id": project_id,
        "title": title,
        "description": desc,
        "who": who,
        "status": status,
        "due_date": when,
    }
    task = _request(cfg, "POST", "/api/v1/tasks", body=body)
    _output(task, json_mode, columns=TASK_COLUMNS)


@cli.command()
@click.argument("task_id", type=int)
@click.option("--title", help="New title")
@click.option("--desc", help="New description")
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
    who: str | None,
    status: str | None,
    when: str | None,
    json_mode: bool,
) -> None:
    """Update an existing task (only the fields you pass)."""
    cfg: KenConfig = ctx.obj["cfg"]
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if desc is not None:
        body["description"] = desc
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


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def done(ctx: click.Context, task_id: int) -> None:
    """Mark a task as done — shortcut for `update --status done`."""
    cfg: KenConfig = ctx.obj["cfg"]
    task = _request(cfg, "PATCH", f"/api/v1/tasks/{task_id}", body={"status": "done"})
    click.echo(f"Task #{task['id']} → {task['status']}")

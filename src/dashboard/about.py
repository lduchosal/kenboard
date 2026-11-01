"""Runtime facts for the /about page (#1165).

The public part only exposes what is already public (version, licence, links). The admin
part adds the runtime environment: Python, platform, installed dependencies, database
server and migration state. Nothing here reads a secret — no password, token or key ever
reaches the template.
"""

import platform
import re
import sys
from importlib import metadata
from typing import Any

import pymysql

from dashboard import __version__
from dashboard.db import Queries

DIST_NAME = "kenboard"

_REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*([^;]*)")
_REQ_EXTRA = re.compile(r"""extra\s*==\s*["']([^"']+)["']""")


def _installed_version(name: str) -> str | None:
    """Return the installed version of distribution ``name``, or ``None``."""
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def public_info() -> dict[str, Any]:
    """Return the facts any logged-in user may see."""
    return {
        "version": _installed_version(DIST_NAME) or __version__,
        "license": "MIT",
        "repo_url": "https://github.com/lduchosal/kenboard",
        "pypi_url": f"https://pypi.org/project/{DIST_NAME}/",
        "releases_url": "https://github.com/lduchosal/kenboard/releases",
    }


def parse_requirement(req: str) -> dict[str, str | None]:
    """Split a ``Requires-Dist`` entry into name, specifier and extra.

    Args:
        req: A PEP 508 string such as ``gunicorn>=21.0; extra == "prod"``.

    Returns:
        A dict with ``name``, ``spec`` (``""`` when unpinned) and ``extra``
        (``None`` for a core dependency).
    """
    match = _REQ_NAME.match(req)
    name = match.group(1) if match else req.strip()
    spec = match.group(3).strip() if match else ""
    extra_match = _REQ_EXTRA.search(req)
    return {
        "name": name,
        "spec": spec,
        "extra": extra_match.group(1) if extra_match else None,
    }


def dependencies() -> list[dict[str, str | None]]:
    """Return kenboard's declared dependencies with their installed versions.

    Core dependencies come first, then each extra; ``installed`` is ``None`` when the
    package is absent (typically an extra that was not requested).
    """
    try:
        reqs = metadata.requires(DIST_NAME) or []
    except metadata.PackageNotFoundError:
        return []
    deps = []
    for req in reqs:
        dep = parse_requirement(req)
        name = dep["name"] or ""
        dep["installed"] = _installed_version(name)
        deps.append(dep)
    deps.sort(key=lambda d: (d["extra"] is not None, d["extra"] or "", d["name"] or ""))
    return deps


def runtime_info() -> dict[str, str]:
    """Return the Python interpreter and host platform facts."""
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "prefix": sys.prefix,
        "platform": platform.platform(),
        "machine": platform.machine(),
    }


def database_info(conn: pymysql.Connection, queries: Queries) -> dict[str, Any]:
    """Return the database server version and the yoyo migration state.

    Each probe degrades to ``None`` on a database error (e.g. a schema that was never
    migrated by yoyo has no ``_yoyo_migration`` table), so the page always renders.
    """
    info: dict[str, Any] = {"server": None, "migrations": None}
    try:
        info["server"] = queries.about_db_server(conn)
    except pymysql.Error:
        pass
    try:
        info["migrations"] = queries.about_migrations(conn)
    except pymysql.Error:
        pass
    return info

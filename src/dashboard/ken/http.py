"""HTTP client for the ``ken`` CLI.

Talks to the kenboard REST API via the stdlib (no extra HTTP dependency).
"""

from __future__ import annotations

import json as json_lib
import sys
from typing import TYPE_CHECKING, Any
from urllib import error as urllib_error
from urllib import request as urllib_request

import click

from dashboard.ken.config import KenConfig, _version

if TYPE_CHECKING:
    import ssl


def _ssl_context() -> ssl.SSLContext | None:
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
        with urllib_request.urlopen(req, context=_SSL_CTX) as resp:
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

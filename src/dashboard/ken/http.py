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

from dashboard.ken.config import KEN_FILE, KEN_INI_FILE, KenConfig, _version

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


def _default_base_url_hint(cfg: KenConfig) -> str:
    """Explain an unconfigured ``base_url`` when a call fails (#1021).

    ``ken`` searches upward from the cwd for ``.ken``/``ken.ini``. Run it from a
    directory outside the project — a scratch dir holding the ``--desc-file``, say —
    and the search comes up empty, ``base_url`` silently falls back to
    ``http://localhost:9090``, and the write lands on whatever happens to listen
    there. The failure then looks like the board rejecting the request (#1013 was
    filed as a kenboard bug on exactly this basis: an unrelated local service
    answered ``400 Method PATCH not implemented (try POST)``).

    Commands needing a ``project_id`` (``list``, ``add``) fail early on the missing
    config; the ones addressing a task by id (``update``, ``move``, ``done``) have
    nothing to catch them — hence this hint. Empty when a base_url was configured.
    """
    if not cfg.base_url_is_default:
        return ""
    root = cfg.search_root or "the current directory"
    return (
        f"\nHint: no {KEN_FILE} / {KEN_INI_FILE} was found above {root}, so ken used "
        f"its built-in default base_url ({cfg.base_url}) — this request never reached "
        "your board.\n"
        "      Run ken from the project directory (--desc-file accepts an absolute "
        "path), or pass --base-url / set KEN_BASE_URL."
    )


def _request(
    cfg: KenConfig,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
) -> Any:  # noqa: ANN401 — JSON parsé, forme libre
    """Send a JSON request, return parsed response or None on empty body.

    Errors name the full URL, not just the path: knowing *which host* answered is what
    tells a real board error apart from a call that silently went to the default
    localhost fallback (#1021). Applies to every endpoint — this is the CLI's only
    HTTP entry point.
    """
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
        click.echo(
            f"Error: HTTP {e.code} on {method} {url}: {body_text}"
            f"{_default_base_url_hint(cfg)}",
            err=True,
        )
        sys.exit(1)
    except urllib_error.URLError as e:
        click.echo(
            f"Error: cannot reach {url}: {e.reason}{_default_base_url_hint(cfg)}",
            err=True,
        )
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

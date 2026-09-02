"""Parsing of the board's onboarding URL — the bootstrap input of ``ken init``.

An onboarding link carries every coordinate ``ken`` needs, which is what breaks the
chicken-and-egg of ``init``: every other command reads ``.ken`` / ``ken.ini``, the very
files that do not exist yet on a fresh checkout, so an ``init`` driven by the resolved
config would aim at ``DEFAULT_BASE_URL`` (``http://localhost:9090``) and never reach
the board (#1013, #1021).

The link is produced by the *copy onboard link* button of a category page and served
by :mod:`dashboard.onboarding`::

    https://board.example.com/onboard/cat/<cat-id>/project/<project-id>?token=<token>

A path prefix is tolerated (``https://host/kenboard/onboard/cat/…``) so an instance
mounted under a reverse-proxy subpath resolves the right ``base_url``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

import click

ONBOARDING_URL_EXAMPLE = (
    "https://board.example.com/onboard/cat/<cat-id>/project/<project-id>?token=<token>"
)

_HOW_TO_GET_ONE = (
    'Copy it from the board: open the category page, then the "copy onboard link" '
    "button.\n"
    f"Expected shape: {ONBOARDING_URL_EXAMPLE}"
)

_PATH_LENGTH = 5


@dataclass(frozen=True)
class OnboardingLink:
    """The coordinates an onboarding URL carries, ready to be written to disk."""

    base_url: str
    cat_id: str
    project_id: str
    token: str | None


def read_url_argument(raw: str) -> str:
    """Return the URL, reading it from stdin when ``raw`` is ``-``.

    The stdin form keeps a link with a ``?token=`` out of the shell history — the
    token is a live API key, and an inline argument lands in ``~/.zsh_history``.

    Raises:
        UsageError: when stdin is empty or closed.
    """
    if raw != "-":
        return raw.strip()
    data = sys.stdin.read().strip()
    if not data:
        msg = f"no URL on stdin. Pipe the onboarding link in:\n{_HOW_TO_GET_ONE}"
        raise click.UsageError(msg)
    return data.splitlines()[0].strip()


def _split_onboard_path(segments: list[str]) -> tuple[list[str], str, str] | None:
    """Split ``[…, onboard, cat, X, project, Y]`` into ``(prefix, cat, project)``."""
    if len(segments) < _PATH_LENGTH:
        return None
    prefix, tail = segments[:-_PATH_LENGTH], segments[-_PATH_LENGTH:]
    if [tail[0], tail[1], tail[3]] != ["onboard", "cat", "project"]:
        return None
    if not tail[2] or not tail[4]:
        return None
    return prefix, tail[2], tail[4]


def parse_onboarding_url(raw: str) -> OnboardingLink:
    """Extract ``base_url``, ids and token from an onboarding URL.

    Nothing here consults the config chain: the URL is the sole source of truth, which
    is the whole point of ``ken init``.

    Raises:
        UsageError: when the argument is not a kenboard onboarding URL — a bare
            project id and a board page URL both land here, each with the hint that
            names what to paste instead.
    """
    url = raw.strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        msg = (
            f"`ken init` takes the board's onboarding URL, not {url!r}.\n"
            f"{_HOW_TO_GET_ONE}"
        )
        raise click.UsageError(msg)

    split = _split_onboard_path([seg for seg in parts.path.split("/") if seg])
    if split is None:
        msg = f"{url} is not an onboarding URL.\n{_HOW_TO_GET_ONE}"
        raise click.UsageError(msg)
    prefix, cat_id, project_id = split

    base_url = f"{parts.scheme}://{parts.netloc}"
    if prefix:
        base_url += "/" + "/".join(prefix)
    token = parse_qs(parts.query).get("token", [""])[0].strip()
    return OnboardingLink(
        base_url=base_url.rstrip("/"),
        cat_id=cat_id,
        project_id=project_id,
        token=token or None,
    )

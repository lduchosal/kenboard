"""Machine-readable onboarding hints for un-authenticated requests.

When a CLI tool, an LLM agent, or any non-browser client follows a kenboard
URL without credentials we want them to learn — without reverse-engineering
the HTML login page — that there is a ``ken`` CLI to install, that they need
a category ID and an API key, and where to get the key. The text and JSON
payloads built here are returned by both the cookie auth handler
(``auth_user._unauthorized``) and the API auth middleware (``auth._enforce``)
so an agent that hits *any* protected URL gets a copy-pasteable runbook
instead of a useless redirect or a one-line ``"missing Authorization"``.
"""

from __future__ import annotations

import re
from typing import Any

from flask.wrappers import Request

# UUID-ish pattern is loose on purpose: we only use the captured value as a
# placeholder in the rendered command, never as a DB key, so a tighter regex
# only buys us a worse user experience on copy-pasted weird IDs.
_CAT_URL_RE = re.compile(r"^/cat/([^/]+)\.html$")


def cat_id_from_path(path: str) -> str | None:
    """Return the category id embedded in a ``/cat/<id>.html`` path, or None.

    Used to render an explicit ``cat_id=<uuid>`` line in the onboarding
    runbook when the agent landed on a category page directly. The matching
    ``project_id`` lives in the URL fragment which the server never receives
    (HTTP clients drop ``#fragment`` before sending), so the runbook
    instructs the agent to copy the project id from the original URL the
    user shared with it.
    """
    m = _CAT_URL_RE.match(path)
    return m.group(1) if m else None


def wants_machine_response(request_obj: Request) -> bool:
    """Return True when the caller is most likely not a graphical browser.

    Heuristic: graphical browsers always advertise ``text/html`` in their
    ``Accept`` header. CLI tools (curl, httpie, the stdlib HTTP client that
    powers ``ken``) and library defaults (``requests``, ``httpx``, the
    fetch / WebFetch tools used by AI agents) usually emit ``Accept: */*``.
    We treat ``Accept`` set, but without ``text/html``, as the agent
    signal. ``Accept`` *absent* (Werkzeug test client, some embedded HTTP
    stacks) is treated as browser to keep the cookie flow stable for the
    unit-test suite — real agents virtually always emit *some* ``Accept``.
    """
    accept = request_obj.headers.get("Accept")
    if accept is None:
        return False
    return "text/html" not in accept


def onboarding_text(cat_id: str | None) -> str:
    """Render the agent-facing 401 body as plain text.

    The runbook lists *both* identifiers — ``cat_id`` (which the server
    sees in the path and can interpolate) and ``project_id`` (which lives
    in the URL fragment and must be copied by the agent from the original
    URL the user shared). The agent is then instructed to write a 4-line
    ``.ken`` file directly, side-stepping ``ken init`` (which is admin-only
    on the listing endpoint and would fail for a per-project token).
    """
    cat_value = cat_id or "<paste the UUID between /cat/ and .html>"
    return (
        "Unauthorized — you are accessing a kenboard project board "
        "without credentials.\n"
        "\n"
        "The URL the user gave you has the form:\n"
        "    https://<host>/cat/<CAT_ID>.html#<PROJECT_ID>\n"
        f"      cat_id     = {cat_value}\n"
        "      project_id = <UUID after `#` in the original URL>\n"
        "\n"
        "HTTP clients drop the URL fragment before sending the request, so\n"
        "this server only sees the cat_id; the project_id must be read\n"
        "from the original URL the user shared with you.\n"
        "\n"
        "To use this board programmatically:\n"
        "\n"
        "  1. Install the kenboard package (ships the `ken` binary):\n"
        "         pip install kenboard\n"
        "\n"
        "  2. Create a `.ken` file (mode 0600) in your project root with:\n"
        "\n"
        f"         cat_id={cat_value}\n"
        "         project_id=<UUID after `#` in the original URL>\n"
        "         base_url=https://www.kenboard.2113.ch\n"
        "         api_token=<API key the user generates at /admin/keys>\n"
        "\n"
        "  3. Ask the user to generate an API key at /admin/keys (with at\n"
        "     least `read` scope on this project) and paste it into the\n"
        "     `api_token=` line.\n"
        "\n"
        "  4. Then query the board:\n"
        "         ken list --status todo --json\n"
        "         ken show <id> --json\n"
        "         ken add 'Title' --desc '...' --who Claude --status todo\n"
        "\n"
        "Browser users: log in at /login.\n"
    )


def onboarding_json(cat_id: str | None) -> dict[str, Any]:
    """Render the agent-facing 401 body as a JSON-friendly dict.

    Same content as ``onboarding_text`` but structured so an SDK can
    extract individual fields without parsing free-form prose. The
    ``project_id`` field is intentionally a placeholder string instead of
    ``null`` so a naïve JSON-to-template substitution still produces a
    visible marker the user notices and replaces.
    """
    cat_value = cat_id or "<paste the UUID between /cat/ and .html>"
    return {
        "error": "unauthorized",
        "message": (
            "kenboard requires authentication for programmatic access — "
            "see `onboarding` below for the runbook"
        ),
        "onboarding": {
            "url_format": "https://<host>/cat/<CAT_ID>.html#<PROJECT_ID>",
            "note": (
                "HTTP clients drop the URL fragment, so this server only "
                "sees the cat_id; copy the project_id from the original "
                "URL the user shared with you (the part after `#`)."
            ),
            "install": "pip install kenboard",
            "ken_file": {
                "path": ".ken (mode 0600 in your project root)",
                "lines": [
                    f"cat_id={cat_value}",
                    "project_id=<UUID after `#` in the original URL>",
                    "base_url=https://www.kenboard.2113.ch",
                    "api_token=<API key from /admin/keys>",
                ],
            },
            "cat_id": cat_id,
            "project_id": "<UUID after `#` in the original URL>",
            "get_api_key": "/admin/keys",
            "next_steps": [
                "ken list --status todo --json",
                "ken show <id> --json",
                "ken add 'Title' --desc '...' --who Claude --status todo",
            ],
        },
    }

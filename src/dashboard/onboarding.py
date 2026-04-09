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

    Used to interpolate the right ``ken init <id>`` command into the
    onboarding hint when the agent landed on a category page directly. Any
    other path (api endpoints, admin pages, root) yields ``None`` and the
    rendered command falls back to the ``<category-id>`` placeholder.
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
    """Render the agent-facing 401 body as plain text."""
    init_arg = cat_id or "<category-id>"
    return (
        "Unauthorized — you are accessing a kenboard project board "
        "without credentials.\n"
        "\n"
        "To use this board programmatically, install and configure the "
        "ken CLI:\n"
        "\n"
        "  1. Install the kenboard package (ships the `ken` binary):\n"
        "     pip install kenboard\n"
        "\n"
        f"  2. Initialise this project (writes a `.ken` file mode 0600):\n"
        f"     ken init {init_arg}\n"
        "\n"
        "  3. Ask the user for an API key generated at /admin/keys and\n"
        "     paste it into `.ken` next to `api_token=`.\n"
        "\n"
        "  4. Then query the board:\n"
        "     ken list --status todo --json\n"
        "     ken show <id> --json\n"
        "     ken add 'Title' --desc '...' --who Claude --status todo\n"
        "\n"
        "Browser users: log in at /login.\n"
    )


def onboarding_json(cat_id: str | None) -> dict[str, Any]:
    """Render the agent-facing 401 body as a JSON-friendly dict.

    Same content as ``onboarding_text`` but structured so an SDK can
    extract individual fields without parsing free-form prose.
    """
    init_arg = cat_id or "<category-id>"
    return {
        "error": "unauthorized",
        "message": (
            "kenboard requires authentication for programmatic access — "
            "see `onboarding` below for the install / init runbook"
        ),
        "onboarding": {
            "install": "pip install kenboard",
            "init": f"ken init {init_arg}",
            "get_api_key": "/admin/keys",
            "category_id": cat_id,
            "next_steps": [
                "ken list --status todo --json",
                "ken show <id> --json",
                "ken add 'Title' --desc '...' --who Claude --status todo",
            ],
        },
    }

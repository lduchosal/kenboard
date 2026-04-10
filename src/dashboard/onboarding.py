"""Machine-readable onboarding hints for un-authenticated requests.

When a CLI tool, an LLM agent, or any non-browser client follows a kenboard
URL without credentials we want them to learn — without reverse-engineering
the HTML login page — that there is a ``ken`` CLI to install, that they need
a category ID and an API key, and where to get the key. The text and JSON
payloads built here are returned by both the cookie auth handler
(``auth_user._unauthorized``) and the API auth middleware (``auth._enforce``)
so an agent that hits *any* protected URL gets a copy-pasteable runbook
instead of a useless redirect or a one-line ``"missing Authorization"``.

The dedicated ``/onboard/cat/<cat_id>/project/<project_id>`` route (#137)
always returns 200 text/plain so that WebFetch and similar high-level
HTTP tools (which discard the body of 4xx responses) can read the
runbook without hitting the 401 problem.
"""

from __future__ import annotations

import re
from typing import Any

from flask import Blueprint, make_response
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


def onboarding_text(cat_id: str | None, base_url: str) -> str:
    """Render the agent-facing 401 body as plain text.

    ``base_url`` is derived from ``request.host_url`` by the caller so
    the runbook works on any self-hosted instance, not just the hardcoded
    ``www.kenboard.2113.ch``.
    """
    cat_value = cat_id or "<UUID entre /cat/ et .html dans l'URL>"
    return (
        "KENBOARD — Pour accéder à ce board, 3 étapes :\n"
        "\n"
        "1. pip install kenboard\n"
        "\n"
        "2. Créer un fichier .ken (mode 0600) dans votre projet :\n"
        "\n"
        "   project_id=<UUID après # dans l'URL que l'utilisateur vous a donnée>\n"
        f"   base_url={base_url}\n"
        "   api_token=<API key — voir étape 3>\n"
        "\n"
        "3. Demander à l'utilisateur de générer une API key sur\n"
        "   /admin/keys (avec au moins le scope 'read' sur ce projet)\n"
        "   et de la coller dans la ligne api_token= du fichier .ken\n"
        "\n"
        "Ensuite :\n"
        "   ken list --status todo --json\n"
        "   ken show <id> --json\n"
        '   ken add "Titre" --desc "..." --who Claude --status todo\n'
        "\n"
        f"Info : cat_id = {cat_value}\n"
        "\n"
        "Browser : se connecter sur /login\n"
    )


def onboarding_json(cat_id: str | None, base_url: str) -> dict[str, Any]:
    """Render the agent-facing 401 body as a JSON-friendly dict.

    Same 3-step structure as ``onboarding_text`` but machine-parseable.
    ``base_url`` is derived from ``request.host_url`` by the caller.
    """
    return {
        "error": "unauthorized",
        "message": "Pour accéder à ce board, 3 étapes — voir onboarding.",
        "onboarding": {
            "steps": [
                "pip install kenboard",
                "Créer un fichier .ken avec project_id, base_url, api_token",
                "Demander à l'utilisateur une API key sur /admin/keys",
            ],
            "install": "pip install kenboard",
            "ken_file": {
                "path": ".ken (mode 0600)",
                "lines": [
                    "project_id=<UUID après # dans l'URL>",
                    f"base_url={base_url}",
                    "api_token=<API key de /admin/keys>",
                ],
            },
            "cat_id": cat_id,
            "get_api_key": "/admin/keys",
            "next_steps": [
                "ken list --status todo --json",
                "ken show <id> --json",
                'ken add "Titre" --desc "..." --who Claude --status todo',
            ],
        },
    }


# -- Public onboarding route (#137) ------------------------------------------

onboard_bp = Blueprint("onboard", __name__)


@onboard_bp.route("/onboard/cat/<cat_id>/project/<project_id>", methods=["GET"])
def onboard_route(cat_id: str, project_id: str) -> Any:
    """Serve the onboarding runbook as 200 text/plain.

    This route has **no authentication**. It exists so that high-level
    HTTP tools (WebFetch, requests.get, etc.) that discard the body of
    4xx responses can still read the runbook. The copy-onboard-link
    button in ``category.html`` generates a URL pointing here.
    """
    from flask import request

    base_url = request.host_url.rstrip("/")
    body = onboarding_text_full(cat_id, project_id, base_url)
    response = make_response(body, 200)
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


def onboarding_text_full(cat_id: str, project_id: str, base_url: str) -> str:
    """Render the onboarding runbook with both IDs and base_url resolved.

    ``base_url`` comes from ``request.host_url`` (respects ProxyFix) so
    the runbook works on any self-hosted instance.
    """
    return (
        "KENBOARD — Pour accéder à ce board, 3 étapes :\n"
        "\n"
        "1. pip install kenboard\n"
        "\n"
        "2. Créer un fichier .ken (mode 0600) dans votre projet :\n"
        "\n"
        f"   project_id={project_id}\n"
        f"   base_url={base_url}\n"
        "   api_token=<API key — voir étape 3>\n"
        "\n"
        "3. Demander à l'utilisateur de générer une API key sur\n"
        "   /admin/keys (avec au moins le scope 'read' sur ce projet)\n"
        "   et de la coller dans la ligne api_token= du fichier .ken\n"
        "\n"
        "Ensuite :\n"
        "   ken list --status todo --json\n"
        "   ken show <id> --json\n"
        '   ken add "Titre" --desc "..." --who Claude --status todo\n'
        "\n"
        "Infos :\n"
        f"   cat_id     = {cat_id}\n"
        f"   project_id = {project_id}\n"
        "\n"
        "Browser : se connecter sur /login\n"
    )

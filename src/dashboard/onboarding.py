"""Machine-readable onboarding hints for un-authenticated requests.

When a CLI tool, an LLM agent, or any non-browser client follows a kenboard URL without
credentials we want them to learn — without reverse-engineering the HTML login page —
that there is a ``ken`` CLI to install, that they need a category ID and an API key, and
where to get the key. The text and JSON payloads built here are returned by both the
cookie auth handler (``auth_user._unauthorized``) and the API auth middleware
(``auth._enforce``) so an agent that hits *any* protected URL gets a copy-pasteable
runbook instead of a useless redirect or a one-line ``"missing Authorization"``.

The dedicated ``/onboard/cat/<cat_id>/project/<project_id>`` route (#137) always returns
200 text/plain so that WebFetch and similar high-level HTTP tools (which discard the
body of 4xx responses) can read the runbook without hitting the 401 problem — it lives
in :mod:`dashboard.onboarding_runbook`, along with the long-form runbook it serves.
"""

from __future__ import annotations

import re
from typing import Any

from flask import request
from flask.wrappers import Request

from dashboard.config import Config

# UUID-ish pattern is loose on purpose: we only use the captured value as a
# placeholder in the rendered command, never as a DB key, so a tighter regex
# only buys us a worse user experience on copy-pasted weird IDs.
_CAT_URL_RE = re.compile(r"^/cat/([^/]+)\.html$")

# Strip anything that is not alphanumeric or a hyphen to prevent reflected
# XSS / injection when interpolating user-controlled path segments into
# the onboarding response body (cf. sonar pythonsecurity:S5131).
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9\-]")


def derive_base_url() -> str:
    """Return the public base URL of this kenboard instance.

    Uses ``request.host_url`` (which respects ProxyFix when nginx sends ``X-Forwarded-
    Proto``). As a fallback for proxies that do NOT forward the header,
    ``Config.KENBOARD_HTTPS`` forces the scheme to ``https`` so the onboarding runbook
    and OIDC redirect_uri are always correct behind a TLS-terminating reverse proxy
    (#147).
    """
    url = request.host_url.rstrip("/")
    if Config.KENBOARD_HTTPS and url.startswith("http://"):
        url = "https://" + url[7:]
    return url


def _sanitize_token(value: str) -> str:
    """Strip anything that is not a valid kenboard token character.

    Tokens are ``kb_`` + base64url (alphanumeric, ``-``, ``_``).
    """
    return re.sub(r"[^a-zA-Z0-9_\-]", "", value)


def _sanitize_id(value: str) -> str:
    """Strip non-UUID characters from a user-supplied identifier.

    Prevents reflected XSS when the value is interpolated into the onboarding response
    body (pythonsecurity:S5131).
    """
    return _SAFE_ID_RE.sub("", value)


def cat_id_from_path(path: str) -> str | None:
    """Return the category id embedded in a ``/cat/<id>.html`` path, or None.

    Used to render an explicit ``cat_id=<uuid>`` line in the onboarding runbook when the
    agent landed on a category page directly. The matching ``project_id`` lives in the
    URL fragment which the server never receives (HTTP clients drop ``#fragment`` before
    sending), so the runbook instructs the agent to copy the project id from the
    original URL the user shared with it.
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

    ``base_url`` is derived from ``request.host_url`` by the caller so the runbook works
    on any self-hosted instance, not just the hardcoded ``www.kenboard.2113.ch``.
    """
    cat_value = cat_id or "<UUID entre /cat/ et .html dans l'URL>"
    return (
        "KENBOARD — Pour accéder à ce board, 3 étapes :\n"
        "\n"
        "Pré-requis : Python 11+ et un virtualenv :\n"
        "   python3 -m venv .venv && source .venv/bin/activate\n"
        "\n"
        "1. pip install kenboard\n"
        "\n"
        "2. Créer un fichier .ken (mode 0600) dans votre projet :\n"
        "\n"
        "   Le plus simple, si l'utilisateur vous a donné un lien d'onboarding\n"
        "   (.../onboard/cat/<cat>/project/<projet>?token=...) :\n"
        "\n"
        '       ken init "<ce lien>"      # ou : ken init -   (URL sur stdin)\n'
        "\n"
        "   Il écrit ken.ini (versionné) + .ken (0600, ajouté au .gitignore).\n"
        "\n"
        "   À la main :\n"
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
        "   ken move <id> --to review     # quand fini\n"
        "   ken wiki groom <id> <section> # classifier pour le wiki\n"
        "\n"
        f"Info : cat_id = {cat_value}\n"
        "\n"
        "Browser : se connecter sur /login\n"
    )


def onboarding_json(cat_id: str | None, base_url: str) -> dict[str, Any]:
    """Render the agent-facing 401 body as a JSON-friendly dict.

    Same 3-step structure as ``onboarding_text`` but machine-parseable. ``base_url`` is
    derived from ``request.host_url`` by the caller.
    """
    return {
        "error": "unauthorized",
        "message": "Pour accéder à ce board, 3 étapes — voir onboarding.",
        "onboarding": {
            "prerequisites": "Python 11+ et un virtualenv (python3 -m venv .venv)",
            "steps": [
                "pip install kenboard",
                "Créer un fichier .ken avec project_id, base_url, api_token",
                "Demander à l'utilisateur une API key sur /admin/keys",
            ],
            "install": "pip install kenboard",
            "ken_init": (
                'ken init "<lien /onboard/cat/<cat>/project/<projet>?token=...>" '
                "— écrit ken.ini + .ken ; `ken init -` lit l'URL sur stdin"
            ),
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
                "ken move <id> --to review  # then ken wiki groom <id> <section>",
            ],
        },
    }

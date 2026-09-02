"""The full onboarding runbook and its public route (#137).

Split out of :mod:`dashboard.onboarding`, which keeps the 401 hints and the shared
sanitizers. This module holds the long-form runbook — the one an agent reads at
``/onboard/cat/<cat_id>/project/<project_id>`` — because it is mostly template text and
grows with every workflow change.

The route has **no authentication**: high-level HTTP tools (WebFetch, ``requests``)
discard the body of 4xx responses, so the runbook needs a 200 to reach them.
"""

from __future__ import annotations

from flask import Blueprint, make_response, request
from flask.typing import ResponseReturnValue

from dashboard.onboarding import _sanitize_id, _sanitize_token, derive_base_url

# -- Public onboarding route (#137) ------------------------------------------

onboard_bp = Blueprint("onboard", __name__)


@onboard_bp.route("/onboard/cat/<cat_id>/project/<project_id>", methods=["GET"])
def onboard_route(cat_id: str, project_id: str) -> ResponseReturnValue:
    """Serve the onboarding runbook as 200 text/plain.

    This route has **no authentication**. It exists so that high-level HTTP tools
    (WebFetch, requests.get, etc.) that discard the body of 4xx responses can still read
    the runbook. The copy-onboard-link button in ``category.html`` generates a URL
    pointing here.

    When ``?token=`` is present (#159), the runbook includes the token in the ``.ken``
    file so the agent can start immediately without asking the user for an API key.
    """
    safe_cat = _sanitize_id(cat_id)
    safe_project = _sanitize_id(project_id)
    token = request.args.get("token", "")
    body = onboarding_text_full(safe_cat, safe_project, derive_base_url(), token)
    response = make_response(body, 200)
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


# Static middle section of the full runbook — everything that doesn't depend
# on the category/project/token of the URL.
_RUNBOOK_GUIDE = (
    "## 3. Travailler\n"
    "\n"
    "   ken list --who Claude --status todo --json\n"
    "   ken show <id> --json\n"
    '   ken add "MODULE / Titre" --desc "..." --who Claude --status todo\n'
    "   ken move <id> --to doing\n"
    "   ken move <id> --to review\n"
    '   ken update <id> --desc "<original>\\n\\n---\\n\\n## Résolution\\n..."\n'
    "   ken wiki groom <id> <section>   # classifier après review\n"
    "\n"
    "Références :\n"
    "   ken --help     commandes disponibles\n"
    "   ken help       guide des bonnes pratiques agent\n"
    "\n"
    "## Bonnes pratiques\n"
    "\n"
    "- Workflow : todo → doing → review → groom → done\n"
    "  L'agent gère todo → doing → review puis ken wiki groom.\n"
    "  Seul l'utilisateur passe review → done.\n"
    "\n"
    "- Titres de tâches : MODULE / Titre\n"
    "  AUTH, BUG, CLEAN, SEC, UI, DOC, QUALITY, AGENT, FIX\n"
    "\n"
    "- Avant de passer en review :\n"
    "  ken move <id> --to review\n"
    "  ken update <id> --desc (ajouter Résolution : Modifications,\n"
    "  Comportements obtenus, Garde-fous)\n"
    "\n"
    "- Toujours utiliser --json quand on parse la sortie\n"
    "- Ne jamais marquer une tâche done soi-même\n"
    "- .ken est gitignored (contient un token), ne jamais le committer\n"
    "\n"
)


def _token_section(token: str) -> tuple[str, str]:
    """``(ligne api_token, étape 3)`` du runbook — selon qu'un token est fourni."""
    if token:
        step3 = (
            "3. Le token API est déjà inclus ci-dessus. Vous pouvez\n"
            "   commencer à travailler immédiatement.\n"
        )
        return f"api_token={_sanitize_token(token)}\n", step3
    step3 = (
        "3. Demander à l'utilisateur de générer une API key sur\n"
        "   /admin/keys (avec au moins le scope 'read' sur ce projet)\n"
        "   et de la coller dans la ligne api_token= du fichier .ken\n"
    )
    return "api_token=<API key — voir étape 3>\n", step3


def _configure_section(
    cat_id: str, project_id: str, base_url: str, token: str, token_line: str
) -> str:
    """Render step 2 — ``ken init`` first, the hand-written ``.ken`` as fallback.

    The runbook is served at the very URL that bootstraps the repo, so the command is
    printed already filled in (#1089). The manual block stays underneath: it is what
    still works when ``ken`` is too old to know ``init``, or when the agent cannot reach
    the network from where it runs.
    """
    onboard_url = f"{base_url}/onboard/cat/{cat_id}/project/{project_id}"
    if token:
        onboard_url += f"?token={_sanitize_token(token)}"
    return (
        "## 2. Configurer\n"
        "\n"
        f'   ken init "{onboard_url}"\n'
        "\n"
        "Ou, pour garder le token hors de l'historique du shell :\n"
        "\n"
        "   ken init -        puis coller cette URL\n"
        "\n"
        "Écrit ken.ini (versionné : project_id, base_url, description et les\n"
        "chemins du wiki) et .ken (mode 0600, ajouté au .gitignore : api_token).\n"
        "\n"
        "Sans ken init (version trop ancienne, pas de réseau) :\n"
        "\n"
        "Copier tel quel dans un fichier .ken :\n"
        "\n"
        f"cat_id={cat_id}\n"
        f"project_id={project_id}\n"
        f"base_url={base_url}\n" + token_line.lstrip()
    )


def onboarding_text_full(
    cat_id: str, project_id: str, base_url: str, token: str = ""
) -> str:
    """Render the onboarding runbook with both IDs and base_url resolved.

    ``base_url`` comes from ``request.host_url`` (respects ProxyFix) so the runbook
    works on any self-hosted instance. When ``token`` is provided (#159), the ``.ken``
    file is complete and the agent can start immediately.
    """
    token_line, step3 = _token_section(token)
    return (
        "# KENBOARD\n"
        "\n"
        "## Pré-requis\n"
        "\n"
        "Python 11 ou supérieur est requis.\n"
        "Créer un virtualenv avant d'installer :\n"
        "\n"
        "   python3 -m venv .venv\n"
        "   source .venv/bin/activate\n"
        "\n"
        "## 1. Installer\n"
        "\n"
        "   pip install kenboard\n"
        "\n"
        + _configure_section(cat_id, project_id, base_url, token, token_line)
        + "\n"
        + step3
        + "\n"
        + _RUNBOOK_GUIDE
        + "---\n"
        f"cat_id={cat_id}  project_id={project_id}\n"
        f"base_url={base_url}\n"
        + (f"api_token={_sanitize_token(token)}\n" if token else "")
        + "Browser : /login\n"
    )

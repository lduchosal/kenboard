---
id: 268
title: "SYS / Fatal error"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:56
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend
section_title: "Backend (Flask / Python)"
---

# #268 — SYS / Fatal error

## Demande

Quand une erreur fatale survient, la page d'erreur devrait avoir un joli message qui dit \"Une erreur fatale est survenue\" avec un code d'erreur indiquant le type de problème.

Actuellement, une erreur 500 est lancée, sans page friendly.

---

## Résolution

### Modifications

- `src/dashboard/templates/error_fatal.html` : nouveau template **standalone** (n'étend pas `base.html` pour rester rendable même si la DB est down). Card centrée avec icône warning rouge, titre \"Une erreur fatale est survenue\", code HTTP + classe d'exception + référence `E-<hex-time>-<4-hex>`, boutons \"Retour à l'accueil\" / \"Réessayer\".
- `src/dashboard/static/style.css` : styles `.error-fatal*` (card, meta-rows, ref monospace).
- `src/dashboard/app.py` :
  - Le handler `Exception` génère un id de corrélation court (`E-<hex-time>-<4-hex>`), loggé via structlog avec le champ `error_id`. L'admin peut grep le log avec la référence rapportée par l'utilisateur pour pull le traceback complet.
  - Content negotiation : path sous `/api/` ou `Accept: application/json` → réponse JSON `{error: \"Internal server error\", error_id}` (préserve le flow `apiCall` côté client). Sinon → HTML friendly.
  - Helper `_wants_json(request)` factorise la décision.

### Tests (4 nouveaux dans `tests/unit/test_fatal_error.py`)

- HTML caller (Accept: text/html) → page friendly avec titre + status + ref id (regex E-<hex>-<4hex>)
- `/api/` caller → JSON shape avec `error_id`
- Accept: application/json hors /api/ → JSON
- HTTPException (404) passe à travers (pas swallow)

### Garde-fous

- `pdm run check` : 393 passed (389 + 4 nouveaux)
- `pdm run test-e2e` : 52 passed / 0 failed
- mypy / ruff / interrogate / vulture : clean
---

[← retour à backend](index.md) · [voir log](../log.md)

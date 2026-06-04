---
id: 415
title: "WIKI / ken wiki groom (#376b)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:24:21
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #415 — WIKI / ken wiki groom (#376b)

Sous-tâche B de #376. Chunk A (#412) a livré la DB + helpers ; ici on expose la surface CLI agent-driven pour la classification.

## À livrer

CLI `ken wiki groom` — agent-driven, pas d'API LLM dans ken.

Commandes :

- `ken wiki groom` (no args) → liste structurée pour l'agent :
  - tâches non classifiées (id, status, who, title) — depuis `wiki_get_unclassified_tasks`
  - sections disponibles — depuis `parse_architecture('./ARCHITECTURE.md')` (path par défaut, override via --architecture)
  - instructions pour appeler la commande suivante
- `ken wiki groom <id> <section>` → assigne ; valide section contre `section_paths(parse_architecture(...))` ; UsageError si section inconnue
- `ken wiki groom <id> --show` → affiche la classification actuelle
- `ken wiki groom <id> --clear` → drop
- `ken wiki groom --help` → explique le pattern Karpathy + lien gist + heuristiques pour l'agent

Options :
- `--architecture PATH` (default `./ARCHITECTURE.md`)
- `--base-url`, `--api-token`, `--project` héritées du group `cli` parent

`classified_by` resolves à l'API token user ou à `os.environ['USER']` si pas de token.

## Tests

`tests/unit/test_ken.py::TestCliGroom` couvre :
- groom no-args avec ARCHITECTURE valide → liste + sections
- groom no-args sans ARCHITECTURE → message d'erreur explicite
- groom <id> <valid-section> → POST/PATCH approprié, affiche confirmation
- groom <id> <unknown-section> → UsageError listant les sections valides
- groom <id> --show → affiche la classif ou "unclassified"
- groom <id> --clear → DELETE
- groom --help → texte contient le lien gist Karpathy

## Hors scope

Pas de sync (chunk C), pas de build (D), pas de lint (E).

---

## Résolution

### Modifications

- `src/dashboard/routes/wiki.py` *(nouveau)* — Blueprint Flask `/api/v1/wiki` avec 4 endpoints :
  `GET /unclassified` (filtre `?project=` optionnel), `GET /classify/<id>`,
  `POST /classify`, `DELETE /classify/<id>`. Toutes les routes vérifient
  `current_user_can_project` ; le serveur stocke `section_path` comme chaîne opaque
  (la validation contre `ARCHITECTURE.md` est faite côté CLI, séparation des
  préoccupations).
- `src/dashboard/routes/__init__.py`, `src/dashboard/app.py` — enregistrement du
  nouveau blueprint `wiki_bp`.
- `src/dashboard/ken.py` — nouveau group `wiki` + commande `groom` avec :
  - `groom` (no args) → JSON ou texte listant tâches non classifiées + sections
    disponibles depuis `ARCHITECTURE.md` + instructions agent.
  - `groom <id> <section>` → valide la section localement contre les sections
    parsées, POST `/api/v1/wiki/classify`.
  - `groom <id> --show` / `--clear` → GET / DELETE.
  - `--help` cite explicitement le gist Karpathy
    (https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) et
    explique le pattern WHAT/WORKFLOW.
- `tests/unit/test_wiki_routes.py` *(nouveau)* — 12 tests sur les 4 endpoints,
  avec fixture `_ensure_login_disabled` autouse pour isoler des autres modules
  qui toggle `LOGIN_DISABLED`.
- `tests/unit/test_ken.py::TestCliGroom` — 9 tests CLI (no-args, classify,
  validation, show, clear, mutually exclusive flags, help mentionne gist,
  fallback sans ARCHITECTURE).

### Comportements obtenus

- Agent peut appeler `ken wiki groom` pour découvrir le travail à faire sans
  connaissance préalable de l'architecture.
- Classification opaque côté serveur — pas de couplage entre la DB et le
  fichier `ARCHITECTURE.md`.
- Audit trail via `classified_at` + `classified_by` (depuis le user du token
  API ou Flask-Login).
- Cascade ON DELETE : supprimer une tâche supprime sa classification.

### Garde-fous

- `pdm run check` : OK (429 tests unit + 10 vitest, lint, typecheck,
  interrogate, format).
- 21 nouveaux tests passent en isolation **et** dans la suite complète.
- Aucun changement de schéma DB (livré en chunk A #412).
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-05-24.md)

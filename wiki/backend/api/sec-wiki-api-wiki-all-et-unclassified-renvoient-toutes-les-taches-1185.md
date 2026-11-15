---
id: 1185
title: "SEC / Wiki API : /wiki/all et /unclassified renvoient toutes les tâches"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:03
classified_at: 2026-11-15T18:44:56
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/api
section_title: "REST API"
---

# #1185 — SEC / Wiki API : /wiki/all et /unclassified renvoient toutes les tâches

**TL;DR** — `/api/v1/wiki/all` et `/unclassified` renvoyaient les tâches de tout le board à n'importe quel compte connecté → les listes sont filtrées sur les projets que l'appelant peut lire.

---

Issu de l'audit #1183 (H2). Sans ?project=, routes/wiki.py ne filtre pas par scope pour une session cookie non admin : tout compte connecté lit titres et descriptions de tout le board.

---

## Résolution

### Modifications

- `src/dashboard/auth_scopes.py` — `visible_project_ids()` : `None` (pas de filtre) pour admin / clé API / mode test, sinon l'ensemble des projets des catégories où l'utilisateur a un scope.
- `src/dashboard/routes/wiki.py` — `_scoped_rows()` appliqué aux deux listings (filtre `?project=` puis filtre de scope).
- `tests/unit/test_sec_audit.py::TestWikiListingScopes` — 4 tests.

### Comportements obtenus

- Un utilisateur avec un scope sur la catégorie A ne reçoit que les lignes de A.
- Un utilisateur sans aucun scope reçoit des listes vides.
- Un admin garde la vue complète ; les clés API restent soumises au `?project=` imposé par le middleware.

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/api](index.md) · [voir log](../../log/2026-11-15.md)

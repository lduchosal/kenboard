---
id: 1187
title: "SEC / Clés API : écriture hors du projet autorisé"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:05
classified_at: 2026-11-15T18:45:03
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1187 — SEC / Clés API : écriture hors du projet autorisé

**TL;DR** — Une clé API `write` sur un projet pouvait déplacer une tâche vers un projet étranger, changer son projet de catégorie et réordonner d'autres projets → les routes vérifient le scope de la clé sur la destination.

---

Issu de l'audit #1183 (H4). current_user_can* renvoie toujours True pour une clé API : une clé write sur A peut déplacer une tâche vers B, changer son projet de catégorie, et réordonner des projets étrangers via project_order.

---

## Résolution

### Modifications

- `src/dashboard/auth_scopes.py` — `current_user_can_project()` contrôle le scope réel de la clé sur le projet demandé (`_api_key_id`, `_project_scope_for_key`) ; `current_user_can()` refuse les clés par projet (elles n'ont aucun scope de catégorie). La clé admin statique garde tous les droits.
- `src/dashboard/routes/projects.py` — `reorder_projects()` : `project_order` n'agit que sur les projets de la catégorie concernée.
- `src/dashboard/routes/categories.py` — utilise `reorder_projects()`.
- `doc/api-keys.md` — règle documentée.
- `tests/unit/test_sec_audit.py::TestApiKeyStaysInScope` — 6 tests.

### Comportements obtenus

- `PATCH /api/v1/tasks/<id>` avec un `project_id` hors scope → 403 ; `read` sur la destination ne suffit pas ; `write` sur les deux projets → autorisé.
- `PATCH /api/v1/projects/<id>` avec `cat` → 403 pour une clé par projet.
- `project_order` ignore les projets d'autres catégories.
- Le CRUD ordinaire d'une clé dans son projet est inchangé (test de non-régression, `ken init` et e2e verts).

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-15.md)

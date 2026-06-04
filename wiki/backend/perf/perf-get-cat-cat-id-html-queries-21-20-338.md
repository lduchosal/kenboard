---
id: 338
title: "PERF / GET /cat/<cat_id>.html / queries 21 > 20"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:01
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #338 — PERF / GET /cat/<cat_id>.html / queries 21 > 20

## Demande

Performance issue on `GET /cat/<cat_id>.html` : 21 queries > 20 budget. Trace montre N+1 typique : `task_get_by_project` ET `burndown_get_by_project` appelés une fois par projet de la catégorie.

---

## Résolution

### Modifications

- `src/dashboard/queries/tasks.sql` : nouvelle `task_get_by_category` qui retourne toutes les tâches de tous les projets d'une catégorie en une seule requête, triées par project_id puis position.
- `src/dashboard/queries/burndown.sql` : nouvelle `burndown_get_for_category_projects` qui retourne toutes les snapshots des projets d'une catégorie sur N jours, triées par project_id puis date.
- `src/dashboard/routes/pages.py:category()` : remplace les deux boucles `for p in cat_projects: queries.task_get_by_project / burndown_get_by_project` par deux requêtes batched + regroupement Python dans `tasks_by_project` et `snapshots_by_project`. Strip du `project_id` dans les snapshots groupées pour matcher la shape attendue par `partials/burndown.html`.

### Comportements obtenus

- **Avant** : 4 setup + N × `task_get_by_project` + N × `burndown_get_by_project` + 1 `burndown_get_by_category` = 5 + 2N queries. Pour N=8 projets → 21 queries (la trace).
- **Après** : 4 setup + 1 `task_get_by_category` + 1 `burndown_get_for_category_projects` + 1 `burndown_get_by_category` = 7 queries, indépendamment du nombre de projets.
- Sémantique inchangée : chaque projet reçoit ses tasks + snapshots, mais groupés en Python plutôt que via N round-trips MySQL.

### Tests

- `tests/unit/test_page_routes.py::TestCategoryPage::test_category_page_uses_batched_queries` :
  1. Vérifie que `task_get_by_category` et `burndown_get_for_category_projects` existent.
  2. Crée une catégorie + 3 projets + 3 tâches (une par projet).
  3. `task_get_by_category` retourne les 3 tâches avec les 3 project_ids attendus.
  4. GET /cat/cat-batch.html → 200 avec les 3 tâches visibles (regression-guard contre mauvais regroupement Python ou retour à la fan-out).

### Garde-fous

- `pdm run check` : 395 passed (394 + 1 nouveau)
- `pdm run test-e2e` : 52 passed
- mypy / ruff / interrogate / vulture / Biome / Vitest : clean

### Note

Même pattern que #257 (admin/keys, key_scopes_get N+1). Si d'autres traces perf remontent ce schéma sur d'autres routes (index?), même recette : batch query + group in Python.
---

[← retour à backend/perf](index.md) · [voir log](../../log/2026-05-24.md)

---
id: 257
title: "PERF / GET /admin/keys / queries 25 > 20"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:53
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #257 — PERF / GET /admin/keys / queries 25 > 20

## Demande

Performance issue on \`GET /admin/keys\`: 25 SQL queries pour 20 clés API → violation du budget perf (queries 25 > 20). N+1 typique : ``key_scopes_get`` appelé une fois par clé.

---

## Résolution

### Modifications

- `src/dashboard/queries/api_keys.sql` : nouvelle requête `key_scopes_get_all` qui retourne tous les `(api_key_id, project_id, scope)` en une seule round-trip.
- `src/dashboard/routes/pages.py` : `admin_keys()` remplace le `for k in api_keys: queries.key_scopes_get(...)` par un seul appel à `key_scopes_get_all`, suivi d'un groupage en Python (`scopes_by_key: dict[str, list]`). Chaque clé reçoit ensuite ses scopes via `scopes_by_key.get(k[\"id\"], [])`.

### Comportements obtenus

- **Avant** : 1 query (categories) + 1 (projects) + 1 (users) + 1 (api_keys) + N (key_scopes_get, une par clé) = 4+N. Pour N=20 → 24 queries plus la query usr_get_by_id du middleware = 25 (la trace).
- **Après** : 1 + 1 + 1 + 1 + **1** = 5 queries, indépendamment du nombre de clés. Pour 20 clés → 5 queries (≪ 20 budget).
- Sémantique inchangée : les scopes par clé sont identiques, juste agrégés en Python plutôt que via N round-trips MySQL.

### Tests

- `tests/unit/test_api_keys.py::TestKeysCRUD::test_admin_keys_page_uses_batched_scopes_query` :
  1. Vérifie que `queries.key_scopes_get_all` existe (sinon route casse).
  2. Crée 2 clés avec scopes différents → la batched query retourne les 2 lignes correctement.
  3. GET /admin/keys → 200 avec les deux labels visibles (regression-guard contre un mauvais regroupement Python ou un retour à la fan-out).

### Garde-fous

- `pdm run check` : 394 passed (393 + 1 nouveau)
- `pdm run test-e2e` : 52 passed / 0 failed
- mypy / ruff / interrogate / vulture / Biome / Vitest : clean

### Note suivi

La route a encore d'autres optims potentiels (charger usr_get_by_id du middleware partage la conn avec la route handler), mais ils ne sont pas couverts ici. Le budget perf 20 est désormais respecté avec marge.
---

[← retour à backend/perf](index.md) · [voir log](../../log.md)

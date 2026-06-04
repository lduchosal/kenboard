---
id: 6
title: "API / API keys avec scopes par projet"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:28:58
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #6 — API / API keys avec scopes par projet

API keys avec scopes par projet (backend) — implémenté.

## Spec

`doc/api-keys.md` (validée par 4 questions OPEN soumises à Q via AskUserQuestion).

Décisions retenues :
- **Rollout** : flag opt-in `KENBOARD_AUTH_ENFORCED=false` par défaut. Le code et la table sont en place mais le middleware ne bloque rien tant que la web UI ne sait pas s'authentifier (cf #1). Permet de déployer sans casser.
- **Endpoints non scopés** (`/api/v1/keys`, `/users`, `/categories`, `/projects` GET/POST) : réservés à `KENBOARD_ADMIN_KEY` (clé statique du `.env`).
- **#6 + #7 en une seule release** : tout livré ensemble.

## Livraisons

- `migrations/0005.create_api_keys.sql` + `0006.create_api_key_projects.sql` (yoyo refuse le multi-statement avec savepoints, deux fichiers séparés)
- `queries/api_keys.sql` (12 requêtes : get_all, get_by_id, get_by_hash, create, update, revoke, delete, touch_last_used, scopes get/clear/add/get_for_project)
- `models/api_key.py` (Pydantic : ApiKey, ApiKeyCreate, ApiKeyUpdate, ApiKeyCreated, ApiKeyScope, Scope)
- `auth.py` (middleware : `_hash_key` sha256, `_resolve_project_id` mapping endpoint→project, `_scope_satisfies` ordering, `_enforce` before_request)
- `routes/keys.py` (CRUD `/api/v1/keys` : POST avec création de clé en clair via `secrets.token_urlsafe(32)` préfixée `kb_`, GET liste, PATCH label/expires/scopes, DELETE = revoke)
- `config.py` : ajout `KENBOARD_ADMIN_KEY`, `KENBOARD_AUTH_ENFORCED`
- `app.py` : `init_auth(app)` enregistre le middleware avant les blueprints

## Mapping endpoint → scope

| Endpoint | project_id | Scope |
|---|---|---|
| GET tasks?project=X | query | read |
| POST tasks | body.project_id | write |
| PATCH/DELETE tasks/<id> | SELECT du task.project_id | write |
| PATCH/DELETE projects/<id> | URL <id> | write |
| /keys/*, /users/*, /categories/*, projects GET/POST | — | admin key only |

## Tests

`tests/unit/test_api_keys.py` — **28 tests** :
- Helpers : `_scope_satisfies`, `_hash_key`
- CRUD `/api/v1/keys` (create returns plaintext once, list strips key, update label, replace scopes, revoke, 404 cases)
- Middleware mode soft (no token passes, invalid token passes, admin endpoint passes)
- Middleware mode enforced (no token blocked, admin key bypass everywhere, normal key blocked on admin endpoint, invalid blocked, revoked blocked, read scope blocks POST, write scope allows POST, wrong project blocked, last_used_at updated)

## État

- 161 tests verts (94 unit + 28 api_keys + reste)
- Tous les checks qualité passent
- Prêt pour publish 0.1.16

Note : nécessite ajout dans le vault ansible de `KENBOARD_ADMIN_KEY` (générer avec `python -c 'import secrets; print("kb_" + secrets.token_urlsafe(32))'`) avant de pouvoir bootstrapper la première api_key. Tant que `KENBOARD_AUTH_ENFORCED=false`, aucune cassure côté web UI.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)

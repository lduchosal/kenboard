---
id: 1129
title: "BACKEND / auth : GET /api/v1/tasks/{id} refusé (403) aux clés API projet"
status: done
who: "Claude"
due_date: 
updated_at: 2026-09-30T14:28:19
classified_at: 2026-09-30T14:14:21
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1129 — BACKEND / auth : GET /api/v1/tasks/{id} refusé (403) aux clés API projet

**TL;DR** — Une clé API projet recevait 403 sur `GET /api/v1/tasks/<id>` parce que le middleware ne résolvait le projet que pour PATCH/DELETE → `GET` ajouté au même lookup DB ; une clé lit désormais les tâches de son projet (200), pas celles d'un autre (403).

## Constat

- `src/dashboard/auth_resolve.py` → `_project_from_tasks` : la branche `/api/v1/tasks/<id>` ne couvre que `method in ("PATCH", "DELETE")`. Pour `GET`, la fonction renvoie `None` → `_check_key_scope` (`auth_api_key.py`) répond 403.
- La route `GET /api/v1/tasks/<id>` (#168) vérifie déjà elle-même `current_user_can_project(row["project_id"], "read")` : c'est seulement la couche clé API en amont qui bloque.
- Conséquences : `ken show` contourne en chargeant toute la liste (`GET /tasks?project=`), et l'extension VS Code (#1127) affiche le détail à partir de la liste, à jour seulement au dernier rafraîchissement.

## À faire

1. `_project_from_tasks` : ajouter `"GET"` au tuple `("PATCH", "DELETE")` pour `/api/v1/tasks/<id>` (même lookup `_task_project_id`).
2. Tests dans `tests/unit/test_auth_resolve.py` : GET `/api/v1/tasks/<id>` → project_id de la tâche ; id inconnu → `None`. Test de scope dans `tests/unit/test_api_keys.py` si le motif existe : une clé du projet A lit une tâche de A (200), pas une tâche de B (403).
3. Optionnel : `ken show <id>` peut passer à `GET /tasks/<id>` au lieu de la liste.
4. Release kenboard + déploiement ; l'extension VS Code pourra alors recharger la tâche fraîche à l'ouverture du détail.


## Résolution

### Modifications

- `src/dashboard/auth_resolve.py` — `_project_from_tasks` : `/api/v1/tasks/<id>` résout le projet via `_task_project_id` pour `GET`, `PATCH` et `DELETE`.
- `tests/unit/test_auth_resolve.py` — GET d'une tâche existante → son project_id ; id inconnu → `None`.
- `tests/unit/test_api_keys.py` — `test_get_task_by_id_scoped_to_key_project` : clé `read` du projet A → 200 sur une tâche de A, 403 sur une tâche de B.

### Comportements obtenus

- `GET /api/v1/tasks/<id>` fonctionne avec une clé API projet ; le cloisonnement par projet est maintenu (id inconnu → 403 côté middleware, comme PATCH/DELETE).
- Commit `ba1a704`.

### Non fait (volontairement)

- Point 3 (`ken show` via `GET /tasks/<id>`) : reporté. Tant que le serveur n'est pas déployé, un `ken` à jour recevrait 403 ; à faire après la release + déploiement (point 4, à la main de l'utilisateur).

### Garde-fous

- Les 2 nouveaux tests échouent sans le correctif et passent avec.
- `pdm run test` : 664 passed. `pdm run check` : gate palier 5 PASS (mypy 0, ruff 0, vulture 0, refurb 0, docstrings 100 %).
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-09-30.md)

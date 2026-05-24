---
id: 197
title: "PERMISSION / Utilisateur sur un board"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:45
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #197 — PERMISSION / Utilisateur sur un board

De la même manière que les clé d'API ont des accès restreints en lecture sur des board, les utilisateurs non administrateur doivent aussi avoir des droits sur des board spécifiques. Dans la gestion des boards ajouter les droits par utilisateur (read / write).

Analyse et propose une spécification pour l'implémentation.

---

## Résolution

Spec (voir historique de cette tâche) implémentée et testée intégralement.

### Modifications

**Schéma + queries**
- `src/dashboard/migrations/0015.create_user_category_scopes.sql` — nouvelle table avec FK cascade, migration idempotente (règles CLAUDE.md §migrations).
- `src/dashboard/queries/user_scopes.sql` — `usr_scopes_*`, `cat_list_for_user`, `proj_list_for_user`, et `usr_grant_all_categories_read` pour le CLI one-shot.
- `tests/conftest.py` — miroir de la table + clean-up dans le fixture `db`.

**Modèles + route**
- `src/dashboard/models/user.py` — `UserScope = Literal["read","write"]`, `UserCategoryScope`, `UserScopeUpdate`, champ `scopes` sur `User`.
- `src/dashboard/routes/users.py` — `PUT /api/v1/users/<id>/scopes` (admin only, clear + add en transaction), enrichissement des réponses avec les scopes.

**Enforcement**
- `src/dashboard/auth_user.py` — `_user_scope_for_category`, `_user_scope_for_project`, `_scope_allows`, `_is_api_key_principal`, `current_user_can`, `current_user_can_project`.
- `src/dashboard/auth.py` — retrait de `/api/v1/categories` et `/api/v1/projects` des `ADMIN_ONLY_PREFIXES`. Les routes s'auto-gèrent via `api_admin_required()` + `current_user_can()`.
- `src/dashboard/routes/categories.py` — GET filtré par scopes, POST/DELETE admin-only, PATCH write sur la category.
- `src/dashboard/routes/projects.py` — GET filtré, POST write sur target cat, PATCH/DELETE write sur la cat du projet + write sur destination en cas de move.
- `src/dashboard/routes/tasks.py` — toutes les opérations check `current_user_can_project`.
- `src/dashboard/routes/pages.py` — `_visible_category_ids()` filtre l'index et `/cat/<id>.html` pour les non-admins.

**UI admin**
- `src/dashboard/templates/admin_users.html` — nouvelle colonne "Accès boards" avec badges colorés cliquables + popover (édition / retrait / ajout). `PUT /users/<id>/scopes` appelé à chaque mutation.

**CLI**
- `src/dashboard/cli.py` — `kenboard grant-legacy-read` (opt-in, idempotent via `INSERT IGNORE`, confirme sauf si `--yes`).

**Tests**
- `tests/unit/test_user_scopes.py` — 19 tests couvrant list-filtering, read/write enforcement, cross-cat move, endpoint scopes atomic, non-régression API-key.
- `tests/unit/test_admin_only.py` + `tests/unit/test_auth_user.py` — mise à jour des tests legacy qui attendaient 403 sur categories/projects (désormais 200 filtré).

**Doc**
- `doc/permissions.md` — modèle dual, scopes, default-closed, CLI legacy, reference API.
- `INSTALL.md` — section 5 : nouvelle table attendue + breaking change de la migration 0015.

### Comportements obtenus

- Humains (cookie) scopés par **category** avec héritage transitif sur projects/tasks.
- API keys (bearer) inchangées — toujours scopées par **project**.
- Non-admin sans scope ⇒ index vide, 403 sur ressource ciblée.
- Admin bypass global via `users.is_admin = 1`.
- UI admin complète : colonne "Accès boards" avec badges colorés + popovers inline.
- Breaking change géré : CLI `kenboard grant-legacy-read` disponible pour les déploiements existants.

### Garde-fous

- `pdm run test-unit` → 289 passed (19 nouveaux tests #197)
- `pdm run test-integration` → 10 passed
- `pdm run test-e2e` → 53 passed
- `pdm run check` (isort + black + docformatter + mypy + flake8 + interrogate 100% + refurb + lint + vulture + test-quick) → tout vert
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)

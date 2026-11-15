---
id: 1189
title: "SEC / Inscription : catégorie Users partagée entre tous les inscrits"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:07
classified_at: 2026-11-15T18:45:08
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1189 — SEC / Inscription : catégorie Users partagée entre tous les inscrits

**TL;DR** — Tous les inscrits recevaient `write` sur une catégorie « Users » commune contenant les projets « personnels » de chacun → chaque inscrit obtient sa propre catégorie.

---

Issu de l'audit #1183 (M1). Chaque inscrit reçoit write sur la catégorie commune 'Users' qui contient les projets personnels de tous : lecture et suppression des tâches des autres.

---

## Résolution

### Modifications

- `src/dashboard/auth_register.py` — `_provision_user()` / `_create_personal_board()` : une catégorie au nom de l'email, un projet dedans, `write` sur cette seule catégorie. Suppression de `_get_or_create_users_category()`.
- `doc/auth-user.md` — flow mis à jour.
- `tests/unit/test_registration.py` — `test_creates_personal_category_and_project`, `test_grants_write_scope_on_own_category_only`.

### Comportements obtenus

- Deux inscrits n'ont aucun scope sur la catégorie de l'autre ; plus de catégorie « Users » créée.

### Point d'attention

- Choix de conception (isolation, les scopes étant par catégorie) **validé par l'utilisateur le 2026-11-15**. Conséquence visible : une catégorie par inscrit sur le tableau de bord des admins.
- Les comptes déjà créés restent dans la catégorie « Users » partagée : pas de migration automatique, à répartir depuis `/admin/board` et `/admin/users` si l'isolation est attendue.

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-15.md)

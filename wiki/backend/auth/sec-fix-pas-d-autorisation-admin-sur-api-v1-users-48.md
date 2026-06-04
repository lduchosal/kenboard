---
id: 48
title: "SEC / FIX / Pas d'autorisation admin sur /api/v1/users"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:19
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #48 — SEC / FIX / Pas d'autorisation admin sur /api/v1/users

**Sévérité: CRITICAL** — corrigé.

## Cause racine

Aucune des routes `/api/v1/users`, `/api/v1/keys`, `/api/v1/categories` (et `/api/v1/projects` GET/POST) ne vérifiait que le caller était admin lorsqu'il était authentifié par cookie. La middleware `auth.py` court-circuitait avec `return None` dès que `current_user.is_authenticated` était vrai, donnant à n'importe quel user connecté tous les droits admin sur l'API. Conséquences:
- `PATCH /api/v1/users/<self> {is_admin: true}` → auto-promotion en admin
- `POST /api/v1/users {is_admin: true}` → création d'un nouvel admin
- `PATCH /api/v1/users/<other>` → modification cross-user
- `DELETE /api/v1/users/<other>` → suppression cross-user

## Fix

`dashboard/auth.py`: la branche `current_user.is_authenticated` du middleware appelle maintenant `_is_admin_only(method, path)` et exige `current_user.is_admin`. Si l'endpoint est admin-only et que le user n'est pas admin, on retourne 403 `admin required for this endpoint` — exactement le même message que pour les keys non-admin (cohérence).

Cette protection vient APRÈS le check CSRF (#49), de sorte qu'une requête sans Origin se fait bloquer en CSRF, et qu'une requête same-origin par un user non-admin se fait bloquer en admin.

`tests/unit/test_admin_only.py` (nouveau, 15 tests):
- Non-admin: GET/POST/PATCH/DELETE sur users, GET/POST sur keys, GET/POST sur categories, GET/POST sur projects → tous 403
- Admin: GET users, GET keys, GET categories, POST categories → tous 200/201

`tests/unit/test_auth_user.py::test_normal_user_session_blocked_on_admin_only_api`: ancien test (qui asserait l'inverse) mis à jour pour refléter le nouveau comportement.

## Vérification

- `pdm run test-quick` → 190 passed (15 nouveaux + 187 existants)
- `python pentest/auth_priv_esc.py` → 0 finding (avant: 4 CRITICAL/HIGH)
- `python pentest/auth_admin_only.py` → 0 finding (avant: 5 CRITICAL)
- `pdm run check` → vert

Les pentests `auth_priv_esc.py` et `auth_admin_only.py` ont été convertis en tests de non-régression. Ils passent maintenant un header `Origin` same-origin pour ne pas être bloqués par le check CSRF en amont, ce qui permet d'aller jusqu'au check admin et de vérifier que c'est lui qui rejette.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)

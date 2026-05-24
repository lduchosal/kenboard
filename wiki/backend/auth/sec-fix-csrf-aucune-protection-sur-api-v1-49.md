---
id: 49
title: "SEC / FIX / CSRF: aucune protection sur /api/v1/*"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:19
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #49 — SEC / FIX / CSRF: aucune protection sur /api/v1/*

**Sévérité: CRITICAL** — corrigé.

## Cause racine

`/api/v1/*` accepte les requêtes JSON authentifiées par cookie sans aucun token CSRF, sans vérification d'`Origin` ni de `Referer`. Combiné à CORS qui reflète l'Origin (#43), n'importe quel site web peut piloter l'API au nom du user connecté.

## Fix

`dashboard/auth.py`: la branche `current_user.is_authenticated` du middleware appelle maintenant `_origin_matches_host()` sur les méthodes unsafe (POST/PATCH/PUT/DELETE) avant de laisser passer. La vérification:
- compare `Origin` à `request.host` (préféré)
- fallback sur `Referer` si `Origin` est absent
- rejette avec 403 si aucun des deux n'est présent (modern browsers en émettent toujours au moins un sur les unsafe + cookie)

Les requêtes par Bearer token ne traversent pas cette branche → elles ne sont pas affectées (un token n'est pas auto-injecté par le navigateur, donc pas de CSRF possible).

`tests/unit/test_csrf.py`: 8 tests couvrant Origin externe, Origin same-origin, Referer-only, méthodes safe, Bearer-token bypass.

## Vérification

- `pdm run test-quick` → 168 passed
- `python pentest/auth_csrf.py` (contre serveur patché) → 0 finding
- `pdm run check` → vert

`pentest/auth_csrf.py` a été converti en test de non-régression (assertions inversées). Le whitelist vulture a aussi été mis à jour pour la fixture `logged_in_user`.
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)

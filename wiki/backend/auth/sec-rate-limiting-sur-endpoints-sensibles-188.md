---
id: 188
title: "SEC / Rate limiting sur endpoints sensibles"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:42
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #188 — SEC / Rate limiting sur endpoints sensibles

Ajouter du rate limiting sur les endpoints sensibles qui n'en ont pas :
- POST /api/v1/keys (création de clés)
- POST /api/v1/users/<id>/reset-password (reset mot de passe)
- POST /api/v1/users (création utilisateur)

Actuellement seul /login est protégé (5/min, 20/h).

---

## Résolution

### Modifications

- `src/dashboard/routes/users.py` — ajout `@limiter.limit("10 per hour")` sur `create_user`, `@limiter.limit("5 per hour")` sur `reset_password`
- `src/dashboard/routes/keys.py` — ajout `@limiter.limit("10 per hour")` sur `create_key`
- `tests/conftest.py` — fix : flask-limiter 4.x cache `enabled` à l'init, ajout `limiter.enabled = False` direct sur l'instance
- `tests/unit/test_auth_user.py` — fixture `rate_limited_client` : toggle `limiter.enabled` directement en plus du config

### Comportements obtenus

- Les 3 endpoints sensibles sont désormais rate-limités par IP (in-memory storage)
- Les tests unitaires ne sont pas impactés grâce au disable explicite du limiter

### Garde-fous

- `pdm run test-quick` : 269 passed
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)

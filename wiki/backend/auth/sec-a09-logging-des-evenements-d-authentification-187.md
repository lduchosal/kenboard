---
id: 187
title: "SEC / A09 / Logging des événements d'authentification"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:42
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #187 — SEC / A09 / Logging des événements d'authentification

Ajouter des logs pour les événements d'authentification manquants :
- login success (auth_user.py)
- login failure (auth_user.py)
- logout (auth_user.py)
- actions admin CRUD users/API keys (routes/users.py, routes/keys.py)

---

## Résolution

### Modifications

- `src/dashboard/auth_user.py` — ajout log `auth.login_success` (user_id, user_name, ip), `auth.login_failed` (user_name, ip), `auth.logout` (user_id, user_name, ip)
- `src/dashboard/auth.py` — ajout log `auth.api_key.invalid` (method, path, ip) sur tentative de clé API invalide
- `src/dashboard/routes/users.py` — ajout logger + logs `admin.user_created`, `admin.user_updated`, `admin.user_deleted` avec principal
- `src/dashboard/routes/keys.py` — ajout logger + logs `admin.key_created`, `admin.key_revoked` avec principal

### Comportements obtenus

- Chaque événement d'authentification (succès, échec, déconnexion) et chaque action admin (CRUD users/keys) est tracé via structlog avec IP et/ou principal
- Les logs utilisent le niveau `info` pour les actions normales, `warning` pour les échecs

### Garde-fous

- `pdm run test-quick` : 269 passed
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)

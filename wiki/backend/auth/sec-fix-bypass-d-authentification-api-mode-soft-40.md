---
id: 40
title: "SEC / FIX / Bypass d'authentification API (mode soft)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:09
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #40 — SEC / FIX / Bypass d'authentification API (mode soft)

**Sévérité: CRITICAL**

`KENBOARD_AUTH_ENFORCED=false` (défaut .env) place la middleware `dashboard.auth` en mode soft: toute requête sans Authorization passe. Conséquence — sur `localhost:5055` avec la DB de test, les opérations suivantes réussissent sans aucun token:

- GET /api/v1/categories → 200
- GET /api/v1/projects → 200
- GET /api/v1/users → 200 (admin-only par design)
- GET /api/v1/keys → 200 (admin-only par design)
- POST /api/v1/categories → 201
- POST /api/v1/projects → 201
- POST /api/v1/tasks → 201
- POST /api/v1/users {is_admin: true} → 201 (création d'admin → prise de contrôle totale via /login)
- POST /api/v1/keys → 201 (clé en clair retournée)

**Reproduction:** `python pentest/auth_bypass.py`

**Remédiation:** retirer le mode soft (la branche `if not enforced: return None` dans `auth.py`), ou au moins faire que le défaut soit `KENBOARD_AUTH_ENFORCED=true`. Documenter dans .env.example. Mettre à jour les tests qui dépendent du mode ouvert.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)

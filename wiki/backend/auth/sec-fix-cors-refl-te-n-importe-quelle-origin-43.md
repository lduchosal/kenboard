---
id: 43
title: "SEC / FIX / CORS reflète n'importe quelle Origin"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:16
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #43 — SEC / FIX / CORS reflète n'importe quelle Origin

**Sévérité: HIGH**

`CORS(app)` est appelé sans whitelist dans `dashboard/app.py:37`. flask-cors renvoie alors `Access-Control-Allow-Origin: <Origin envoyée>` pour toute requête. Combiné au bypass d'auth (#40) et aux cookies de session, n'importe quel site web peut piloter l'API au nom de l'utilisateur connecté.

**Reproduction:** `python pentest/cors.py` — un Origin `https://attacker.example` est reflété tel quel.

**Remédiation:** `CORS(app, origins=["http://localhost:5000", "https://kanban.exemple.com"], supports_credentials=True)`. La liste doit venir d'une variable d'env (`KENBOARD_CORS_ORIGINS`).
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)

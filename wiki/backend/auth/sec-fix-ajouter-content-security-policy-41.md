---
id: 41
title: "SEC / FIX / Ajouter Content-Security-Policy"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:09
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #41 — SEC / FIX / Ajouter Content-Security-Policy

**Sévérité: HIGH**

Aucun header `Content-Security-Policy` n'est servi. Combiné à l'absence de `X-Frame-Options` et à un éventuel XSS futur (le frontend manipule du markdown utilisateur via marked.js), une injection se transformerait directement en exécution de script.

**Reproduction:** `python pentest/headers.py`

**Remédiation:** ajouter un `@app.after_request` dans `dashboard/app.py` qui pose une CSP stricte: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`. Vérifier que app.js / sortable.min.js / marked.min.js continuent de charger.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)

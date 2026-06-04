---
id: 52
title: "SEC / FIX / Stored XSS via marked.parse() sans sanitization"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:20
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #52 — SEC / FIX / Stored XSS via marked.parse() sans sanitization

**Sévérité: HIGH**

`static/app.js:451`: `el.innerHTML = marked.parse(src);` rend le markdown des descriptions de tâches sans sanitization. marked.js (depuis v5+) ne sanitize plus par défaut et autorise le HTML inline. Une description contenant `<img src=x onerror=alert(1)>` est exécutée à l'ouverture de la tâche.

**Vector:** `PATCH /api/v1/tasks/<id> {"description": "<img src=x onerror=alert(1)>"}`

**Reproduction:** `python pentest/auth_xss_stored.py`

**Remédiation:**
1. Vendoriser DOMPurify et l'appliquer après `marked.parse`: `el.innerHTML = DOMPurify.sanitize(marked.parse(src))`.
2. **OU** configurer marked avec `{ async: false, gfm: true, breaks: true }` + une extension qui strip les balises dangereuses.
3. La CSP (#41) limitera l'impact en bloquant l'exécution des handlers inline.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)

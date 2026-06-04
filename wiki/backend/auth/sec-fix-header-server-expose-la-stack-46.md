---
id: 46
title: "SEC / FIX / Header Server expose la stack"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:18
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #46 — SEC / FIX / Header Server expose la stack

**Sévérité: LOW**

`Server: Werkzeug/3.1.8 Python/3.13.12` est servi par toutes les réponses. Donne immédiatement à un attaquant la version exacte de la stack pour cibler les CVE.

**Reproduction:** `python pentest/headers.py`

**Remédiation:** en prod, kenboard ne devrait pas servir directement via Werkzeug (c'est le serveur de dev de Flask). Documenter dans INSTALL.md le déploiement derrière gunicorn/uwsgi + reverse proxy nginx, et nettoyer le header `Server` au niveau du proxy. À court terme: `@app.after_request` qui supprime/écrase `response.headers['Server']`.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)

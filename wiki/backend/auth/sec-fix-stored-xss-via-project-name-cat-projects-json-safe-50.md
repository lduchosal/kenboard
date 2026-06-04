---
id: 50
title: "SEC / FIX / Stored XSS via project.name (cat_projects_json | safe)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:19
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #50 — SEC / FIX / Stored XSS via project.name (cat_projects_json | safe)

**Sévérité: HIGH**

Le template `templates/index.html` injecte les projets dans le DOM via:
```html
<script>const CAT_PROJECTS = {{ cat_projects_json | safe }};</script>
```

Le filtre `| safe` désactive l'auto-escape Jinja2. Le JS lit ensuite cette structure et fait `el.innerHTML = `...${p.name}...`` (cf. `static/app.js:106` et `:178`). Tout HTML stocké dans `projects.name` est donc exécuté.

**Vector:** `PATCH /api/v1/projects/<id> {"name": "<img src=x onerror=alert(1)>"}` puis n'importe quel autre user qui ouvre / voit le XSS s'exécuter.

**Reproduction:** `python pentest/auth_xss_stored.py`

**Remédiation:**
1. Court terme: utiliser `textContent` au lieu de `innerHTML` dans `app.js` lignes 106, 148, 178 (au moins pour `p.name` et `p.acronym`).
2. `cat_projects_json` doit passer par `tojson` (filtre Jinja2 sécurisé) au lieu de `json.dumps + | safe`.
3. Sanitization côté Pydantic: refuser les caractères `<` et `>` dans `ProjectCreate.name` (ou les encoder).
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)

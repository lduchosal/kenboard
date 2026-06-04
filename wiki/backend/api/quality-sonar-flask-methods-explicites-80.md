---
id: 80
title: "QUALITY / Sonar - Flask methods explicites"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:21
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/api
section_title: "REST API"
---

# #80 — QUALITY / Sonar - Flask methods explicites

10 issues python:S6965 — Flask routes sans `methods=` explicite. Le défaut Flask est GET only mais Sonar veut que ce soit déclaré (clarté + defense in depth contre une dérive accidentelle vers PUT/POST/DELETE).

## Fix

`src/dashboard/app.py` (6 routes static-asset): `methods=["GET"]` ajouté à `/style.css`, `/app.js`, `/sortable.min.js`, `/marked.min.js`, `/dompurify.min.js`, `/favicon.ico`. Commentaire inline ajouté en tête du bloc qui pin la convention et mentionne la règle Sonar.

`src/dashboard/routes/pages.py` (4 routes pages): `methods=["GET"]` ajouté à `/`, `/admin/users`, `/admin/keys`, `/cat/<cat_id>.html`.

## Vérification

- `grep -rn '@app.route\|@bp.route' src/dashboard/ | grep -v 'methods='` → aucun match (toutes les routes sont annotées)
- `pdm run check` → 208 passed, vert
---

[← retour à backend/api](index.md) · [voir log](../../log/2026-05-24.md)

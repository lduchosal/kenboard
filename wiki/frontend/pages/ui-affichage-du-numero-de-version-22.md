---
id: 22
title: "UI / Affichage du numéro de version"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:13
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #22 — UI / Affichage du numéro de version

Dans le header, on veut le numéro de version.

## Implémentation

- `routes/pages.py` : import `__version__` depuis `dashboard/__init__.py`, ajoute `version` dans le contexte Jinja partagé `_build_context()`
- `templates/partials/header.html` : nouveau `<span class="header-version" title="kenboard X.Y.Z">vX.Y.Z</span>` à côté du `<h1>KENBOARD</h1>`
- `static/style.css` : `.header-version` en font 10px, `var(--dimmed)`, `tabular-nums`, aligné en bas pour donner un effet "version subscript"

## Test e2e

`test_header_shows_version` dans `TestDashboardLoads` : import `__version__`, vérifie que `.header-version` est visible et affiche `v<version>`.

## État

- 162 tests verts (161 + 1)
- Quality OK
- Sera dans la prochaine release (probablement 0.1.16 avec #6/#7 + #22)
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-05-24.md)

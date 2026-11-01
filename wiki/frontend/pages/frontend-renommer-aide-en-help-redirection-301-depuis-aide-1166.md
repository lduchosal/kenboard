---
id: 1166
title: "frontend / renommer /aide en /help (redirection 301 depuis /aide)"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-01T10:16:08
classified_at: 2026-11-01T10:16:06
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #1166 — frontend / renommer /aide en /help (redirection 301 depuis /aide)

**TL;DR** — `/aide` était la seule route en français → la page d'aide est désormais servie sur `/help` ; `/aide` reste en redirection 301 pour ne casser ni favoris ni liens collés. Le libellé « Aide » ne change pas.

Toutes les routes sont en anglais (/about, /admin/*, /onboard, /login…) sauf /aide. Renommer en /help, garder /aide en redirection 301 (favoris, liens collés), renommer aide.html → help.html et partials/aide_styles.html → partials/card_styles.html (partagé avec /about). Le libellé UI reste « Aide ».

## Résolution

### Modifications
- `src/dashboard/routes/pages.py` — nouvelle vue `help_page` sur `GET /help` (`@login_required`) ; `aide()` ne fait plus que `redirect(url_for("pages.help_page"), 301)`, sans exiger de connexion (c'est `/help` qui protège).
- `src/dashboard/templates/aide.html` → `help.html`, `partials/aide_styles.html` → `partials/card_styles.html` (`git mv`, historique conservé) ; `help.html` et `about.html` incluent le nouveau partial.
- `src/dashboard/templates/partials/header.html` — le menu avatar pointe vers `/help`.
- `src/dashboard/templates/about.html` — le lien vers l'aide pointe vers `/help`.
- Tests : `test_page_routes.py` (`TestAidePage` sur `/help` + 3 tests : 301 `/aide` → `/help`, anonyme : 301 puis 302 vers `/login`, le header ne contient plus `/aide`), `test_branding.py` (`test_help_override`), `test_about.py`.

### Comportements obtenus
- `/help` sert l'aide ; `/aide` → 301 → `/help`.
- Plus aucune référence à `/aide` dans le code, hors la route de redirection et ses tests.
- Les classes CSS `.aide-*` sont gardées telles quelles, pour un diff minimal.

### Garde-fous
- `pdm run test-unit` : 688 passed.
- isort, black, docformatter, ruff, flake8, mypy, interrogate, vulture, refurb : verts.
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-11-01.md)

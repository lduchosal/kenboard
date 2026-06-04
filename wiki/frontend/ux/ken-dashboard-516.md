---
id: 516
title: "KEN / Dashboard"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T22:42:55
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #516 — KEN / Dashboard

Nouveau graph dans le dashboard, statistiques en fonction de la classification des taches wiki groom

---

**Source:** https://www.kenboard.2113.ch/

---

## Résolution

### Modifications
- src/dashboard/queries/wiki.sql — `wiki_section_counts` : COUNT(*) des classifications groupées par section_path, busiest-first (global, comme les autres agrégats du dashboard).
- src/dashboard/routes/pages.py — `_build_wiki_sections_chart(rows)` : prépare {section, count, pct} (pct = part de la section la plus chargée) ; branché dans index() (requête dans le try, ctx.update après le taskers chart).
- src/dashboard/templates/partials/wiki_sections.html — carte ".activity-card" avec une liste de barres horizontales (label section + barre + count).
- src/dashboard/templates/index.html — include du partial dans la section du haut (après activity_taskers).
- src/dashboard/static/style.css — bloc .wiki-bar-* (barres horizontales, cohérent avec le thème).
- tests/unit/test_page_routes.py — test : une tâche classée 'backend/api' apparaît dans le graphe (titre + section).

### Comportements obtenus
- Le dashboard affiche « Tâches par section wiki » : une barre par section_path classée, triées par volume, avec le total. Caché si aucune classification.

### Garde-fous
- mypy clean (typage de l'arithmétique via tuples (name, count) typés) ; flake8(src) clean ; interrogate OK.
- Suite complète : 496 passed (+1).
- NON vérifié visuellement en navigateur ici : rendu confirmé via client de test (partial + section présents). À regarder sur / une fois déployé.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)

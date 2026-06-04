---
id: 533
title: "DASHBOARD / wiki sections par board (scope à la catégorie, pas aggrégat global)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T13:18:10
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #533 — DASHBOARD / wiki sections par board (scope à la catégorie, pas aggrégat global)

Le graphe "Tâches par section wiki" (#516) montre actuellement un agrégat global sur tous les projets/boards mélangés. C'est de la moyenne sans signal : un projet "infra" et un projet "frontend" n'ont pas les mêmes sections représentatives. La classification a du sens **par board** (= par projet / par catégorie selon où on regarde).

Source : observation faite via l'annotation #532 sur la home.

---

## Résolution (option A retenue : déplacer sur les pages catégorie)

### Modifications
- src/dashboard/queries/wiki.sql — `wiki_section_counts` remplacée par `wiki_section_counts_by_category` (JOIN tasks + projects, filtre WHERE p.cat_id = :category_id). La requête globale est supprimée (un seul consommateur).
- src/dashboard/routes/pages.py — `index()` perd la requête + ctx.update du chart ; `category()` ajoute la requête scoped à `cat_id` + ctx.update.
- src/dashboard/templates/index.html — retire `{% include "partials/wiki_sections.html" %}`.
- src/dashboard/templates/category.html — ajoute `{% include "partials/wiki_sections.html" %}` dans une `<div class="section">` juste après le header.
- tests/unit/test_page_routes.py :
  - `TestIndexPage.test_dashboard_does_not_show_wiki_chart_anymore` : régression (le titre du chart ne doit plus apparaître sur /).
  - `TestCategoryPage.test_wiki_chart_scoped_to_category` : crée 2 catégories avec 2 classifications différentes, vérifie que `/cat/A.html` ne montre que la sienne et idem pour B (étanchéité).

### Comportements obtenus
- Chaque page de catégorie affiche désormais son propre chart "Tâches par section wiki", scoped aux projets de cette catégorie. Plus de mélange entre boards sans rapport (#532).
- Le dashboard reste lean (activity + taskers).

### Garde-fous
- TestIndexPage + TestCategoryPage : 13/13 passed.
- mypy clean.
- Suite complète unit+integration verte.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)

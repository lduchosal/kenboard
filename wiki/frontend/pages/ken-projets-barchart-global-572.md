---
id: 572
title: "KEN / Projets / barchart global"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T23:33:35
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #572 — KEN / Projets / barchart global

## Annotations

**Source:** [KEN / Projets / KENBOARD](https://www.kenboard.2113.ch/cat/0ee51b6f-81b8-4da0-9efc-0bd9e01f9e4f.html)

> TÂCHES PAR SECTION WIKI

**Note :** Ce barchart global doit être découpé en 1 barchart par board

---

## Résolution

Le barchart « Tâches par section wiki » de la page catégorie (`/cat/<id>.html`) agrégeait les sections de **tous** les projets de la catégorie en un seul graphique. Sur KENBOARD (355 classifications) ça mélangeait `net-0/monitor`, `backend/auth`, `frontend/ux`, `extension`, `cli/ken`… — des métiers totalement disjoints (finance vs server vs kenboard).

Remplacé par une grille de mini-cards (un barchart par projet/board de la catégorie), calquée sur la grille par-catégorie du dashboard (#540).

### Modifications

- `src/dashboard/queries/wiki.sql` — suppression de `wiki_section_counts_by_category` (#533) ; ajout de `wiki_section_counts_by_category_per_project` qui groupe par `(project_id, section_path)` au lieu de juste `section_path`.
- `src/dashboard/routes/pages.py` — suppression de `_build_wiki_sections_chart` ; ajout de `_build_wiki_sections_per_project_chart(rows, projects, top_n=8)` qui retourne `{wiki_by_project, wiki_by_project_total}`. Route `/cat/<id>.html` câblée sur le nouveau builder + nouvelle query, en passant `cat_projects` pour l'ordre d'affichage.
- `src/dashboard/templates/partials/wiki_sections_by_project.html` — nouveau partial, une mini-card par projet avec l'accent couleur de la catégorie et un anchor `#<project_id>` qui scrolle vers le board.
- `src/dashboard/templates/partials/wiki_sections.html` — supprimé.
- `src/dashboard/templates/category.html` — bascule sur le nouveau partial.
- `src/dashboard/templates/partials/wiki_sections_by_cat.html` — commentaire mis à jour (l'ancien partial n'existe plus).
- `tests/unit/test_page_routes.py` — `test_wiki_chart_scoped_to_category` réétiquetté (#533, #572) ; ajout de `test_wiki_chart_splits_per_project_within_category` qui couvre exactement le cas du #572 (deux projets dans la même cat → deux cards distinctes, sections jamais sommées).

### Comportements obtenus

- Sur `/cat/<id>.html` : titre devient « Tâches par section wiki — par projet », une mini-card par projet ayant au moins une classification, triée par l'ordre d'affichage des projets de la catégorie. Bars normalisées par projet (la plus longue d'un projet remplit son track).
- Les projets sans aucune classification sont omis (pas de carte vide).
- L'anchor `#<project_id>` saute directement au board dans la même page.
- Plus de mélange de métiers : chaque board ne montre que ses propres sections.

### Garde-fous

- `pdm run test-unit` → 498 passed (1 nouveau test).
- `pdm run lint` → All checks passed.
- `pdm run typecheck` → no issues found.
- `pdm run interrogate` → 100% (seuil 95%).
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-05-30.md)

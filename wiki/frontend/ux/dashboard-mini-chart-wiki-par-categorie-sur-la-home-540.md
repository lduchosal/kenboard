---
id: 540
title: "DASHBOARD / mini-chart wiki par catégorie sur la home"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T14:15:09
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #540 — DASHBOARD / mini-chart wiki par catégorie sur la home

Suite de #533 : après déplacement vers /cat/<id>.html, la home a perdu tout signal wiki. Ramener une grille de mini-charts (un par catégorie visible) sur le dashboard, chacun montrant ses propres top sections wiki — sans revenir à l'agrégat mélangé qu'on voulait éliminer (#532). Le chart détaillé reste sur les pages catégorie.

---

## Résolution

### Modifications
- src/dashboard/queries/wiki.sql — nouvelle `wiki_section_counts_grouped` : retourne (category_id, section_path, count), JOIN tasks + projects, GROUP BY p.cat_id, c.section_path, ORDER BY p.cat_id, count DESC. Une ligne par couple (catégorie, section).
- src/dashboard/routes/pages.py — `_build_wiki_sections_per_category_chart(rows, categories, top_n=6)` : groupe par category_id, garde l'ordre catégorie de l'utilisateur (filtré par scope dans index()), normalise chaque carte sur sa propre busiest section (max_count par carte, pas global → comparaisons intra-carte significatives), top 6 sections par carte.
- src/dashboard/templates/partials/wiki_sections_by_cat.html (nouveau) — grid de `<a class="wiki-cat-card">` cliquables vers /cat/<id>.html, bordure gauche colorée à la couleur de la catégorie, header (nom + total), liste de barres avec la couleur de la catégorie sur le fill (override de var(--accent) par inline style).
- src/dashboard/templates/index.html — include du nouveau partial dans la section du haut (après activity_taskers).
- src/dashboard/static/style.css — .wiki-cat-grid (auto-fill, minmax(260px, 1fr), gap 10px), .wiki-cat-card (bg, border, hover, link reset), .wiki-cat-head, .wiki-cat-name/total.
- tests/unit/test_page_routes.py — `test_dashboard_shows_wiki_minichart_per_category` (remplace l'assertion 'not present') : vérifie que le titre, la section et le nom de catégorie apparaissent sur /.

### Comportements obtenus
- La home affiche désormais une mini-grille : une carte par catégorie visible ayant au moins une tâche classifiée, scoped à ses propres projets.
- Chaque carte est un lien vers /cat/<id>.html (chart détaillé).
- Catégorie sans classif → carte invisible (pas de bruit).
- Plus de mélange global (#532 réglé proprement).

### Garde-fous
- TestIndexPage : 22/22 passed.
- Suite complète unit+integration : 499 passed.
- mypy clean.
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-30.md)

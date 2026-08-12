---
id: 1014
title: "WIKI / CHURN - Retirer le numéro de version du ken dans le wiki généré"
status: review
who: "Claude"
due_date: 
updated_at: 2026-08-12T18:06:30
classified_at: 2026-08-12T18:06:36
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #1014 — WIKI / CHURN - Retirer le numéro de version du ken dans le wiki généré

A chaque nouvelle version du ken cli, `ken wiki build` réécrit le footer de **toutes** les pages HTML (`kenboard <version>`) → le publish du wiki engendre un churn insoutenable (326 fichiers modifiés à chaque bump de version, pour zéro changement de contenu).

Analyse et corrige : retirer complètement le numéro de version du wiki généré.

---

## Analyse

`_format_footer()` (`wiki_build.py`) émettait `<footer class="wiki-footer">[Modifié le … — ]kenboard <version></footer>` sur **chaque** page, la version venant de `_version()` (= `dashboard.__version__`).

C'est exactement la même classe de bug que #999 (date de génération) : une donnée **globale, indépendante de la page**, embarquée dans 326 fichiers committés. #999 avait retiré le timestamp de build mais laissé la version — donc le churn est simplement passé de « à chaque build » à « à chaque release », ce qui reste 326 fichiers modifiés pour 0 changement de contenu.

Règle qui en découle : **seule de la donnée par-page (per-task) a le droit d'apparaître dans le HTML généré.**

## Modifications

- `src/dashboard/ken/wiki_build.py`
  - `_format_footer(version, updated_at)` → `_format_footer(updated_at)` : plus de version ; retourne `\"\"` (pas de footer du tout) quand il n'y a pas de stamp, au lieu d'un `<footer>` vide à bordure.
  - `_build_html_plan()` : suppression de l'appel `_version()` ; les pages sans tâche (index de section, index racine, journal) passent `footer_html=\"\"`.
  - Import `_version` retiré ; docstrings module / `_wrap_html` / `_format_footer` mises à jour avec la raison (invariant anti-churn).
- `src/dashboard/ken/wiki_css.py` — commentaire de la règle `.wiki-footer` mis à jour (la règle CSS reste : toujours utilisée par les pages détail).
- `tests/unit/test_ken.py`
  - `TestBuildFooter` adapté à la nouvelle signature ; `test_format_footer_without_date_shows_version_only` → `test_format_footer_without_date_is_empty`.
  - `test_format_footer_omits_ken_version` (neuf) — assert explicite que ni `kenboard` ni `__version__` n'apparaissent.
  - `test_wiki_build_is_byte_stable_across_versions` (neuf) — **garde anti-régression du churn** : build complet avec `__version__` monkeypatché à `0.1.131` puis `9.9.9`, les deux arbres HTML doivent être identiques byte-à-byte.
  - `test_wiki_build_renders_html_tree` : assert que les pages sans tâche ne portent plus de footer, ni version ni « Généré le ».

## Comportements obtenus

- Pages détail : footer réduit à `<footer class=\"wiki-footer\">Modifié le 2026-08-10 18:13:32</footer>` — donnée propre à la tâche, ne bouge que si la tâche bouge.
- Index / sections / journal : plus aucun footer (288 pages avec footer sur 326 ; les 38 restantes n'en ont plus).
- Un bump de version ne modifie plus **aucun** fichier de `wiki-html/`.

## Garde-fous

Vérifié sur l'arbre réel (326 pages) :

- `ken wiki build` × 2 → manifeste `shasum` identique (`c91fb21b…`) : build déterministe.
- `grep -rn 'kenboard 0\.' wiki-html/` → plus que 3 fichiers, tous de la **prose** des tickets #743 / #856 qui décrivent l'ancien footer (contenu, pas génération).
- `grep -o '<footer[^>]*>'` sur index racine / log / ops → vide.

Gates :

- `pdm run lint` — All checks passed
- `pdm run typecheck` — Success, no issues in 60 source files
- `pdm run flake8` — clean
- `pdm run format` / `isort` — 102 files unchanged
- `pdm run interrogate` — PASSED (100%, min 95%)
- `pdm run vulture` — clean
- `pdm run test-unit` — **617 passed**

## Note de publication

Le prochain `angel publish` produira un diff one-shot large (retrait de la ligne version sur 326 pages + suppression de 38 footers devenus vides). C'est le coût unique de la bascule ; après ça, les releases ne touchent plus le wiki.
---

[← retour à wiki](index.md) · [voir log](../log/2026-08-12.md)

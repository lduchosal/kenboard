---
id: 1017
title: "QUALITY / REFACTOR - Découper wiki_build.py et wiki_sync.py sous le plafond metrics-gate"
status: done
who: "Claude"
due_date: 
updated_at: 2026-08-13T08:10:50
classified_at: 2026-08-13T08:05:08
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1017 — QUALITY / REFACTOR - Découper wiki_build.py et wiki_sync.py sous le plafond metrics-gate

`scripts/quality_metrics.py` impose `max_file_lines = 300` en **plafond absolu** (bloquant dans `publish.sh`, étape « Quality Metrics Gate »). Deux modules collent au plafond :

| Fichier | Lignes | Marge |
|---|---:|---:|
| `src/dashboard/ken/wiki_sync.py` | 300 | **0** |
| `src/dashboard/ken/wiki_build.py` | 299 | **1** |
| `src/dashboard/ken/config.py` | 290 | 10 |

**La moindre ligne ajoutée à l'un des deux fait tomber le publish.** Ce n'est pas théorique : c'est arrivé sur ken #1014, où l'ajout de quelques lignes de docstring à `wiki_build.py` (300 → 305) a avorté la release 0.2.8 au step 23/36. Le correctif a été de recomprimer les docstrings — on a payé en lisibilité pour tenir sous un plafond, ce qui est le mauvais arbitrage et ne fait que repousser le problème d'une ligne.

Précédent : ken #786 avait déjà découpé `ken.py` (2266 lignes) en package `dashboard/ken/`. Même geste, un cran plus bas.

## Découpe proposée

Les deux fichiers ont la même structure : un bloc de *formatters* purs suivi d'un bloc *plan + IO + commande click*. La couture est nette dans les deux cas.

**`wiki_build.py` (299) → extraire le chrome HTML vers `wiki_layout.py` (~110 l.)**

- Déplacer : `_rel_href`, `_format_journal_nav`, `_format_sidebar_nav`, `_format_footer`, `_wrap_html` (l. 56–160)
- Reste dans `wiki_build.py` (~190 l.) : `_split_frontmatter`, `_extract_title`, `_sidebar_section_key`, `_build_html_plan`, `_write_html_plan`, la commande `wiki_build`
- `wiki_layout.py` se pose naturellement à côté de `wiki_css.py` (56 l.) — même couche « présentation »

**`wiki_sync.py` (300) → extraire les formatters MD vers `wiki_md.py` (~130 l.)**

- Déplacer : `_format_section_md`, `_format_section_row`, `_format_task_detail_md`, `_yaml_str`, `_format_root_index_md` (l. 38–166)
- Reste dans `wiki_sync.py` (~170 l.) : `_section_pages`, `_build_sync_plan`, `_write_sync_plan`, la commande `wiki_sync`

## Contrainte à respecter

`src/dashboard/ken/__init__.py` **ré-exporte nommément** des symboles privés de ces deux modules (l. 66–67 : `from dashboard.ken.wiki_build import _format_footer, _format_sidebar_nav, _wrap_html`, idem pour `wiki_sync`), et `tests/unit/test_ken.py` les consomme via `ken._format_footer` etc.

→ La surface `ken.*` doit rester **strictement identique** : seules les lignes d'import de `__init__.py` changent, et les 157 tests de `test_ken.py` doivent passer **sans modification**. C'est le critère de non-régression de la découpe.

## Critères d'acceptation

- Aucun fichier de `src/dashboard/ken/` au-dessus de ~200 lignes ; marge nette sous le plafond de 300
- `tests/unit/test_ken.py` inchangé et vert
- `pdm run check` vert, `pdm run metrics-gate` PASS
- `ken wiki sync` + `ken wiki build` produisent un arbre **byte-identique** avant/après découpe (le test `test_wiki_build_is_byte_stable_across_versions` de #1014 couvre déjà la stabilité ; vérifier en plus le manifeste `shasum` sur les 328 pages réelles)

## Hors périmètre

`config.py` (290 l.) n'est pas urgent mais sera le prochain sur la liste — à surveiller.

---

## Résolution

Commit `0af6707` — `refactor(ken): découper wiki_build.py et wiki_sync.py (ken #1017)`.

### Modifications

- `src/dashboard/ken/wiki_layout.py` (**nouveau**, 120 l.) — chrome HTML : `_rel_href`, `_format_journal_nav`, `_format_sidebar_nav`, `_format_footer`, `_wrap_html`. Couche présentation, posée à côté de `wiki_css.py`.
- `src/dashboard/ken/wiki_md.py` (**nouveau**, 147 l.) — formatters MD : `_format_section_md`, `_format_section_row`, `_format_task_detail_md`, `_yaml_str`, `_format_root_index_md`, plus la constante `_ACTIVE_STATUS_ORDER`.
- `src/dashboard/ken/wiki_build.py` — 299 → **191** l. ; ne garde que `_split_frontmatter`, `_extract_title`, `_sidebar_section_key`, `_build_html_plan`, `_write_html_plan`, la commande click.
- `src/dashboard/ken/wiki_sync.py` — 300 → **171** l. ; ne garde que `_section_pages`, `_build_sync_plan`, `_write_sync_plan`, la commande click.
- `src/dashboard/ken/__init__.py` — imports recâblés uniquement. Bonus d'honnêteté : `_classified_date` / `_format_log_day_md` / `_format_log_index_md` sont désormais importés depuis `wiki_log` (leur vraie origine) au lieu de transiter par `wiki_sync`.

### Comportements obtenus

| Fichier | Avant | Après | Marge / 300 |
|---|---:|---:|---:|
| `wiki_build.py` | 299 | **191** | 109 |
| `wiki_sync.py` | 300 | **171** | 129 |
| `wiki_layout.py` | — | 120 | 180 |
| `wiki_md.py` | — | 147 | 153 |

`max_file_lines` du gate : **300 → 298**, et le maximum n'est plus porté par `ken/` mais par `onboarding.py` (298). Le piège qui a fait tomber la 0.2.8 est désarmé.

### Garde-fous

- **Surface publique intacte** : `tests/unit/test_ken.py` passe **sans une seule modification** (`git diff` vide sur mes changements côté tests). `ken._format_footer.__module__` → `dashboard.ken.wiki_layout`, tous les noms de `ken.__all__` résolvent.
- **Sortie byte-identique** : `ken wiki build` sur un arbre MD strictement identique donne le même manifeste `shasum` sur les 328 pages avant et après découpe (`8ac2365ae126e2488a2154886c07bd32850ef7f7`).
- **MD iso-comportement** : `ken wiki sync` re-lancé ne produit qu'un diff de *données* (#1014 passé en `done` → migre de « En cours » vers « Archivé »), zéro changement de structure.
- `ruff` + `flake8` sur les 5 fichiers du périmètre : clean.
- `mypy` : Success, 63 fichiers.
- `interrogate` : 100 % (min 95).
- `vulture`, `refurb` : clean.
- `pdm run test-unit` : **630 passed, 2 failed** — les 2 échecs sont dans `tests/unit/test_method_override.py`, WIP concurrent de #1013 présent dans l'arbre de travail. Baseline prouvée : mes fichiers remisés (`git stash push -- <mes 5 fichiers>`), la suite complète donne **exactement les mêmes 2 échecs**.

### Note — état du gate au moment du commit

`pdm run metrics-gate` est **FAIL**, mais pour une raison étrangère à ce ticket :

```
✗ c901_over_10 = 1 > plafond absolu 0
✗ ruff_debt    = 1 > plafond absolu 0
```

Un unique finding en cause — `D107 Missing docstring in __init__` à `src/dashboard/method_override.py:71` (WIP #1013). Il est compté **deux fois** parce que `_ruff_count()` (`scripts/quality_metrics.py:117`) utilise `--extend-select`, ce qui laisse les règles de base actives : n'importe quel finding ruff gonfle donc simultanément `c901_over_10` et `ruff_debt`, quel que soit son rapport avec C901.

Vérifié : `ruff check src --extend-select C901` → 1 finding, **0 hors `method_override.py`**. Le publish repassera dès qu'une docstring sera posée sur `MethodOverrideMiddleware.__init__`.

Deux pistes hors périmètre, à ouvrir si utile :
- `_ruff_count()` mériterait de filtrer sur le code de règle demandé — la conflation `c901_over_10` / `ruff_debt` rend le diagnostic trompeur.
- `config.py` (290 l.) est le prochain fichier à surveiller sous le plafond.

### Clôture

Passé en `done` sur demande. Vérification finale une fois le WIP de #1013 stabilisé dans l'arbre de travail :

- `pdm run test-unit` → **632 passed, 0 failed**. Les 2 échecs de `test_method_override.py` relevés plus haut ont disparu (corrigés côté #1013) ; la découpe n'y était pour rien, comme la baseline remisée l'avait montré.
- Le `D107` de `method_override.py` qui bloquait le gate a également été corrigé : `ruff check src --extend-select C901` → **0 finding**.
- `max_file_lines` confirmé à **298**, porté par `onboarding.py` — plus aucun module `ken/` au plafond.

Le gate reste FAIL au moment de la clôture, mais sur un motif encore différent et toujours hors périmètre : `vulture = 2 > 0`, deux variables `auth_bypassed` inutilisées dans `tests/unit/test_method_override.py:104` et `:115` (WIP #1013, en `doing`). Le publish ne repassera qu'une fois #1013 terminé.
---

[← retour à quality](index.md) · [voir log](../log/2026-08-13.md)

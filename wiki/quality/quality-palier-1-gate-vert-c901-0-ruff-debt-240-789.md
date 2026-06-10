---
id: 789
title: "QUALITY / Palier 1 — gate vert : C901 → 0 + ruff_debt ≤ 240"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T11:17:03
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #789 — QUALITY / Palier 1 — gate vert : C901 → 0 + ruff_debt ≤ 240

## Objectif

Rendre `pdm run metrics-gate` **vert au palier 1** (régime par paliers ken #788, procédure et tableau dans doc/code-quality.md § Gate bloquant). Sortie rouge actuelle :

```
gate (palier 1): FAIL
  ✗ c901_over_10 = 3 > plafond absolu 0
  ✗ ruff_debt = 255 > plafond absolu 240
```

## Travail

### 1. Complexité C901 → 0 (extraire des helpers, pas de noqa)

- `groom` (CC 16, src/dashboard/ken/wiki.py:164, 126 lignes)
- `_resolve_project_id` (CC 11, src/dashboard/auth.py:89)
- `init_perf` (CC 11, src/dashboard/perf.py:266)

Puis, conformément à la procédure de resserrage : activer `C901` dans `[tool.ruff.lint] extend-select` (pyproject.toml) avec `[tool.ruff.lint.mccabe] max-complexity = 10`.

### 2. ruff_debt 255 → ≤ 240 (−15 findings)

Mesure : `.venv/bin/ruff check src --extend-select PLC0415,PLR,EM,TRY,PERF,PTH,FBT,ARG,BLE,SLF,G,ANN401,RUF --statistics`. Gisements rapides : RUF100 ×10 (noqa obsolètes, auto-fixables — vérifier que les noqa flake8 type DCO ne sont pas supprimés à tort), PLR2004 ×4 (constantes nommées), PERF401 ×6 (comprehensions). Le refactoring du point 1 en résorbe aussi (PLR0911/0912/0915 portés par groom et _resolve_project_id).

## Contraintes

- Ne PAS modifier les seuils GATE_PALIER/GATE_MAX/GATE_MIN (scripts/quality_metrics.py) ni l'historique doc/quality-history.csv : le gate doit passer par amélioration du code uniquement.
- Critère de done : `pdm run check` entièrement vert (inclut metrics-gate) + `pdm run metrics-record` committé une fois vert.
- Attention : modifications non committées en cours dans le working tree (gate #788 : scripts/quality_metrics.py, pyproject.toml, publish.sh, doc/) — ne pas les écraser.
- Workflow board : ken move 789 --to doing avant de commencer ; résolution appendée à la description avant move --to review ; ken wiki groom 789 quality.

---

## Résolution

### Modifications

- `src/dashboard/auth.py` — `_resolve_project_id` (CC 11, 11 returns) décomposé : dispatch par préfixe + `_project_from_tasks` / `_project_from_wiki` + `_task_project_id` (déduplique 3 blocs DB identiques) + `_int_suffix`. PLR0911/PLR0912 résorbés au passage.
- `src/dashboard/perf.py` — les 4 handlers imbriqués de `init_perf` (CC 11) remontés au niveau module (`_perf_before`, `_perf_before_template`, `_perf_after_template`, `_perf_after`) ; `init_perf` ne fait plus que l'enregistrement. Bonus : références fortes pour les signaux blinker.
- `src/dashboard/ken/wiki.py` — `groom` (CC 16, 126 lignes) décomposé : `_show_classification`, `_classify_task`, `_groom_overview` ; `groom` = validations + dispatch (~30 lignes). PLR0915/PLR0912 résorbés.
- RUF100 ×10 purgés (noqa rendus obsolètes par la découpe #786) — le `# noqa: BLE001` d'activity.py conservé (documente un blind-except délibéré).
- PERF401 ×6 : append-en-boucle → `extend`/comprehensions (fmt.py, wiki_sync.py ×3, perf.py, pages.py).
- `pyproject.toml` — ratchet : `C901` activé dans `[tool.ruff.lint] extend-select` + `[tool.ruff.lint.mccabe] max-complexity = 10` ; `tests/**` exempté (helper séquentiel de conftest, le gate métrique ne mesure que src/).
- `doc/quality-history.csv` — snapshot vert enregistré (procédure § Gate bloquant).

### Comportements obtenus

- `pdm run metrics-gate` : **PASS palier 1**. c901_over_10 3 → 0, ruff_debt 255 → 238 (≤ 240), max_func_lines 126 → 110, test_cov 89.81 %.
- Aucun changement fonctionnel (refactorings d'extraction purs).
- Seuils GATE_* et historique non modifiés (contrainte de la carte respectée).

### Garde-fous

- `pdm run check` complet vert (isort, docformatter, black, mypy strict, flake8, interrogate 100%, refurb, ruff, vulture, gate JS, 560 tests, metrics-gate).
- Commit cbf0b4b poussé sur main.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-10.md)

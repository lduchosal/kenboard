---
id: 805
title: "QUALITY / Palier 4 — gate vert : fichiers ≤ 400, fonctions ≤ 60, dette ≤ 20, min_file_cov ≥ 70"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T22:32:28
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #805 — QUALITY / Palier 4 — gate vert : fichiers ≤ 400, fonctions ≤ 60, dette ≤ 20, min_file_cov ≥ 70

## Objectif

Rendre `pdm run metrics-gate` **vert au palier 4** (avant-dernier palier — procédure dans doc/code-quality.md § Gate bloquant). Sortie rouge actuelle :

```
gate (palier 4): FAIL
  ✗ max_file_lines = 461 > plafond absolu 400
        461  src/dashboard/ken/tasks.py
        451  src/dashboard/auth_user.py
        428  src/dashboard/auth.py
        426  src/dashboard/routes/pages.py
        426  src/dashboard/ken/wiki_build.py
        421  src/dashboard/app.py
  ✗ max_func_lines = 78 > plafond absolu 60
        78  init (ken/cli.py:50) ; 78  index (routes/pages.py:135) ; 75  oidc_callback (auth_oidc.py:82) ;
        74  _load_config (ken/config.py:122) ; 70  _build_taskers_daily_chart (routes/charts.py:131) ;
        69  _register_error_handlers (app.py:227) ; 65  register_post (auth_register.py:78) ;
        63  _autocreate_error_task (app.py:162) ; 62  _groom_overview (ken/wiki.py:193) ; 61  polish (ken/tasks.py:369)
  ✗ ruff_debt = 39 > plafond absolu 20
        39  ANN401  any-type
```

min_file_cov : 70.63 % au dernier snapshot — au-dessus du plancher 70 mais avec 0.63 pt de marge seulement. **Tout module créé par les découpes doit naître testé**, sinon la règle vire au rouge.

## Travail

### 1. Six fichiers ≤ 400 (60 lignes max à extraire chacun)

Découpes légères et cohérentes (le gros œuvre est fait aux paliers 2-3) : ken/tasks.py (461), auth_user.py (451), auth.py (428), routes/pages.py (426), ken/wiki_build.py (426), app.py (421).

### 2. Dix fonctions ≤ 60

Extraire des helpers, pas de noqa. Les pires : init 78, index 78, oidc_callback 75, _load_config 74.

### 3. ANN401 39 → ≤ 20 (−19)

`ruff check src --extend-select ANN401` pour la liste. Typer les plus simples (retours de routes → Response, payloads → TypedDict/Pydantic existants). Le reliquat ≤ 20 part au palier 5 (zéro).

### 4. Acquis à verrouiller si atteints

La famille PLR complète et RUF100 sont déjà actifs depuis ce resserrage. Si ANN401 tombe à zéro directement : l'activer (extend-select ANN401 + retrait de DEBT_SELECT) et le palier 5 n'aura plus de volet dette.

## Contraintes

- Ne PAS modifier GATE_PALIER/GATE_MAX/GATE_MIN ni doc/quality-history.csv : le vert vient du code uniquement.
- Critère de done : `pdm run check` entièrement vert (inclut metrics-gate palier 4) + `pdm run metrics-record` committé une fois vert.
- Workflow board : ken move --to doing avant de commencer ; résolution appendée avant move --to review ; ken wiki groom <id> quality.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-10.md)

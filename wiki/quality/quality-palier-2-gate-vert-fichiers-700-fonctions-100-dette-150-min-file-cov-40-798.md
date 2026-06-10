---
id: 798
title: "QUALITY / Palier 2 — gate vert : fichiers ≤ 700, fonctions ≤ 100, dette ≤ 150, min_file_cov ≥ 40"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T18:37:35
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #798 — QUALITY / Palier 2 — gate vert : fichiers ≤ 700, fonctions ≤ 100, dette ≤ 150, min_file_cov ≥ 40

## Objectif

Rendre `pdm run metrics-gate` **vert au palier 2** (procédure et tableau dans doc/code-quality.md § Gate bloquant). Sortie rouge actuelle :

```
gate (palier 2): FAIL
  ✗ max_file_lines = 888 > plafond absolu 700
        888 lignes  src/dashboard/auth_user.py
        701 lignes  src/dashboard/routes/pages.py
  ✗ max_func_lines = 110 > plafond absolu 100
        110 lignes  _build_taskers_daily_chart  src/dashboard/routes/pages.py:95
  ✗ ruff_debt = 237 > plafond absolu 150
  ✗ min_file_cov = 30.36 < plancher absolu 40 (email.py — contrôlé dès qu'un pdm run test-ci a régénéré .coverage)
```

## Travail

### 1. Fichiers ≤ 700 lignes

- `auth_user.py` (888) : vraie découpe en modules (ex. registration / password-reset / email-verification / session), entry points préservés.
- `routes/pages.py` (701) : 1 ligne au-dessus — la découpe des helpers de charts (#2) le règle au passage.

### 2. Fonctions ≤ 100 lignes

- `_build_taskers_daily_chart` (110, routes/pages.py:95) : extraire des helpers (pas de noqa).

### 3. ruff_debt 237 → ≤ 150 (−87)

Mesure : `ruff check src --extend-select PLC0415,PLR,EM,TRY,PTH,FBT,ARG,BLE,SLF,G,ANN401,RUF --statistics`. Gisement complet hors ANN401/PLC0415 = 77 findings : EM ×17, TRY003/300 ×19, FBT ×22, PLR2004 ×4, G201 ×3, PTH ×4, ARG001 ×3, SLF001 ×2, BLE001 ×1, RUF002/012 ×2. Compléter avec ~10 PLC0415 triés (lazy imports CLI légitimes → noqa argumenté ; les autres → remonter en tête de module). ANN401 (×111) reste pour les paliers 4-5.

### 4. min_file_cov ≥ 40

Tests unitaires `email.py` (30.36 %) — aiosmtpd est déjà en dev-deps pour mocker SMTP. Vérifier ensuite qu'aucun autre fichier ne reste < 40 (`coverage json` / sortie détaillée du gate).

## Contraintes

- Ne PAS modifier GATE_PALIER/GATE_MAX/GATE_MIN (scripts/quality_metrics.py) ni doc/quality-history.csv : le vert vient du code uniquement.
- À chaque famille ruff tombée à zéro : l'activer dans [tool.ruff.lint] extend-select et la retirer de DEBT_SELECT (script + doc) — principe ratchet.
- Critère de done : `pdm run check` entièrement vert (inclut metrics-gate palier 2) + `pdm run metrics-record` committé une fois vert.
- Workflow board : ken move --to doing avant de commencer ; résolution appendée avant move --to review ; ken wiki groom <id> quality.

---

## Résolution

### Modifications

**1. Fichiers ≤ 700** — `auth_user.py` 888 → 556 : flows password-reset (`auth_reset.py`, 154) et self-registration (`auth_register.py`, 225) extraits ; routes attachées au même blueprint via import local dans `init_login_manager` (évite le cycle). `routes/pages.py` 701 → 421 : géométrie des charts extraite dans `routes/charts.py` (345).

**2. Fonctions ≤ 100** — `_build_taskers_daily_chart` 110 → 70 (`_bucket_activity_by_person` + `_layout_taskers_bars`) ; `_pie_slices` extrait de `_build_tasks_per_board_pie` (ratchet funcs_over_50 → 24). max_func_lines = 90.

**3. ruff_debt 237 → 114** — EM/TRY003 ×34 (pattern `msg = …; raise`), FBT ×22 (booléens keyword-only, click passe par mot-clé ; appels internes de `_output` adaptés), PLC0415 ×47 triés (25 imports remontés en tête de module ; CLIs `cli.py`/`ken/**` exemptés par per-file-ignores — lazy imports délibérés ; `db.py` noqa argumenté — importable sans flask), PLR2004 ×4 (constantes nommées dont `HTTPStatus.FOUND`), G201 ×3 (`log.exception`), PTH ×4, ARG ×3, SLF ×2 (noqa argumentés), BLE ×1 (noqa argumenté), TRY300 ×2, RUF002/012.

**4. min_file_cov 30.36 → 41.96** — `tests/unit/test_email.py` (8 tests, mock smtplib à la frontière) : `email.py` 30 % → 100 %. Piège évité : `send_email` désormais appelé via attribut de module dans auth_reset/auth_register pour préserver le patch `dashboard.email.send_email` des tests.

**Ratchet** — activés dans `[tool.ruff.lint] extend-select` et retirés de `DEBT_SELECT` (script + doc) : EM, TRY, FBT, ARG, BLE, SLF, G, PTH, PLC0415, PLR2004, RUF002, RUF012. Tests exemptés des familles « hygiène src » (comme mypy/interrogate). Reste en dette : ANN401 ×111 (paliers 4-5), PLR0913 ×3, RUF100 contextuel.

### Comportements obtenus

- `pdm run metrics-gate` : **PASS palier 2**. max_file 556, files>500 = 1, max_func 90, funcs>50 = 24, c901 = 0, dette 114 (≤ 150), cov 90.8 %, min_file_cov 41.96 (≥ 40).
- Aucun changement fonctionnel ; seuils GATE_* et historique intacts (contrainte respectée), snapshot vert committé.

### Garde-fous

- `pdm run check` complet : exit 0 (mypy strict 43 fichiers, flake8, interrogate 100 %, vulture, refurb, gate JS, metrics-gate).
- Suite complète hors e2e : 568 passed ; **e2e 52/52** (la découpe auth touche les routes login/reset/register).
- Commit ee5db41 poussé sur main.
- Note : flake préexistant `test_oidc_login_redirects_to_idp` uniquement sous `pytest tests/unit tests/integration` (ordre de collection non canonique) — reproduit sur baseline propre via git stash, hors périmètre.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-10.md)

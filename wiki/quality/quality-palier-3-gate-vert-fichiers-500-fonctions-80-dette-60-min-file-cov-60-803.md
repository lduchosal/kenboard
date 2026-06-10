---
id: 803
title: "QUALITY / Palier 3 — gate vert : fichiers ≤ 500, fonctions ≤ 80, dette ≤ 60, min_file_cov ≥ 60"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T22:32:27
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #803 — QUALITY / Palier 3 — gate vert : fichiers ≤ 500, fonctions ≤ 80, dette ≤ 60, min_file_cov ≥ 60

## Objectif

Rendre `pdm run metrics-gate` **vert au palier 3** (procédure et tableau dans doc/code-quality.md § Gate bloquant). Sortie rouge actuelle :

```
gate (palier 3): FAIL
  ✗ max_file_lines = 556 > plafond absolu 500
        556 lignes  src/dashboard/auth_user.py
  ✗ max_func_lines = 90 > plafond absolu 80
        90 lignes  category  src/dashboard/routes/pages.py:333
        82 lignes  onboarding_text_full  src/dashboard/onboarding.py:201
        81 lignes  verify_email  src/dashboard/auth_register.py:145
  ✗ ruff_debt = 114 > plafond absolu 60
        111  ANN401  any-type
        3    PLR0913 too-many-arguments
  ✗ min_file_cov = 41.96 < plancher absolu 60 (au dernier snapshot — relancer pdm run test-ci pour le détail ; suspect principal : cli.py ~42 %)
```

## Travail

### 1. auth_user.py ≤ 500 (556 actuellement)

Poursuivre la découpe du palier 2 (auth_register.py en est issu) : extraire un module cohérent de ~60+ lignes (ex. password-reset ou la gestion de session).

### 2. Fonctions ≤ 80 : 3 contrevenants

`category` (90), `onboarding_text_full` (82), `verify_email` (81) — extraire des helpers, pas de noqa.

### 3. ruff_debt 114 → ≤ 60 (−54)

- **PLR0913 ×3** (vraies fonctions, pas des commandes click) : activity.py:48 (7 args), routes/charts.py:77 (6), routes/pages.py:85 (6) — regrouper les params (dataclass/TypedDict) plutôt que noqa. Une fois à zéro : activer PLR0913 dans extend-select **et retirer `RUF100` de `ignore`** (pyproject — différé exprès, les # noqa: PLR0913 des commandes click deviennent alors utilisés), retirer PLR de DEBT_SELECT (script + doc).
- **ANN401 ×51 minimum** : typer les `Any` les plus simples d'abord (retours de routes Flask → `Response | tuple`, payloads ken → TypedDict). Le reste (~60) part aux paliers 4-5.

### 4. min_file_cov ≥ 60

Tests `cli.py` (~42 %) — commandes admin (serve/build/migrate/set-password) via click CliRunner. Vérifier ensuite qu'aucun autre fichier < 60 (sortie détaillée du gate après test-ci).

## Contraintes

- Ne PAS modifier GATE_PALIER/GATE_MAX/GATE_MIN ni doc/quality-history.csv : le vert vient du code uniquement.
- Familles ruff tombées à zéro → extend-select + retrait de DEBT_SELECT (script + doc), principe ratchet.
- Critère de done : `pdm run check` entièrement vert (inclut metrics-gate palier 3) + `pdm run metrics-record` committé une fois vert.
- Workflow board : ken move --to doing avant de commencer ; résolution appendée avant move --to review ; ken wiki groom <id> quality.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-10.md)

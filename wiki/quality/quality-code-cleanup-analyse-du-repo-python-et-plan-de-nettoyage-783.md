---
id: 783
title: "QUALITY / Code cleanup : analyse du repo python et plan de nettoyage"
status: review
who: "Claude"
due_date: 
classified_at: 2026-06-09T22:00:43
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #783 — QUALITY / Code cleanup : analyse du repo python et plan de nettoyage

Analyser le repo python (src/dashboard) et proposer du nettoyage / refactoring pour améliorer la qualité du code. Objectif : définir des critères mesurables (métriques) que l'on peut suivre dans le temps pour constater que la qualité augmente (ex : complexité cyclomatique, duplication, taille des fonctions/modules, couverture, dette mypy/ruff, docstrings).

---

## Résolution

### Modifications

- `scripts/quality_metrics.py` (nouveau) — snapshot des critères qualité : stats AST (LOC, taille fichiers/fonctions), complexité C901, dette ruff (jeu curé `DEBT_SELECT`), mypy/vulture/refurb, interrogate, couverture. Stdlib + outils déjà en venv, zéro dépendance ajoutée. `--json`, `--record`.
- `doc/code-quality.md` (nouveau) — définition des 13 critères suivis, baseline 2026-06-09 (v0.1.132), état des lieux et plan de nettoyage priorisé en 8 chantiers.
- `doc/quality-history.csv` (nouveau) — historique des snapshots (1 ligne baseline). C'est le fichier qui matérialise l'évolution de la qualité.
- `pyproject.toml` — scripts pdm `metrics` et `metrics-record`.

### Comportements obtenus

- `pdm run metrics` affiche le snapshot ; `pdm run metrics-record` l'ajoute au CSV.
- Baseline : 8101 LOC, ken.py 2266 lignes (28% du code), 3 fonctions C901>10 (groom=16), 25 fonctions >50 lignes, ruff_debt=267 (ANN401 ×111, PLC0415 ×48, TRY/EM ×34, DTZ ×6), gates existants tous verts (mypy 0, vulture 0, refurb 0, interrogate 100%, cov 89.29%).
- Plan priorisé (doc/code-quality.md) : 1) auto-fix PLR0402/UP017/RUF100, 2) datetimes naïfs DTZ, 3) casser les 3 C901 puis ratchet du gate, 4) découper ken.py en package, 5) couverture email.py (30%)/cli.py (42%), 6) hygiène exceptions, 7) tri PLC0415, 8) ANN401 au fil de l'eau. Principe ratchet : famille à zéro → ajoutée au gate ruff.
- Duplication : hors périmètre local, suivie par SonarCloud (sonar_gate.py existant).

### Garde-fous

- black + ruff + mypy --strict sur le nouveau script : verts.
- Suite complète hors e2e : 549 passed, cov 89.29%.
- WIP préexistant dans l'arbre (ken.py + tests, autre tâche) non touché.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-09.md)

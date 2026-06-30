---
id: 923
title: "QUALITY / perf.py couverture sous 75% bloque le publish"
status: review
who: "Claude"
due_date: 
classified_at: 2026-06-30T07:36:11
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #923 — QUALITY / perf.py couverture sous 75% bloque le publish

Le job *scheduled* **Publish Package** ([run 28373653620](https://github.com/lduchosal/kenboard/actions/runs/28373653620/job/84057587097)) échoue au **Quality Metrics Gate (palier 5)** :

```
gate (palier 5): FAIL
  ✗ min_file_cov = 63.03 < plancher absolu 75.0
        63.0 %  src/dashboard/perf.py
  ✗ test_cov = 93.13 < meilleur historique 94.12 - tolérance 0.5 (ratchet)
```

`perf.py` (module monitoring #214) a été ajouté sans couverture suffisante : les
helpers purs (`_can_create_task`, `_build_description`, `_create_perf_task`) et
les hooks Flask (templates / after_request / `init_perf`) ne sont pas testés, ce
qui tire perf.py à 63 % (< plancher 75) et le `test_cov` global sous le ratchet.

**Objectif** : remonter `perf.py` ≥ 75 % et le `test_cov` global ≥ 93.62 % en
ajoutant des tests unitaires (sans DB, mock de `db`).

---

## Résolution

### Modifications

- `tests/unit/test_perf.py` — ajout de 24 tests unitaires (sans DB) couvrant les
  blocs jusque-là non testés de `src/dashboard/perf.py` :
  - `TestCooldown` — `_route_key`, `_can_create_task` (fenêtre de cooldown,
    cooldown nul).
  - `TestBuildDescription` — `_build_description` (métriques, détail des queries,
    fallback `template_name` → `N/A`).
  - `TestCreatePerfTask` — `_create_perf_task` avec `db` mocké : pas de
    `project_id`, cooldown bloquant, tâche existante (dédup), création, et chemin
    d'exception (libération du cooldown + `conn.close`).
  - `TestRequestSummary` — `_build_request_summary` (retour `None` sans
    `_start_time`, résumé complet).
  - `TestLogAndEvaluate` — `_log_and_evaluate` (branche avec/sans violation).
  - `TestHooks` — `_perf_before`/`_perf_before_template`/`_perf_after_template`/
    `_perf_after` (collector posé, static skippé, timing template, no-op hors
    contexte, réponse renvoyée sans collector / sans start-time).
  - `TestInitPerf` — `init_perf` (branche désactivée vs activée).
  - Helper `_summary(**overrides)` + fixture `_clear_cooldowns` (isole l'état
    module-level entre tests).

### Comportements obtenus

- `src/dashboard/perf.py` : **63 % → 100 %** (via les tests unitaires seuls,
  119/119 stmts) → au-dessus du plancher absolu 75.
- `test_cov` global : 3786 stmts au total, +44 stmts couverts → ~**94.3 %**,
  au-dessus du ratchet (94.12 − 0.5 = 93.62) et du meilleur historique 94.12.
- `perf.py` était le **seul** fichier < 75 % dans le run CI → `min_file_cov`
  résolu.

### Garde-fous

- `pytest tests/unit/test_perf.py --cov=dashboard.perf` → **40 passed, 100 %**.
- `pytest tests/unit` → **612 passed** (aucune régression, état cooldown isolé).
- `ruff check` → All checks passed (noqa SLF001 inutiles retirés).
- `black --check` / `isort --check-only` / `docformatter --check` → clean.
- `flake8` ne vise que `src/` ; `mypy` exempte les tests.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-30.md)

---
id: 214
title: "PERF / CATEGORY / SLOW REPORT"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:49
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #214 — PERF / CATEGORY / SLOW REPORT

Mettre en place un système d'auto-monitoring des performances côté serveur dans kenboard. Le système doit détecter ses propres problèmes de performance et créer automatiquement des tâches dans le kenboard pour signaler les anomalies. Le board s'alimente lui-même.

---

## Resolution

### Modifications

- `src/dashboard/perf.py` (nouveau) — Module principal : PerfCollector accumule les metriques par requete, check_thresholds evalue les seuils, create_perf_task cree une tache si depassement. Hooks Flask before/after_request + signals template_rendered.
- `src/dashboard/db.py` — Proxy _InstrumentedQueries autour d'aiosql : chaque query SQL est automatiquement chronometree et enregistree dans g.perf quand actif. Transparent hors Flask (CLI, tests).
- `src/dashboard/app.py` — Branchement init_perf(app) dans la factory, avant l'auth.
- `src/dashboard/config.py` — 8 variables d'environnement : PERF_ENABLED, PERF_BUDGET_MS (500), PERF_MAX_QUERIES (20), PERF_MAX_SQL_MS (300), PERF_MAX_RESPONSE_KB (512), PERF_PROJECT_ID, PERF_TASK_WHO (Claude), PERF_COOLDOWN_S (3600).
- `src/dashboard/queries/perf.sql` (nouveau) — Query perf_find_open_task pour la deduplication (LIKE sur le titre).
- `tests/unit/test_perf.py` (nouveau) — 16 tests : PerfCollector, seuils, titres, integration Flask.

### Comportements obtenus

- Chaque requete HTTP (hors statique) est instrumentee : nombre de queries SQL, temps SQL cumule, temps template, taille reponse, temps total.
- Log structlog `perf` emis a chaque requete avec toutes les metriques.
- Quand un seuil est depasse : log warning `perf_threshold_exceeded` + creation automatique d'une tache PERF dans le projet configure (PERF_PROJECT_ID).
- Deduplication : pas de doublon si une tache ouverte existe deja pour la meme route.
- Cooldown configurable (defaut 1h) pour eviter le spam.
- Sans PERF_PROJECT_ID : monitoring en mode log-only (pas de creation de tache).

### Garde-fous

- pytest unit : 327 passed
- mypy : 0 issues
- flake8 : clean
- vulture : clean
- interrogate : 100%
---

[← retour à backend/perf](index.md) · [voir log](../../log/2026-05-24.md)

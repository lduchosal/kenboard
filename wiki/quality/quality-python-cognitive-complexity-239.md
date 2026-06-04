---
id: 239
title: "QUALITY /  Python Cognitive complexity"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:58
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #239 — QUALITY /  Python Cognitive complexity

Cognitive complexity elevee sur 3 fonctions.

---

## Resolution

### create_app() — 44 → ~10

Extrait 5 fonctions helper :
- `_configure_security(app)` — ProxyFix, CORS, security headers
- `_register_request_logging(app)` — before/after request hooks
- `_register_error_handlers(app, debug)` — Pydantic + generique
- `_register_blueprints(app)` — tous les blueprints
- `_register_static_routes(app)` — 6 routes statiques

`create_app()` devient un orchestrateur lisible de ~30 lignes.

### backfill() — 26 → ~10

Extrait 3 fonctions :
- `_to_date(val)` — conversion datetime → date
- `_count_task_status_at(task, day)` — statut d'une tache a une date
- `_backfill_project(conn, proj_id, tasks, start, days)` — boucle par projet

### init_perf() — 19 → ~8

Extrait 2 fonctions du after_request hook :
- `_build_request_summary(response)` — extraction timing/route/taille
- `_log_and_evaluate(summary)` — log + threshold check + task creation

### Garde-fous

- pytest unit : 368 passed
- mypy : clean
- flake8 : clean
- interrogate : 100%
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)

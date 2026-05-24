---
id: 226
title: "PERF / GET / / queries 44 > 20"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:52
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #226 — PERF / GET / / queries 44 > 20

Performance issue on `GET /` — 44 queries.

---

## Resolution

Supprime l'appel a _load_all_data(). L'index charge : categories, projets, users, task_counts_by_project (1 query bulk pour done/total), task_get_all_doing (1 query pour les taches en cours), burndown par categorie. Les taches done/todo/review ne sont plus chargees.

Queries attendues : 3 + 2 (counts + doing) + C (burndown categories)
---

[← retour à backend/perf](index.md) · [voir log](../../log.md)

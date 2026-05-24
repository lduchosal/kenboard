---
id: 224
title: "PERF / GET /admin/board / queries 44 > 20"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:51
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #224 — PERF / GET /admin/board / queries 44 > 20

Performance issue on `GET /admin/board` — 44 queries.

---

## Resolution

Supprime l'appel a _load_all_data(). La route charge directement : categories, projets, users. Plus de taches ni burndown.

Queries attendues : 3
---

[← retour à backend/perf](index.md) · [voir log](../../log.md)

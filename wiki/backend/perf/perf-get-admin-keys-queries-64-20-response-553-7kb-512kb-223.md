---
id: 223
title: "PERF / GET /admin/keys / queries 64 > 20, response 553.7KB > 512KB"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:51
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #223 — PERF / GET /admin/keys / queries 64 > 20, response 553.7KB > 512KB

Performance issue on `GET /admin/keys` — 64 queries, 554KB.

---

## Resolution

Supprime l'appel a _load_all_data(). La route charge directement : categories, projets, users, cles API + scopes. Plus de taches ni burndown. Le N+1 key_scopes_get reste (un par cle) — acceptable pour une page admin.

Queries attendues : ~5 + N (cles API)
---

[← retour à backend/perf](index.md) · [voir log](../../log/2026-05-24.md)

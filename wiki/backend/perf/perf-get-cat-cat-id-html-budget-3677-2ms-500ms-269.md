---
id: 269
title: "PERF / GET /cat/<cat_id>.html / budget 3677.2ms > 500ms"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:00
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #269 — PERF / GET /cat/<cat_id>.html / budget 3677.2ms > 500ms

Performance issue on `GET /cat/<cat_id>.html`.

## Metriques

- **Temps total** : 3677.2ms
- **Queries SQL** : 7 (39.1ms cumule)
- **Template** : category.html (144.3ms)
- **Taille reponse** : 25.3KB

## Violations

- budget 3677.2ms > 500ms

## Detail des queries

- `usr_get_by_id` : 39.0ms
- `cat_get_all` : 0.0ms
- `proj_get_all` : 0.0ms
- `usr_get_all` : 0.0ms
- `task_get_by_project` : 0.0ms
- `burndown_get_by_project` : 0.0ms
- `burndown_get_by_category` : 0.0ms

---

*Tache creee automatiquement par le monitoring de performance (#214).*
---

[← retour à backend/perf](index.md) · [voir log](../../log/2026-05-24.md)

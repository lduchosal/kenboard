---
id: 81
title: "QUALITY / Sonar - SQL ORDER BY ASC explicite"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:22
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/db
section_title: "Database (SQL + migrations)"
---

# #81 — QUALITY / Sonar - SQL ORDER BY ASC explicite

5 issues plsql:OrderByExplicitAscCheck — ORDER BY sans direction explicite. ASC est le défaut mais Sonar veut qu'il soit écrit pour éviter les ambiguïtés.

Fix: ajouter ASC sur les ORDER BY concernés.

Fichiers:
- src/dashboard/queries/users.sql:5
- src/dashboard/queries/categories.sql:5
- src/dashboard/queries/projects.sql:5, 12
- src/dashboard/queries/tasks.sql:7
---

[← retour à backend/db](index.md) · [voir log](../../log/2026-05-24.md)

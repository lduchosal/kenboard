---
id: 4
title: "AUTH / Gestion des users en DB"
status: done
who: "Q"
due_date: 
classified_at: 2026-05-24T14:28:57
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #4 — AUTH / Gestion des users en DB

Créer une table users (id, name, color, etc.) et une migration.

Les users ont un passwd dans la DB SHA2

Remplacer le dict AVATAR_COLORS hardcodé dans routes/pages.py par une lecture en base. 

Exposer un CRUD /api/v1/users et brancher la sélection « who » des tâches dessus.

Une page permet la gestion des droits.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)

---
id: 21
title: "UX / UI / Afficher l'ID de la tâche"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:13
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #21 — UX / UI / Afficher l'ID de la tâche

En mode normal et en mode sélectionné (existant), on souhaite afficher l'ID de la tâche #ID en gris, aligné à droite discret.

## Implémentation

- `templates/partials/task_card.html` : `.task-body` contient désormais une `.task-title-row` (flex baseline) avec `.task-title` (flex:1) à gauche et `.task-id` (`#{{ t.id }}`) à droite
- `static/style.css` : `.task-id` en font-size 10px, `color: var(--dimmed)`, `font-variant-numeric: tabular-nums`, `flex-shrink: 0`
- Visible en mode normal ET en mode détail (la title-row fait partie de `.task-body`, toujours rendue)

## Test e2e

`test_task_id_visible` dans `TestTaskCRUD` : crée une tâche, vérifie que `.task-id` est visible avec le texte `#<id>` en mode normal puis en mode détail.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)

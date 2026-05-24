---
id: 11
title: "BUG / L'édition d'une tâche change son status"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:05
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #11 — BUG / L'édition d'une tâche change son status

Dans l'UI le drop down du status n'est pas mis à jour avec le status de la tâche, Toutes les tâches éditées repartent dans "A FAIRE". Corriger ce problème.

## Cause

Le template `task_card.html` rendait l'onclick avec `t.status` baked-in (`openEditTask(..., "todo", ...)`). Sortable.js déplace la carte dans une autre colonne (ex: doing) **sans recharger la page**, donc l'attribut onclick reste avec la valeur du render initial. À la réouverture du modal, le dropdown affiche `todo` ; le user sauve sans toucher → la tâche revient en A FAIRE.

Aussi : le **fichier `marked.min.js` rendait 500** parce qu'il manquait sa route raccourci dans `app.py` (sortable.min.js / app.js / style.css ont chacun la leur).

## Fix

- `templates/partials/task_card.html` : on passe `this` (le bouton) à `openEditTask` au lieu de `t.status` / `t.project_id` baked-in
- `static/app.js openEditTask(btn, ...)` : status et projectId sont lus depuis `btn.closest(".kanban-tasks").dataset.status` et `btn.closest(".kanban").dataset.projectId` — donc reflètent toujours l'état DOM courant, drag&drop compris
- `app.py` : ajout de la route `/marked.min.js`

## Test de régression

`test_edit_modal_status_reflects_dragged_position` dans `test_dashboard.py::TestTaskCRUD` — crée une tâche, simule le drag (déplacement DOM + PATCH api) sans reload, ouvre le modal, vérifie que le dropdown affiche `doing`, sauve sans rien toucher, vérifie que la tâche reste en doing. Sans le fix : assertion fail.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)

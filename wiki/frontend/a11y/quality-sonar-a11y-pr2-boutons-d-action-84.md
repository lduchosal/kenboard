---
id: 84
title: "QUALITY / Sonar a11y - PR2: boutons d'action"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:23
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/a11y
section_title: "Accessibility"
---

# #84 — QUALITY / Sonar a11y - PR2: boutons d'action

Sous-tâche de #78. Remplacer les <div>/<span> onclick par des <button type='button'> sur les éléments qui sont sémantiquement des boutons.

Cibles:
- header.html:14 — badge-menu-toggle (dropdown)
- header.html:29 — avatar-btn (dropdown)
- kanban.html:14 — kanban-add-task
- kanban.html:50 — show-more
- admin_keys.html:48 — k-scope-remove
- admin_keys.html:52 — k-scope-add
- admin_keys.html:69 — addNewScopeRow
- category.html:20 — cat-card-add (Ajouter un projet)
- category.html:27 — archived-toggle
- index.html:40 — cat-card-add (Ajouter une catégorie)

Risque CSS modéré: il faudra ajouter un reset (background, border, font, padding) sur les nouveaux <button> pour préserver le rendu. Vérifier visuellement après.

~30 issues.
---

[← retour à frontend/a11y](index.md) · [voir log](../../log/2026-05-24.md)

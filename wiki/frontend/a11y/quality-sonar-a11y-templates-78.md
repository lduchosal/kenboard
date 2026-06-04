---
id: 78
title: "QUALITY / Sonar - a11y templates"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:20
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/a11y
section_title: "Accessibility"
---

# #78 — QUALITY / Sonar - a11y templates

48 issues SonarCloud (24 Web:S6848 + 24 Web:MouseEventWithoutKeyboardEquivalentCheck) sur les templates Jinja: les <div onclick=...> et <span onclick=...> ne sont pas accessibles au clavier ni aux lecteurs d'écran.

Fix: remplacer par %lt;button type="button"> quand c'est sémantiquement un bouton, ou ajouter role="button" tabindex="0" + handler keydown (Enter/Space) sinon.

Fichiers:
- src/dashboard/templates/partials/header.html (14, 29)
- src/dashboard/templates/partials/kanban.html (14, 50)
- src/dashboard/templates/partials/task_card.html (8)
- src/dashboard/templates/admin_keys.html (48, 52, 69, 78)
- src/dashboard/templates/category.html (20, 27)
- src/dashboard/templates/index.html (28, 40)
- src/dashboard/templates/modals/error.html (1, 2)
- src/dashboard/templates/modals/category.html (1, 2, 9)
- src/dashboard/templates/modals/confirm.html (1, 2)
- src/dashboard/templates/modals/project.html (1, 2)
- src/dashboard/templates/modals/task.html (1, 2)
---

[← retour à frontend/a11y](index.md) · [voir log](../../log/2026-05-24.md)

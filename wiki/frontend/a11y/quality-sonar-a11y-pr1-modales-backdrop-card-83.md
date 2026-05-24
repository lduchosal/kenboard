---
id: 83
title: "QUALITY / Sonar a11y - PR1: modales (backdrop + card)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:23
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/a11y
section_title: "Accessibility"
---

# #83 — QUALITY / Sonar a11y - PR1: modales (backdrop + card)

Sous-tâche de #78. Refactor des modales pour résoudre les onclick sur backdrop/card.

Stratégie:
- Enlever onclick='this.style.display="none"' du backdrop des modales
- Enlever onclick='event.stopPropagation()' du card interne
- Ajouter en JS: listener Escape global + listener click backdrop (avec event.target === backdrop)

Fichiers:
- src/dashboard/templates/modals/error.html (1, 2)
- src/dashboard/templates/modals/category.html (1, 2)
- src/dashboard/templates/modals/confirm.html (1, 2)
- src/dashboard/templates/modals/project.html (1, 2)
- src/dashboard/templates/modals/task.html (1, 2)
- src/dashboard/static/app.js (ajouter le helper)

~11 issues. Risque faible: pas de changement visuel, pas de nouveau tag.
---

[← retour à frontend/a11y](index.md) · [voir log](../../log.md)

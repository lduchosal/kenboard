---
id: 205
title: "BUG / UX / Detail d'une tâche / se ferme après 1 minute"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:46
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #205 — BUG / UX / Detail d'une tâche / se ferme après 1 minute

Quand on consulte le détail d'une tâche, le refresh automatique de la page ferme le détail et rafraichit. C'est embêtant et empêche de lire une tache.

Ce problème a déjà été résolu pour l'édition d'une tâche. Peux-tu apporter le même fix pour le détail ?

---

## Résolution

### Modifications

- `src/dashboard/static/app.js` — `shouldSkipRefresh()` vérifie maintenant si le dialog fullscreen (`#task-fullscreen`) est ouvert via `dialog.open`. Le modal d'édition (`task-modal`) était déjà protégé via la classe `.project-add-modal`, mais le fullscreen detail view (un `<dialog>` natif) ne l'était pas.

### Comportements obtenus

- La vue fullscreen d'une tâche reste ouverte indéfiniment — l'auto-refresh de 60s est suspendu tant que le dialog est ouvert.
- Dès que le dialog est fermé, l'auto-refresh reprend normalement.
- Le detail-mode inline (expansion de la carte) survit déjà au reload via le hash URL `#ID-<task-id>` (#109), donc pas de changement nécessaire là.

### Garde-fous

- `pdm run test-unit` → 303 passed
- `pdm run test-e2e` → 53 passed
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-24.md)

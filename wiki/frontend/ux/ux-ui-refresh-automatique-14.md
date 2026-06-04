---
id: 14
title: "UX / UI / Refresh automatique"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:07
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #14 — UX / UI / Refresh automatique

Toutes les minutes, un js trigger un refresh de la page.

## Implémentation

Ajout dans `src/dashboard/static/app.js` :
- `setInterval(60_000)` qui appelle `window.location.reload()`
- `shouldSkipRefresh()` saute le reload si :
  - `document.hidden` (onglet en arrière-plan)
  - une carte est en cours de drag (`.task-chosen` / `.task-drag`)
  - une modale (`.project-add-modal`) est ouverte (sinon on perd la saisie en cours)

Aucun nouveau dépendance, ~15 lignes.
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-24.md)

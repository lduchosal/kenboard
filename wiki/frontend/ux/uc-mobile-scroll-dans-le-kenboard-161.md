---
id: 161
title: "UC / MOBILE / Scroll dans le kenboard"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:42
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #161 — UC / MOBILE / Scroll dans le kenboard

En mobile quand on scroll dans le kenboard, on est sans cesse en train de deplacer des tache a cause di drag and drop.
En mode mobile, mettre le drag handler sur les cartes pour eviter ces problèmes

---

## Résolution

### Cause

SortableJS interceptait les événements touch sur toute la surface de la carte kanban. Sur mobile, un geste de scroll vertical déclenchait un drag-and-drop au lieu de faire défiler la page.

### Fix

Même pattern que le `.cat-drag-handle` existant sur les cartes catégorie :

- **`task_card.html`** — ajout d'un `<span class="task-drag-handle">☰</span>` (position absolute, top-left de la carte)
- **`style.css`** — `.task-drag-handle` : `display: none` par défaut (desktop = drag sur toute la carte). Dans `@media (max-width: 480px)` : `display: inline-block` (mobile = drag uniquement via le handle).
- **`app.js`** — le Sortable des colonnes kanban est reconstruit dynamiquement via `matchMedia('(max-width: 480px)')`. Quand mobile détecté : `opts.handle = '.task-drag-handle'`. Le listener `change` réinitialise les instances au changement de breakpoint.
- `.kanban-task` reçoit `position: relative` pour ancrer le handle absolute.

### Garde-fous

- 269 tests verts
- Desktop : aucun changement visible (handle hidden, drag sur toute la carte comme avant)
- Mobile : le handle ☰ apparaît en haut-gauche, seul élément draggable → scroll vertical fonctionne
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-24.md)

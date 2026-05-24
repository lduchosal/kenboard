---
id: 259
title: "UX / Navigation avec le clavier"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:53
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/a11y
section_title: "Accessibility"
---

# #259 — UX / Navigation avec le clavier

## Demande

Down / Up : passe à la tache suivante dans la colonne. Quand on est à la fin de la colonne, on passe a la première tâche de la colonne suivante. Quand on est à la fin de la dernière tâche de la dernière colonne, on passe à la permière tâche du board suivant.

---

## Résolution

### Modifications

- `src/dashboard/static/js/keyboard.js` : `moveVertical` étendu en cascade.
  - Au bord d'une colonne, on tente d'abord la colonne adjacente du même kanban (`nextCardAcrossColumns`) — première carte si on descend, dernière si on monte. Les colonnes vides sont skip.
  - Si on est en bas de la dernière colonne (ou en haut de la première), on tombe sur la logique #253 d'origine via `nextCardAcrossKanbans` — première carte du kanban suivant (ou dernière du précédent).
  - Deux helpers privés extraits pour clarté + couverture : `nextCardAcrossColumns(kanban, currentCol, delta)` et `nextCardAcrossKanbans(kanban, delta)`.
- `src/dashboard/templates/modals/keyboard.html` : section *Navigation entre boards* renommée en *Navigation verticale entre colonnes et boards* avec les deux comportements expliqués (intra-kanban puis inter-kanban).
- `src/dashboard/static/js/keyboard.test.js` : nouveau bloc `describe('moveVertical across columns within a kanban (#259)')` avec 4 tests :
  - end-of-column → first card of next column
  - top-of-column → last card of previous column
  - skips empty intermediate columns
  - only spills to next kanban after the LAST column of the current one (deux ↓ successifs depuis la première colonne d'un kanban à 2 colonnes pour atteindre le kanban suivant)

### Comportements obtenus

Pour un kanban à 4 colonnes (todo / doing / review / done) avec des cartes dans chaque :
- ↓ sur la dernière carte de *todo* sélectionne la première de *doing*.
- ↓ sur la dernière carte de *doing* sélectionne la première de *review*.
- ↓ sur la dernière carte de *done* (dernière colonne) sélectionne la première carte du kanban suivant (ou clamp si dernier kanban).
- ↑ symétrique.
- Les colonnes vides sont skip dans les deux directions.

### Garde-fous

- `pdm run js-test` : 60 tests passed (4 nouveaux + 56 existants)
- `pdm run check` (composite Python + JS) : 378 passed
- `pdm run test-e2e` : 52 passed / 0 failed
- Bundle : 23.35 KB / 6.66 KB gzip
---

[← retour à frontend/a11y](index.md) · [voir log](../../log.md)

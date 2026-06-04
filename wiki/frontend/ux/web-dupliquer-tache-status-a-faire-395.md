---
id: 395
title: "WEB / Dupliquer tâche / Status A Faire"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:08
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #395 — WEB / Dupliquer tâche / Status A Faire

## Demande

Quand on duplique une tâche, la copie revient en TODO.

---

## Diagnostic

`src/dashboard/static/js/tasks.js::duplicateTask` héritait du status de l'original via `document.getElementById('task-modal-status').value`. Si tu dupliquais une tâche en \"doing\" ou \"done\", la copie atterrissait dans la même colonne — comportement inverse de ce qui est attendu pour un duplicate.

## Résolution

### Modifications

- `src/dashboard/static/js/tasks.js` : la POST du duplicate force `status: 'todo'` (hardcode, drop de la lecture du select). Après la réponse serveur, le champ `#task-modal-status` du modal est aussi remis à `'todo'` pour que l'UI reflète l'état serveur (sinon l'utilisateur voit encore `doing` dans le dropdown et pourrait re-save sans s'en rendre compte).
- Commentaire JSDoc qui explique le pourquoi : un duplicate représente du travail neuf à planifier, pas une ré-instanciation d'une tâche en cours / faite.

### Tests

- `src/dashboard/static/js/tasks.test.js` (nouveau) : deux tests Vitest avec jsdom + fetch mocké :
  1. Original en `doing` → POST a `status: 'todo'`, modal-select réaligné à `todo`.
  2. Original en `done` → idem, le forçage marche pour toutes les colonnes.

Sanity check inclus que `openEditTask` reflète bien le status original AVANT le duplicate, pour montrer que c'est le duplicate qui force, pas un effet de bord d'`openEditTask`.

### Comportements obtenus

- Duplicate d'une tâche `todo` → copie en `todo` (inchangé)
- Duplicate d'une tâche `doing` → copie en `todo` (fix #395)
- Duplicate d'une tâche `review` → copie en `todo` (fix)
- Duplicate d'une tâche `done` → copie en `todo` (fix)
- Le modal affiche `todo` après le duplicate, plus de confusion UX.

### Garde-fous

- `pdm run js-test` : 63 passed (61 + 2 nouveaux)
- `pdm run check` (composite Python + JS) : 395 passed
- `pdm run test-e2e` : 52 passed / 0 failed
- Note : `tasks.js` reste exclu de la coverage Sonar (per `sonar-project.properties`, DOM-mutator → couvert par Playwright), mais le test Vitest est explicitement présent pour ce contrat précis.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
